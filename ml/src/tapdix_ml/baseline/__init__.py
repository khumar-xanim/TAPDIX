"""Baseline = the legacy hand-weighted TypeScript scorer, ported 1:1 to Python.

Every ML model we build must beat this on the offline metrics (NDCG@k, MRR).
It is intentionally NOT fixed: known defects are documented in docs/legacy_engine_audit.md
and kept so the comparison is against what actually shipped.
"""

from .legacy_scorer import (
    find_similar_successful_workers,
    get_personalized_recommendations,
    recommend_workers_for_job,
    score_worker,
)
from .types import JobListing, Review, ScoringResult, ScoringWeights, WorkerProfile

__all__ = [
    "JobListing",
    "Review",
    "ScoringResult",
    "ScoringWeights",
    "WorkerProfile",
    "find_similar_successful_workers",
    "get_personalized_recommendations",
    "recommend_workers_for_job",
    "score_worker",
]
