from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Recommendation = Literal["highly_recommended", "recommended", "suitable", "not_recommended"]


@dataclass(frozen=True)
class Review:
    client_id: str
    rating: float
    quality: float
    communication: float
    professionalism: float
    timeliness: float
    date: datetime  # timezone-aware


@dataclass(frozen=True)
class WorkerProfile:
    id: str
    category: str
    location: str
    age: float
    experience: float  # years
    completed_jobs: float
    rating: float  # 0-5
    success_rate: float  # 0-100
    response_time: float  # minutes
    certifications: list[str] = field(default_factory=list)
    reviews: list[Review] = field(default_factory=list)


@dataclass(frozen=True)
class JobListing:
    id: str
    category: str
    location: str
    complexity: float  # 1-10


@dataclass(frozen=True)
class ScoringWeights:
    experience: float
    quality: float
    reliability: float
    match: float
    reputation: float


@dataclass(frozen=True)
class Breakdown:
    experience_score: float
    quality_score: float
    reliability_score: float
    match_score: float
    reputation_score: float


@dataclass(frozen=True)
class ScoringResult:
    worker_id: str
    total_score: float
    breakdown: Breakdown
    confidence: float
    recommendation: Recommendation
    reasoning: list[str]
