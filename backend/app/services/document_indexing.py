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
from app.repositories import documents as documents_repo
from app.repositories.document_chunks import DocumentChunk
from app.repositories.organizations import Organization
from app.repositories.sources import Source

logger = logging.getLogger("app.services.document_indexing")


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

    docs = await documents_repo.list_by_ids(session, document_ids)
    written = 0

    for doc in docs:
        if doc.organization_id is None:
            continue
        if doc.organization_id != organization.organization_id:
            continue
        body = (doc.body_text or "").strip()
        if not body:
            continue

        await chunks_repo.delete_for_document(session, doc.document_id)

        source_name = await _source_name(session, doc, organization)
        title = (doc.title or "").strip()
        embed_input_prefix = f"{title}\n\n" if title else ""

        pieces = _split(
            body,
            chunk_size=settings.chunk_size_chars,
            chunk_overlap=settings.chunk_overlap_chars,
        )
        if not pieces:
            continue

        texts_for_embed = [f"{embed_input_prefix}{piece}" for piece in pieces]
        try:
            vectors = await embedder.embed_texts(texts_for_embed)
        except Exception:
            logger.exception("Embedding failed for document %s", doc.document_id)
            continue

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
        written += len(rows)

    return written


async def _source_name(
    session: AsyncSession, doc, organization: Organization
) -> str:
    if doc.source_id is not None:
        source = await session.get(Source, doc.source_id)
        if source is not None:
            return source.name
    return f"{organization.name} official website"
