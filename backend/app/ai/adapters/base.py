from __future__ import annotations

from typing import Protocol


from dataclasses import dataclass


@dataclass(frozen=True)
class SourceCandidate:
    url: str
    title: str | None
    page_category: str
    reason: str | None = None


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
