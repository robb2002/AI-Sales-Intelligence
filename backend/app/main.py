import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import protected_router, public_router
from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.errors import AppError, error_body, register_exception_handlers
from app.core.logging import configure_logging, request_id_var
from app.core.security import ClerkClient

logger = logging.getLogger("app")


async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = uuid.uuid4().hex
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error")
            response = JSONResponse(
                status_code=500, content=error_body("INTERNAL_ERROR", AppError.message)
            )
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            },
        )
        return response
    finally:
        request_id_var.reset(token)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        from app.services.scans import mark_interrupted_on_startup

        await mark_interrupted_on_startup(create_session_factory(engine))
        yield
        await engine.dispose()

    is_local = settings.app_env == "local"
    app = FastAPI(
        title="AI Sales Intelligence API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if is_local else None,
        redoc_url=None,
        openapi_url="/openapi.json" if is_local else None,
    )
    app.state.settings = settings
    app.state.session_factory = create_session_factory(engine)
    app.state.clerk_client = ClerkClient(settings.clerk_secret_key, settings.cors_origins)

    register_exception_handlers(app)
    app.middleware("http")(request_context)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
    )

    app.include_router(public_router)
    app.include_router(protected_router)
    return app


app = create_app()
