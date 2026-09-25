from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SourceCandidate:
    url: str
    title: str | None
    page_category: str
    reason: str | None = None


@dataclass(frozen=True)
class ExtractedSignalCandidate:
    signal_type: str
    title: str
    summary: str
    snippet: str
    relationship: str
    source_url: str | None = None


class LLMProviderAdapter(Protocol):
    async def propose_organization_urls(
        self,
        *,
        organization_name: str,
        official_domain: str,
        candidate_urls: list[str] | None = None,
    ) -> list[SourceCandidate]:
        """Select/classify candidates. Must not invent URLs outside candidate_urls."""
        ...

    async def extract_signals(
        self,
        *,
        organization_name: str,
        organization_id: str,
        source_name: str,
        source_url: str,
        title: str | None,
        body_text: str,
        published_on: str | None,
    ) -> list[ExtractedSignalCandidate]:
        """Extract zero or more signal candidates from one document. Snippets must be
        verbatim spans from body_text; the caller validates."""
        ...

    async def correlate_signals(
        self,
        *,
        organization_name: str,
        signals: list[dict[str, str]],
    ) -> str:
        """Write an INTERPRETATION correlation reason from stored snippets only.
        Must not invent facts or predict solicitations."""
        ...

    async def explain_score(
        self,
        *,
        organization_name: str,
        score_value: int,
        score_band: str,
        weight_version: str,
        factors: dict[str, int],
        signal_types: list[str],
        snippets: list[str],
    ) -> str:
        """Explain a rules-computed score. Must repeat score_value and score_band.
        Must not invent or alter the numeric total."""
        ...
