"""v0 master matcher: explainable, hand-weighted - a BASELINE for the learned ranker, like the legacy scorer.

Fixes the legacy defects that matter here: small-sample ratings are shrunk (one 5.0 review no longer beats fifty
4.8s), everything is deterministic (stable tie-break), and inputs are never mutated. Weights are NOT learned yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tapdix_ml.data.taxonomy import load_taxonomy, problem_index, skills_for
from tapdix_ml.nlp.classifier import TextPrediction
from tapdix_ml.vision.fusion import FusionDecision

W = {
    "skill": 0.40,
    "rating": 0.20,
    "experience": 0.10,
    "verification": 0.10,
    "urgency_fit": 0.10,
    "area": 0.10,
}
URGENT = {"Urgent", "Emergency"}


@dataclass(frozen=True)
class Master:
    master_id: str
    main_category: str
    skills: frozenset[str]
    years_experience: float
    average_rating: float
    rating_count: int
    verification_status: str
    is_available: bool
    accepts_emergency_jobs: bool
    areas: tuple[tuple[str, str], ...]  # (city, district)


@dataclass(frozen=True)
class Need:
    category: str
    skill_weights: dict[str, float]
    city: str
    district: str
    urgency: str = "Normal"


@dataclass(frozen=True)
class MatchResult:
    master_id: str
    score: float
    reasons: list[str] = field(default_factory=list)


def bayesian_rating(
    avg: float, n: int, prior_mean: float = 4.0, prior_weight: float = 5.0
) -> float:
    """Shrink towards the prior when there are few reviews (0 reviews -> prior_mean)."""
    return (avg * n + prior_mean * prior_weight) / (n + prior_weight)


def skill_weights_from_prediction(
    text: TextPrediction | None, decision: FusionDecision
) -> dict[str, float]:
    """Spread skill demand over the plausible problem types instead of betting on one."""
    weights: dict[str, float] = {}
    if decision.problem_type:
        for s in skills_for(decision.problem_type):
            weights[s] = weights.get(s, 0.0) + 1.0
    elif text is not None and decision.category:
        for code, p in text.top_k:
            if problem_index()[code]["category"] == decision.category:
                for s in skills_for(code):
                    weights[s] = weights.get(s, 0.0) + p
    if (
        not weights and decision.category
    ):  # photo-only / very uncertain: any skill of the trade, equally
        cat = next(c for c in load_taxonomy()["categories"] if c["slug"] == decision.category)
        weights = {s["code"]: 1.0 for s in cat["skills"]}
    return weights


def _skill_name_az(code: str) -> str:
    for c in load_taxonomy()["categories"]:
        for s in c["skills"]:
            if s["code"] == code:
                return s["name_az"]
    return code


def score_master(m: Master, need: Need) -> MatchResult | None:
    """None = excluded (unavailable, rejected, wrong city, or no relevant skill/trade)."""
    if not m.is_available or m.verification_status == "Rejected":
        return None
    same_district = (need.city, need.district) in m.areas
    same_city = any(c == need.city for c, _ in m.areas)
    if not same_city:
        return None
    total_w = sum(need.skill_weights.values()) or 1.0
    covered = {s: w for s, w in need.skill_weights.items() if s in m.skills}
    coverage = sum(covered.values()) / total_w
    if coverage == 0:
        if m.main_category != need.category:
            return None
        coverage = 0.15  # same trade, but no listed skill matches: weak candidate
    rating = (bayesian_rating(m.average_rating, m.rating_count) - 1) / 4
    verification = {"Verified": 1.0, "Pending": 0.4}.get(m.verification_status, 0.0)
    urgency_fit = 1.0 if (need.urgency not in URGENT or m.accepts_emergency_jobs) else 0.0
    parts = {
        "skill": coverage,
        "rating": rating,
        "experience": min(m.years_experience, 10) / 10,
        "verification": verification,
        "urgency_fit": urgency_fit,
        "area": 1.0 if same_district else 0.5,
    }
    score = sum(W[k] * v for k, v in parts.items())
    reasons = [
        f"Bacarıq: {_skill_name_az(s)}" for s in sorted(covered, key=lambda k: -covered[k])[:2]
    ]
    reasons.append("Eyni rayon" if same_district else "Eyni şəhər")
    if verification == 1.0:
        reasons.append("Doğrulanmış usta")
    if need.urgency in URGENT and m.accepts_emergency_jobs:
        reasons.append("Təcili işlərə baxır")
    if m.rating_count:
        reasons.append(f"Reytinq {m.average_rating:.1f} ({m.rating_count} rəy)")
    return MatchResult(m.master_id, round(score, 4), reasons)


def rank_masters(masters: list[Master], need: Need, k: int = 10) -> list[MatchResult]:
    scored = [r for r in (score_master(m, need) for m in masters) if r is not None]
    by_id = {m.master_id: m for m in masters}
    # deterministic tie-break: more reviews first, then id
    return sorted(scored, key=lambda r: (-r.score, -by_id[r.master_id].rating_count, r.master_id))[
        :k
    ]
