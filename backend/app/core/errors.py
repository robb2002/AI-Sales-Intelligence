from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    message = "Something went wrong on the server."

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class AuthMissingError(AppError):
    status_code = 401
    code = "AUTH_MISSING"
    message = "Authentication is required."


class AuthInvalidError(AppError):
    status_code = 401
    code = "AUTH_INVALID"
    message = "Authentication failed."


class AuthExpiredError(AppError):
    status_code = 401
    code = "AUTH_EXPIRED"
    message = "Sign in again."


class UserNotProvisionedError(AppError):
    status_code = 403
    code = "USER_NOT_PROVISIONED"
    message = "This account is signed in but has not been granted access yet."


class UserWithoutRoleError(AppError):
    status_code = 403
    code = "USER_WITHOUT_ROLE"
    message = "This account is signed in but has no application role."


class InsufficientPermissionError(AppError):
    status_code = 403
    code = "INSUFFICIENT_PERMISSION"
    message = "This account is not allowed to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "The requested item was not found."

    def __init__(self, resource: str, message: str | None = None) -> None:
        super().__init__(message, {"resource": resource})


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _field_name(location: tuple[Any, ...]) -> str:
    parts = [str(part) for part in location if part not in ("body", "query", "path", "header")]
    return ".".join(parts) or "request"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = {_field_name(tuple(error["loc"])): error["msg"] for error in exc.errors()}
        return JSONResponse(
            status_code=400,
            content=error_body("VALIDATION_ERROR", "The request is not valid.", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            body = error_body("NOT_FOUND", "The requested path does not exist.")
        elif exc.status_code >= 500:
            body = error_body("INTERNAL_ERROR", AppError.message)
        else:
            body = error_body("VALIDATION_ERROR", "The request is not valid for this path.")
        return JSONResponse(status_code=exc.status_code, content=body)
