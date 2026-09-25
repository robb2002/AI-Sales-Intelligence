from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger("app.ai.embeddings")


class EmbeddingAdapter(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""
        ...


class AzureOpenAIEmbeddingAdapter:
    """Azure OpenAI embeddings via the embeddings deployment (not chat)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self._settings.embedding_configured:
            raise RuntimeError("Azure embeddings are not configured")
        cleaned = [t.strip() for t in texts if t and t.strip()]
        if not cleaned:
            return []

        endpoint = self._settings.azure_openai_endpoint.rstrip("/")
        deployment = self._settings.embedding_model
        api_version = self._settings.azure_openai_api_version
        url = (
            f"{endpoint}/openai/deployments/{deployment}/embeddings"
            f"?api-version={api_version}"
        )
        vectors: list[list[float]] = []
        batch_size = 16
        async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
            for i in range(0, len(cleaned), batch_size):
                batch = cleaned[i : i + batch_size]
                response = await client.post(
                    url,
                    headers={
                        "api-key": self._settings.llm_api_key,
                        "Content-Type": "application/json",
                    },
                    json={"input": batch},
                )
                if response.status_code >= 400:
                    logger.error(
                        "Azure embedding failed status=%s body=%s",
                        response.status_code,
                        response.text[:500],
                    )
                    response.raise_for_status()
                payload = response.json()
                data = payload.get("data") or []
                data_sorted = sorted(data, key=lambda item: int(item.get("index", 0)))
                for item in data_sorted:
                    emb = item.get("embedding")
                    if not isinstance(emb, list):
                        raise RuntimeError("Embedding response missing vector")
                    if len(emb) != self._settings.embedding_dimensions:
                        raise RuntimeError(
                            f"Embedding width {len(emb)} != "
                            f"{self._settings.embedding_dimensions}"
                        )
                    vectors.append([float(x) for x in emb])
        if len(vectors) != len(cleaned):
            raise RuntimeError("Embedding count mismatch")
        return vectors


def get_embedding_adapter(settings: Settings) -> EmbeddingAdapter:
    return AzureOpenAIEmbeddingAdapter(settings)
