from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    delete,
    func,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.vector import Vector
from app.repositories.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint(
            "content_role IN ('signal_source', 'reference')",
            name="document_chunks_content_role_check",
        ),
        CheckConstraint(
            "data_origin IN ('live', 'cached')",
            name="document_chunks_data_origin_check",
        ),
        CheckConstraint(
            "char_length(chunk_text) > 0",
            name="document_chunks_chunk_text_not_empty",
        ),
        UniqueConstraint(
            "document_id", "chunk_index", name="document_chunks_document_index_uq"
        ),
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.organization_id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("signals.signal_id", ondelete="SET NULL")
    )
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    published_on: Mapped[date | None] = mapped_column(Date)
    content_role: Mapped[str] = mapped_column(Text, nullable=False)
    data_origin: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    embedding_model: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


async def delete_for_document(session: AsyncSession, document_id: uuid.UUID) -> None:
    await session.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(float(x)) for x in values) + "]"


async def insert_chunks(
    session: AsyncSession,
    rows: list[DocumentChunk],
) -> list[DocumentChunk]:
    """Insert chunks with an explicit CAST so asyncpg accepts pgvector literals."""
    inserted: list[DocumentChunk] = []
    for row in rows:
        embedding = row.embedding
        embedding_model = row.embedding_model
        result = await session.execute(
            text(
                """
                INSERT INTO document_chunks (
                  document_id, organization_id, signal_id, source_name, source_url,
                  published_on, content_role, data_origin, chunk_text, chunk_index,
                  embedding, embedding_model, retrieved_at
                ) VALUES (
                  :document_id, :organization_id, :signal_id, :source_name, :source_url,
                  :published_on, :content_role, :data_origin, :chunk_text, :chunk_index,
                  CAST(:embedding AS vector), :embedding_model, :retrieved_at
                )
                RETURNING chunk_id
                """
            ),
            {
                "document_id": row.document_id,
                "organization_id": row.organization_id,
                "signal_id": row.signal_id,
                "source_name": row.source_name,
                "source_url": row.source_url,
                "published_on": row.published_on,
                "content_role": row.content_role,
                "data_origin": row.data_origin,
                "chunk_text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "embedding": _vector_literal(embedding) if embedding is not None else None,
                "embedding_model": embedding_model,
                "retrieved_at": row.retrieved_at,
            },
        )
        chunk_id = result.scalar_one()
        row.chunk_id = chunk_id
        inserted.append(row)
    await session.flush()
    return inserted


async def get_chunk(
    session: AsyncSession, chunk_id: uuid.UUID
) -> DocumentChunk | None:
    return await session.get(DocumentChunk, chunk_id)


async def retrieve_similar(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    query_embedding: list[float],
    embedding_model: str,
    limit: int = 6,
) -> list[tuple[DocumentChunk, float]]:
    """Exact cosine search filtered by organization. Returns (chunk, similarity)."""
    vec_literal = _vector_literal(query_embedding)
    result = await session.execute(
        text(
            """
            SELECT chunk_id,
                   1 - (embedding <=> CAST(:q AS vector)) AS similarity
            FROM document_chunks
            WHERE organization_id = :org_id
              AND embedding IS NOT NULL
              AND embedding_model = :model
            ORDER BY embedding <=> CAST(:q AS vector)
            LIMIT :lim
            """
        ),
        {
            "q": vec_literal,
            "org_id": organization_id,
            "model": embedding_model,
            "lim": limit,
        },
    )
    out: list[tuple[DocumentChunk, float]] = []
    for chunk_id, similarity in result.all():
        chunk = await session.get(DocumentChunk, chunk_id)
        if chunk is not None:
            out.append((chunk, float(similarity)))
    return out
