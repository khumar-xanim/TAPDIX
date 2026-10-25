"""Port of legacy/ai/config/scoringConfig.ts (values copied verbatim)."""

from .types import ScoringWeights

DEFAULT_WEIGHTS = ScoringWeights(
    experience=0.25, quality=0.30, reliability=0.20, match=0.15, reputation=0.10
)

CATEGORY_WEIGHTS: dict[str, ScoringWeights] = {
    "Elektrik": ScoringWeights(0.30, 0.35, 0.20, 0.10, 0.05),
    "İT": ScoringWeights(0.20, 0.35, 0.15, 0.20, 0.10),
    "Tikinti": ScoringWeights(0.30, 0.30, 0.25, 0.10, 0.05),
    "Su": ScoringWeights(0.25, 0.30, 0.25, 0.15, 0.05),
}

# Defined in the TS config but never used by the engine (kept for completeness).
URGENCY_MULTIPLIERS = {"low": 1.0, "medium": 1.1, "high": 1.2}

LOCATION_BONUS = 5
CERTIFICATION_BONUS = 3
MIN_REVIEWS_FOR_CONFIDENCE = 5

RELATED_CATEGORIES: dict[str, list[str]] = {
    "Elektrik": ["Texniki xidmət", "Tikinti"],
    "Tikinti": ["Elektrik", "Su", "Boyama"],
    "İT": ["Texniki xidmət"],
    "Su": ["Tikinti"],
}
