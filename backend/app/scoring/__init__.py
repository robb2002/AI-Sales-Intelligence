"""Public scoring entrypoints. Keep this package free of AI imports."""

from app.scoring.v1 import ScoreBreakdown, ScoreInputSignal, score_opportunity

__all__ = ["ScoreBreakdown", "ScoreInputSignal", "score_opportunity"]
