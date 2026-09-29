"""One-off smoke check: chunking, Azure embeddings, document_chunks/pgvector."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main() -> None:
    from app.core.config import get_settings
    from app.ingestion.chunking import split_text
    from app.ai.adapters.embeddings import get_embedding_adapter
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    s = get_settings()
    print("CONFIG")
    print("  llm_model=", s.llm_model)
    print("  embedding_model=", s.embedding_model)
    print("  embedding_dimensions=", s.embedding_dimensions)
    print("  embedding_configured=", s.embedding_configured)

    sample = "University assessment modernization and LMS digital learning. " * 40
    chunks = split_text(
        sample, chunk_size=s.chunk_size_chars, chunk_overlap=s.chunk_overlap_chars
    )
    print("CHUNKING")
    print("  input_chars=", len(sample.strip()))
    print("  chunk_count=", len(chunks))
    print("  first_chunk_chars=", len(chunks[0]) if chunks else 0)

    print("EMBED_API")
    embedder = get_embedding_adapter(s)
    try:
        vecs = await embedder.embed_texts(
            ["EdTech procurement LMS assessment modernization"]
        )
        v = vecs[0]
        print("  ok=True")
        print("  vector_len=", len(v))
        print("  first3=", [round(x, 5) for x in v[:3]])
    except Exception as e:
        print("  ok=False")
        print("  error=", type(e).__name__, str(e)[:500])
        return

    engine = create_async_engine(s.database_url, pool_pre_ping=True)
    async with engine.connect() as conn:
        ext = await conn.scalar(
            text("SELECT extname FROM pg_extension WHERE extname='vector'")
        )
        print("PGVECTOR_EXT", ext)
        exists = await conn.scalar(text("SELECT to_regclass('public.document_chunks')"))
        print("TABLE_document_chunks", exists)
        if not exists:
            rev = await conn.scalar(text("SELECT version_num FROM alembic_version"))
            print("  MISSING — run alembic upgrade head")
            print("  alembic_version=", rev)
        else:
            cols = (
                await conn.execute(
                    text(
                        """
                        SELECT column_name, data_type, udt_name
                        FROM information_schema.columns
                        WHERE table_name='document_chunks'
                          AND column_name IN ('embedding','chunk_text','embedding_model')
                        ORDER BY column_name
                        """
                    )
                )
            ).all()
            for c in cols:
                print("  col", c[0], c[1], c[2])
            cnt = await conn.scalar(text("SELECT count(*) FROM document_chunks"))
            with_emb = await conn.scalar(
                text("SELECT count(*) FROM document_chunks WHERE embedding IS NOT NULL")
            )
            print("  row_count=", cnt, "with_embedding=", with_emb)
            lit = "[" + ",".join(str(float(x)) for x in v) + "]"
            sim = await conn.scalar(
                text("SELECT 1 - (CAST(:a AS vector) <=> CAST(:b AS vector))"),
                {"a": lit, "b": lit},
            )
            print(
                "  self_cosine_similarity=",
                float(sim) if sim is not None else None,
            )
    await engine.dispose()
    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
