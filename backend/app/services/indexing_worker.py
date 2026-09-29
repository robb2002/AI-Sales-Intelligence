"""Same-process background document indexing (Advisor RAG).

Scan / Scan All enqueue document ids and continue. Chunking and Azure embeddings
run here so they do not block scan latency. Integrity: reload by document_id,
match organization_id, replace chunks only for that document.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.adapters.embeddings import get_embedding_adapter
from app.core.config import Settings
from app.repositories.organizations import Organization
from app.services.document_indexing import STALE_CONTENT, index_one_document

logger = logging.getLogger("app.services.indexing_worker")

_embed_semaphore: asyncio.Semaphore | None = None
_MAX_STALE_RETRIES = 3
_STARTUP_SWEEP_LIMIT = 100


def _semaphore(settings: Settings) -> asyncio.Semaphore:
    global _embed_semaphore
    if _embed_semaphore is None:
        _embed_semaphore = asyncio.Semaphore(max(1, settings.index_concurrency))
    return _embed_semaphore


def schedule_document_indexing(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    organization_id: UUID,
    document_ids: list[UUID],
    stale_attempt: int = 0,
) -> None:
    """Fire-and-forget indexing. Safe to call from the scan critical path."""
    ids = list(dict.fromkeys(document_ids))
    if not ids:
        return
    if not settings.embedding_configured:
        logger.warning(
            "Embeddings not configured; skip scheduling index for org %s (%s docs)",
            organization_id,
            len(ids),
        )
        return

    task = asyncio.create_task(
        run_indexing_job(
            session_factory=session_factory,
            settings=settings,
            organization_id=organization_id,
            document_ids=ids,
            stale_attempt=stale_attempt,
        ),
        name=f"index-org-{organization_id}",
    )

    def _done(t: asyncio.Task[None]) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            logger.exception(
                "Background indexing task failed org %s",
                organization_id,
                exc_info=exc,
            )

    task.add_done_callback(_done)


async def run_indexing_job(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    organization_id: UUID,
    document_ids: list[UUID],
    stale_attempt: int = 0,
) -> None:
    """Index documents for one organization with a global embed concurrency cap."""
    if not document_ids or not settings.embedding_configured:
        return

    embedder = get_embedding_adapter(settings)
    stale_ids: list[UUID] = []
    written = 0

    async with _semaphore(settings):
        async with session_factory() as session:
            org = await session.get(Organization, organization_id)
            if org is None:
                logger.warning("Indexing skipped; organization %s missing", organization_id)
                return

            for document_id in document_ids:
                try:
                    result = await index_one_document(
                        session,
                        settings=settings,
                        embedder=embedder,
                        organization=org,
                        document_id=document_id,
                    )
                    if result == STALE_CONTENT:
                        stale_ids.append(document_id)
                    elif isinstance(result, int):
                        written += result
                    await session.commit()
                except Exception:
                    logger.exception(
                        "Indexing failed document %s org %s",
                        document_id,
                        organization_id,
                    )
                    await session.rollback()

    logger.info(
        "Background index org %s: %s chunks from %s documents (%s stale)",
        organization_id,
        written,
        len(document_ids),
        len(stale_ids),
    )

    if stale_ids and stale_attempt < _MAX_STALE_RETRIES:
        schedule_document_indexing(
            session_factory=session_factory,
            settings=settings,
            organization_id=organization_id,
            document_ids=stale_ids,
            stale_attempt=stale_attempt + 1,
        )
    elif stale_ids:
        logger.warning(
            "Giving up stale re-index after %s attempts for org %s docs %s",
            _MAX_STALE_RETRIES,
            organization_id,
            stale_ids,
        )


async def sweep_unindexed_documents(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """On startup, schedule documents missing chunks for the current embedding model."""
    if not settings.embedding_configured:
        return

    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                SELECT d.document_id, d.organization_id
                FROM documents d
                WHERE d.organization_id IS NOT NULL
                  AND char_length(trim(d.body_text)) > 0
                  AND NOT EXISTS (
                    SELECT 1
                    FROM document_chunks c
                    WHERE c.document_id = d.document_id
                      AND c.embedding_model = :model
                  )
                ORDER BY d.retrieved_at DESC
                LIMIT :lim
                """
            ),
            {"model": settings.embedding_model, "lim": _STARTUP_SWEEP_LIMIT},
        )
        pending = [(row[0], row[1]) for row in rows.all()]

    if not pending:
        return

    by_org: dict[UUID, list[UUID]] = {}
    for document_id, organization_id in pending:
        by_org.setdefault(organization_id, []).append(document_id)

    logger.info(
        "Startup index sweep: %s documents across %s organizations",
        len(pending),
        len(by_org),
    )
    for organization_id, doc_ids in by_org.items():
        schedule_document_indexing(
            session_factory=session_factory,
            settings=settings,
            organization_id=organization_id,
            document_ids=doc_ids,
        )
