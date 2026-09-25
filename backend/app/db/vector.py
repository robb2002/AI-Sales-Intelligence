"""SQLAlchemy Vector type that does not require the pgvector Python package.

Stores embeddings as float lists; binds them as pgvector literal strings for asyncpg.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim

    def get_col_spec(self, **_: Any) -> str:
        if self.dim is not None:
            return f"vector({self.dim})"
        return "vector"

    def bind_processor(self, _dialect: Any):
        def process(value: list[float] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(str(float(x)) for x in value) + "]"

        return process

    def result_processor(self, _dialect: Any, _coltype: Any):
        def process(value: Any) -> list[float] | None:
            if value is None:
                return None
            if isinstance(value, list):
                return [float(x) for x in value]
            if isinstance(value, str):
                inner = value.strip()
                if inner.startswith("[") and inner.endswith("]"):
                    inner = inner[1:-1]
                if not inner:
                    return []
                return [float(x) for x in inner.split(",")]
            return list(value)

        return process
