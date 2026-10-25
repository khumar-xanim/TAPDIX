"""1:1 port of legacy/ai (ScoreCalculator, DataProcessor, WorkerScoringModel, RecommendationEngine).

Parity rules (JS -> Python) that matter for exact reproduction:
  * Math.round rounds .5 UP (Python's round() is banker's) -> js_round
  * Number.toFixed(1) picks the larger n on exact ties (4.25 -> "4.3") -> to_fixed1
  * Python 3.12 sum() uses compensated summation, JS reduce does not -> _sum (plain loop)
  * Number -> string drops ".0" (5.0 -> "5") -> js_num
  * Date.now() is injected (as_of) so results are reproducible
Intentionally NOT ported: unused helpers (calculateCommunicationScore,
calculateProfessionalismScore, analyzeClientSatisfaction) and in-place array mutation
(documented in the audit).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from .legacy_config import (
    CATEGORY_WEIGHTS,
    CERTIFICATION_BONUS,
    DEFAULT_WEIGHTS,
    LOCATION_BONUS,
    MIN_REVIEWS_FOR_CONFIDENCE,
    RELATED_CATEGORIES,
)
from .types import Breakdown, JobListing, Recommendation, Review, ScoringResult, WorkerProfile

Trend = Literal["improving", "stable", "declining"]
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MS = timedelta(milliseconds=1)


# ---------------------------------------------------------------- JS-semantics helpers
def js_round(x: float) -> int:
    return math.floor(x + 0.5)


def to_fixed1(x: float) -> str:
    return str(Decimal(x).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def js_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else repr(float(x))


def _sum(values) -> float:
    total = 0.0
    for v in values:
        total = total + v
    return total


def _ms(dt: datetime) -> int:
    return (dt - _EPOCH) // _MS


def _r1(x: float) -> float:
    return js_round(x * 10) / 10


# ---------------------------------------------------------------- ScoreCalculator
def experience_score(w: WorkerProfile) -> float:
    years = min(w.experience * 8, 50)
    jobs = min(w.completed_jobs * 0.5, 30)
    ratio = w.experience / max(w.age - 18, 1)
    consistency = min(ratio * 40, 20)
    return years + jobs + consistency


def quality_score(w: WorkerProfile) -> float:
    if len(w.reviews) == 0:
        return 50
    n = len(w.reviews)
    avg_quality = _sum(r.quality for r in w.reviews) / n
    avg_rating = _sum(r.rating for r in w.reviews) / n
    return (avg_quality / 5) * 50 + (avg_rating / 5) * 50


def reliability_score(w: WorkerProfile, as_of_ms: int) -> float:
    success = w.success_rate
    response = max(0, 100 - (w.response_time / 60) * 10)
    recent = [r for r in w.reviews if (as_of_ms - _ms(r.date)) / (1000 * 60 * 60 * 24) <= 90]
    consistency = 20 if len(recent) >= 3 else len(recent) * 6.67
    return (success * 0.5) + (response * 0.3) + (consistency * 0.2)


def reputation_score(w: WorkerProfile) -> float:
    base = (w.rating / 5) * 60
    count = min(len(w.reviews) * 2, 20)
    cert = min(len(w.certifications) * 5, 20)
    return base + count + cert


# ---------------------------------------------------------------- DataProcessor
def category_match(w: WorkerProfile, job: JobListing) -> float:
    if w.category == job.category:
        return 100
    if job.category in RELATED_CATEGORIES.get(w.category, []):
        return 50
    return 0


def location_match(worker_location: str, job_location: str) -> bool:
    a, b = worker_location.lower(), job_location.lower()
    return a.find(b) != -1 or b.find(a) != -1


def complexity_match(w: WorkerProfile, job: JobListing) -> float:
    required = math.ceil(job.complexity / 2)
    if w.experience >= required * 2:
        return 100
    if w.experience >= required:
        return 80
    if w.experience >= required * 0.7:
        return 60
    return 30


def analyze_trend(reviews: list[Review]) -> Trend:
    if len(reviews) < 3:
        return "stable"
    ordered = sorted(
        reviews, key=lambda r: -_ms(r.date)
    )  # stable, newest first (copy: no mutation)
    recent, older = ordered[:3], ordered[3:6]
    if len(older) == 0:
        return "stable"
    diff = _sum(r.rating for r in recent) / len(recent) - _sum(r.rating for r in older) / len(older)
    if diff > 0.3:
        return "improving"
    if diff < -0.3:
        return "declining"
    return "stable"


# ---------------------------------------------------------------- WorkerScoringModel
def _confidence(w: WorkerProfile) -> float:
    c = 50.0
    n = len(w.reviews)
    if n >= MIN_REVIEWS_FOR_CONFIDENCE * 2:
        c += 30
    elif n >= MIN_REVIEWS_FOR_CONFIDENCE:
        c += 20
    else:
        c += n * 3
    c += min(w.completed_jobs * 0.5, 15)
    c += min(w.experience * 0.5, 5)
    return min(100, c)


def _recommendation(score: float, confidence: float) -> Recommendation:
    if score >= 85 and confidence >= 70:
        return "highly_recommended"
    if score >= 70 and confidence >= 60:
        return "recommended"
    if score >= 55:
        return "suitable"
    return "not_recommended"


def _reasoning(w: WorkerProfile, job: JobListing, b: Breakdown, trend: Trend) -> list[str]:
    out: list[str] = []
    if b.experience_score >= 80:
        out.append(
            f"{js_num(w.experience)} illik təcrübəsi və "
            f"{js_num(w.completed_jobs)} tamamlanmış işi var"
        )
    elif b.experience_score >= 60:
        out.append("Orta səviyyəli təcrübəyə malikdir")
    if b.quality_score >= 85:
        out.append(f"Yüksək keyfiyyətli iş göstəriciləri ({to_fixed1(w.rating)}/5.0)")
    elif b.quality_score < 60:
        out.append("Keyfiyyət göstəriciləri inkişafa ehtiyac göstərir")
    if b.match_score >= 80:
        out.append("İşin tələblərinə tam uyğundur")
    elif b.match_score < 50:
        out.append("İş tələbləri ilə tam uyğun olmaya bilər")
    if trend == "improving":
        out.append("Son dövrdə performansı yüksəlməkdədir")
    elif trend == "declining":
        out.append("Son dövrdə performansda azalma müşahidə olunur")
    if b.reliability_score >= 80:
        out.append("Yüksək etibarlılıq və vaxtında çatdırılma göstəriciləri")
    if len(w.certifications) > 0:
        out.append(f"{len(w.certifications)} sertifikata malikdir")
    if location_match(w.location, job.location):
        out.append("İşin ərazisində yerləşir")
    return out


def score_worker(w: WorkerProfile, job: JobListing, as_of: datetime | None = None) -> ScoringResult:
    as_of_ms = _ms(as_of or datetime.now(UTC))
    wt = CATEGORY_WEIGHTS.get(job.category) or DEFAULT_WEIGHTS

    exp = experience_score(w)
    qual = quality_score(w)
    rel = reliability_score(w, as_of_ms)
    rep = reputation_score(w)
    match = (category_match(w, job) * 0.7) + (complexity_match(w, job) * 0.3)

    bonus = 0
    if location_match(w.location, job.location):
        bonus += LOCATION_BONUS
    if len(w.certifications) > 0:
        bonus += CERTIFICATION_BONUS * len(w.certifications)

    total = min(
        100,
        (exp * wt.experience)
        + (qual * wt.quality)
        + (rel * wt.reliability)
        + (match * wt.match)
        + (rep * wt.reputation)
        + bonus,
    )
    trend = analyze_trend(w.reviews)
    adj = -3 if trend == "declining" else (2 if trend == "improving" else 0)
    adjusted = max(0, min(100, total + adj))

    conf = _confidence(w)
    raw = Breakdown(exp, qual, rel, match, rep)
    return ScoringResult(
        worker_id=w.id,
        total_score=_r1(adjusted),
        breakdown=Breakdown(_r1(exp), _r1(qual), _r1(rel), _r1(match), _r1(rep)),
        confidence=_r1(conf),
        recommendation=_recommendation(adjusted, conf),
        reasoning=_reasoning(w, job, raw, trend),
    )


# ---------------------------------------------------------------- RecommendationEngine
def recommend_workers_for_job(
    workers: list[WorkerProfile], job: JobListing, limit: int = 10, as_of: datetime | None = None
) -> list[ScoringResult]:
    scored = [score_worker(w, job, as_of) for w in workers]
    return sorted(scored, key=lambda r: -r.total_score)[:limit]  # stable, like JS sort


def get_personalized_recommendations(
    workers: list[WorkerProfile], client_history: list[JobListing], limit: int = 5
) -> list[WorkerProfile]:
    if len(client_history) == 0:
        return sorted(workers, key=lambda w: -w.rating)[:limit]
    freq: dict[str, int] = {}
    for job in client_history:
        freq[job.category] = freq.get(job.category, 0) + 1
    preferred = [c for c, _ in sorted(freq.items(), key=lambda kv: -kv[1])[:3]]
    return sorted((w for w in workers if w.category in preferred), key=lambda w: -w.rating)[:limit]


def find_similar_successful_workers(
    target: JobListing, all_workers: list[WorkerProfile], limit: int = 5
) -> list[WorkerProfile]:
    def s(w: WorkerProfile) -> float:
        return (w.experience * 0.3) + (w.rating * 20) + (w.completed_jobs * 0.1)

    pool = [
        w
        for w in all_workers
        if w.category == target.category and w.completed_jobs > 0 and w.rating >= 4.0
    ]
    return sorted(pool, key=lambda w: -s(w))[:limit]
