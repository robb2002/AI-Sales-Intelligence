"""Rules opportunity score v1. No AI imports (AD-12)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

WEIGHT_VERSION = "v1"

EDTECH_TERMS = (
    "assessment",
    "testing",
    "lms",
    "learning",
    "online learning",
    "student information",
    "digital transformation",
    "modernization",
)


@dataclass(frozen=True)
class ScoreInputSignal:
    signal_type: str
    published_on: date | None
    snippet: str
    reliability_label: str | None  # official_api | official_website | other_public | None


@dataclass(frozen=True)
class ScoreBreakdown:
    value: int
    band: str
    weight_version: str
    procurement_relevance: int
    related_signal_strength: int
    assessment_edtech_relevance: int
    recency: int
    source_reliability: int


def score_opportunity(signals: list[ScoreInputSignal], *, now: date | None = None) -> ScoreBreakdown:
    if not signals:
        return ScoreBreakdown(0, "monitor", WEIGHT_VERSION, 0, 0, 0, 0, 0)

    types = {s.signal_type for s in signals}
    procurement = _procurement_relevance(types)
    related = _related_signal_strength(types)
    edtech = _edtech_relevance(" ".join(s.snippet for s in signals))
    recency = _recency(signals, today=now or datetime.now(timezone.utc).date())
    reliability = _source_reliability(signals)
    value = procurement + related + edtech + recency + reliability
    return ScoreBreakdown(
        value=value,
        band=_band(value),
        weight_version=WEIGHT_VERSION,
        procurement_relevance=procurement,
        related_signal_strength=related,
        assessment_edtech_relevance=edtech,
        recency=recency,
        source_reliability=reliability,
    )


def _procurement_relevance(types: set[str]) -> int:
    if "procurement" in types or "contract_renewal" in types:
        return 30
    if "funding_budget" in types:
        return 18
    soft = {
        "technology_initiative",
        "leadership_change",
        "strategic_announcement",
        "competitor_vendor",
    }
    if types and types <= soft:
        return 8
    return 0


def _related_signal_strength(types: set[str]) -> int:
    n = len(types)
    if n < 2:
        return 0
    # 8 for the second distinct type, +6 for each further, cap 25
    points = 8 + 6 * (n - 2)
    return min(25, points)


def _edtech_relevance(text: str) -> int:
    lower = text.lower()
    hits = sum(1 for term in EDTECH_TERMS if term in lower)
    if hits <= 0:
        return 0
    if hits <= 2:
        return 10
    return 20


def _recency(signals: list[ScoreInputSignal], *, today: date) -> int:
    dates = [s.published_on for s in signals if s.published_on is not None]
    if not dates:
        return 0
    newest = max(dates)
    age = (today - newest).days
    if age <= 30:
        return 15
    if age <= 90:
        return 10
    if age <= 180:
        return 5
    return 0


def _source_reliability(signals: list[ScoreInputSignal]) -> int:
    mapping = {"official_api": 10, "official_website": 6, "other_public": 3}
    best = 0
    for s in signals:
        best = max(best, mapping.get(s.reliability_label or "", 0))
    return best


def _band(value: int) -> str:
    if value >= 75:
        return "high"
    if value >= 50:
        return "medium"
    if value >= 25:
        return "low"
    return "monitor"
