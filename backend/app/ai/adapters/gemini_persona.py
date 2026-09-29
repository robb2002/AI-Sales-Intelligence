"""Gemini adapter for Sales Persona only.

Advisor, scan extraction, and embeddings stay on Azure. This module is used only when
PERSONA_GEMINI_API_KEY is set. On Gemini failure, falls back to Azure so demos stay up.

Latency: prefer models.generate_content (fast JSON path). interactions.create is tried only
when generate_content fails, and Azure is the last resort — never wait on long 503 retries.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from google import genai
from google.genai import types

from app.ai.persona_prompts import (
    PERSONA_SYSTEM,
    build_persona_user_prompt,
    parse_persona_answer,
)
from app.core.config import Settings

logger = logging.getLogger(__name__)

# Keep Persona snappy; long answers still fit in ~3–8 blocks.
_MAX_OUTPUT_TOKENS = 1400
_HTTP_TIMEOUT_MS = 45_000


class GeminiPersonaAdapter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = genai.Client(
            api_key=settings.persona_gemini_api_key.strip(),
            http_options=types.HttpOptions(
                timeout=_HTTP_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=2, initial_delay=0.5, max_delay=4.0),
            ),
        )
        self._azure = None
        if settings.llm_configured:
            from app.ai.adapters.azure_openai import create_llm_adapter

            self._azure = create_llm_adapter(settings)

    async def compose_persona_answer(
        self,
        *,
        mode: str,
        message: str,
        context_block: str,
        history_block: str,
        scope_note: str = "",
    ) -> dict[str, Any]:
        if not self._settings.persona_gemini_configured:
            raise RuntimeError("Persona Gemini is not configured")
        user = build_persona_user_prompt(
            mode=mode,
            message=message,
            context_block=context_block,
            history_block=history_block,
            scope_note=scope_note,
        )
        try:
            content = await asyncio.to_thread(self._generate, user)
            parsed = parse_persona_answer(content)
            if parsed.get("blocks"):
                return parsed
            logger.warning("Persona Gemini returned no blocks; trying Azure fallback")
        except Exception:
            logger.exception("Persona Gemini failed; trying Azure fallback")

        if self._azure is None:
            raise RuntimeError("Persona Gemini failed and Azure is not configured")
        return await self._azure.compose_persona_answer(
            mode=mode,
            message=message,
            context_block=context_block,
            history_block=history_block,
            scope_note=scope_note,
        )

    def _generate(self, user: str) -> str:
        model = self._settings.persona_gemini_model.strip()
        prompt = f"{PERSONA_SYSTEM}\n\n{user}"
        # Fast path first: generate_content with JSON mime (avoids experimental Interactions
        # retries that can stall for minutes on 503).
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=_MAX_OUTPUT_TOKENS,
                    temperature=0.4,
                    response_mime_type="application/json",
                ),
            )
            text = _generate_content_text(response)
            if text.strip():
                return text
            logger.warning("Persona Gemini generate_content empty; trying interactions.create")
        except Exception:
            logger.exception(
                "Persona Gemini generate_content failed; trying interactions.create once"
            )
        interaction = self._client.interactions.create(model=model, input=prompt)
        return _interaction_text(interaction)


def _interaction_text(interaction: Any) -> str:
    for attr in ("output_text", "text"):
        value = getattr(interaction, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    outputs = getattr(interaction, "outputs", None) or getattr(interaction, "output", None)
    if isinstance(outputs, list):
        parts: list[str] = []
        for item in outputs:
            if isinstance(item, str) and item.strip():
                parts.append(item)
                continue
            text = getattr(item, "text", None)
            if isinstance(text, str) and text.strip():
                parts.append(text)
                continue
            if isinstance(item, dict):
                t = item.get("text")
                if isinstance(t, str) and t.strip():
                    parts.append(t)
                    continue
                content = item.get("content")
                if isinstance(content, str) and content.strip():
                    parts.append(content)
        if parts:
            return "\n".join(parts)
    if isinstance(outputs, str) and outputs.strip():
        return outputs
    return str(interaction) if interaction is not None else ""


def _generate_content_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    return str(response) if response is not None else ""


def create_persona_llm(settings: Settings):
    """Pick Gemini for Persona when configured; otherwise Azure (same as scan/Advisor)."""
    if settings.persona_gemini_configured:
        return GeminiPersonaAdapter(settings)
    from app.ai.adapters.azure_openai import create_llm_adapter

    return create_llm_adapter(settings)
