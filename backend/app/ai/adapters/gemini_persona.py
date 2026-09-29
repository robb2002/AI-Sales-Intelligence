"""Gemini adapter for Sales Persona only.

Advisor, scan extraction, and embeddings stay on Azure. This module is used only when
PERSONA_GEMINI_API_KEY is set. On Gemini failure, falls back to Azure so demos stay up.

Latency (2026-09-29): a second Gemini call (`interactions.create`) used to be tried after
`generate_content` failed. In practice it always failed too (free-tier rate limit or the same
"high demand" 503), so every Gemini failure was paying for two slow calls, each with its own
client-level retries, before ever reaching the working Azure fallback — well over a minute in
total. `generate_content` is now the only Gemini attempt, and the whole attempt is bounded by
`_GENERATE_TIMEOUT_SECONDS` so a stuck/overloaded Gemini falls back to Azure quickly instead of
however long the SDK's own retry/backoff takes.
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
# Ceiling on the whole Gemini attempt (including the client's own internal retries) before
# giving up and falling back to Azure. Comfortably covers a normal response; well under the
# multi-minute worst case an overloaded/rate-limited model can otherwise cause.
_GENERATE_TIMEOUT_SECONDS = 20.0


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
            content = await asyncio.wait_for(
                asyncio.to_thread(self._generate, user), timeout=_GENERATE_TIMEOUT_SECONDS
            )
            parsed = parse_persona_answer(content)
            if parsed.get("blocks"):
                return parsed
            logger.warning("Persona Gemini returned no blocks; trying Azure fallback")
        except asyncio.TimeoutError:
            logger.warning(
                "Persona Gemini timed out after %ss; trying Azure fallback",
                _GENERATE_TIMEOUT_SECONDS,
            )
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
        response = self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=_MAX_OUTPUT_TOKENS,
                temperature=0.4,
                response_mime_type="application/json",
            ),
        )
        return _generate_content_text(response)


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
