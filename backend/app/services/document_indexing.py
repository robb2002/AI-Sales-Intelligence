"""Chunk and embed collected documents for Advisor RAG (AI_RAG_DESIGN.md §§13–16)."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.embeddings import EmbeddingAdapter
from app.core.config import Settings
from app.ingestion.chunking import split_text

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    def _split(
        text: str, *, chunk_size: int, chunk_overlap: int
    ) -> list[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_text(text)
except ImportError:  # optional; local splitter matches AI_RAG_DESIGN.md §14 sizes

    def _split(
        text: str, *, chunk_size: int, chunk_overlap: int
    ) -> list[str]:
        return split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

from app.repositories import document_chunks as chunks_repo
from app.repositories.document_chunks import DocumentChunk
from app.repositories.documents import Document
from app.repositories.organizations import Organization
from app.repositories.sources import Source

logger = logging.getLogger("app.services.document_indexing")

# Returned by index_one_document when the body changed while embedding was in flight.
STALE_CONTENT = "stale"


async def index_documents(
    session: AsyncSession,
    *,
    settings: Settings,
    embedder: EmbeddingAdapter,
    organization: Organization,
    document_ids: list[UUID],
) -> int:
    """Delete and rebuild chunks for changed documents. Returns chunk count written."""
    if not document_ids:
        return 0
    if not settings.embedding_configured:
        logger.warning("Embeddings not configured; skipping document index")
        return 0

    written = 0
    for document_id in document_ids:
        result = await index_one_document(
            session,
            settings=settings,
            embedder=embedder,
            organization=organization,
            document_id=document_id,
        )
        if isinstance(result, int):
            written += result
    return written


async def index_one_document(
    session: AsyncSession,
    *,
    settings: Settings,
    embedder: EmbeddingAdapter,
    organization: Organization,
    document_id: UUID,
) -> int | str:
    """Index one document after reloading it from the DB.

    Returns chunk count written, 0 if skipped, or ``STALE_CONTENT`` if the body
    changed during the embed call (caller should re-queue).
    """
    if not settings.embedding_configured:
        return 0

    doc = await session.get(Document, document_id)
    if doc is None or doc.organization_id is None:
        return 0
    if doc.organization_id != organization.organization_id:
        logger.warning(
            "Skip index: document %s org mismatch (doc=%s expected=%s)",
            document_id,
            doc.organization_id,
            organization.organization_id,
        )
        return 0

    body = (doc.body_text or "").strip()
    if not body:
        return 0

    hash_before = doc.content_hash
    source_name = await _source_name(session, doc, organization)
    title = (doc.title or "").strip()
    embed_input_prefix = f"{title}\n\n" if title else ""

    pieces = _split(
        body,
        chunk_size=settings.chunk_size_chars,
        chunk_overlap=settings.chunk_overlap_chars,
    )
    if not pieces:
        return 0

    texts_for_embed = [f"{embed_input_prefix}{piece}" for piece in pieces]
    try:
        vectors = await embedder.embed_texts(texts_for_embed)
    except Exception:
        logger.exception(
            "Embedding failed for document %s org %s",
            document_id,
            organization.organization_id,
        )
        return 0

    # Stale-body guard: do not write vectors for a body that was replaced mid-flight.
    await session.refresh(doc)
    if doc.content_hash != hash_before:
        logger.info(
            "Stale content during embed; re-queue document %s org %s",
            document_id,
            organization.organization_id,
        )
        return STALE_CONTENT

    await chunks_repo.delete_for_document(session, doc.document_id)

    rows: list[DocumentChunk] = []
    for idx, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
        rows.append(
            DocumentChunk(
                document_id=doc.document_id,
                organization_id=doc.organization_id,
                signal_id=None,
                source_name=source_name,
                source_url=doc.source_url,
                published_on=doc.published_on,
                content_role="signal_source",
                data_origin=doc.data_origin,
                chunk_text=piece,
                chunk_index=idx,
                embedding=vector,
                embedding_model=settings.embedding_model,
                retrieved_at=doc.retrieved_at,
            )
        )
    await chunks_repo.insert_chunks(session, rows)
    return len(rows)


async def _source_name(
    session: AsyncSession, doc, organization: Organization
) -> str:
    if doc.source_id is not None:
        source = await session.get(Source, doc.source_id)
        if source is not None:
            return source.name
    return f"{organization.name} official website"
