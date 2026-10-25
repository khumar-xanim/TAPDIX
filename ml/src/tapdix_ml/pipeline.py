"""End-to-end: listing (text [+ photo detections]) -> category/problem -> required skills -> ranked masters."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from tapdix_ml.matching import (
    Master,
    MatchResult,
    Need,
    rank_masters,
    skill_weights_from_prediction,
)
from tapdix_ml.nlp.classifier import ListingClassifier, TextPrediction, listing_text
from tapdix_ml.vision.fusion import (
    DEFAULT_CONFIG,
    Detection,
    FusionConfig,
    FusionDecision,
    fuse,
    vision_from_detections,
)


@dataclass(frozen=True)
class Recommendation:
    decision: FusionDecision
    text: TextPrediction
    matches: list[MatchResult]


def load_masters(path: Path) -> list[Master]:
    out = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            out.append(
                Master(
                    master_id=r["master_id"],
                    main_category=r["main_category"],
                    skills=frozenset(json.loads(r["skills"])),
                    years_experience=float(r["years_experience"]),
                    average_rating=float(r["average_rating"]),
                    rating_count=int(r["rating_count"]),
                    verification_status=r["verification_status"],
                    is_available=r["is_available"] == "True",
                    accepts_emergency_jobs=r["accepts_emergency_jobs"] == "True",
                    areas=tuple((a["city"], a["district"]) for a in json.loads(r["service_areas"])),
                )
            )
    return out


def recommend(
    model: ListingClassifier,
    masters: list[Master],
    *,
    title: str,
    description: str,
    city: str,
    district: str,
    urgency: str = "Normal",
    detections: list[Detection] | None = None,
    k: int = 5,
    cfg: FusionConfig = DEFAULT_CONFIG,
) -> Recommendation:
    text = model.predict(listing_text(title, description))
    vision = vision_from_detections(detections) if detections else None
    decision = fuse(text, vision, cfg)
    if decision.category is None:
        return Recommendation(decision, text, [])
    need = Need(
        decision.category, skill_weights_from_prediction(text, decision), city, district, urgency
    )
    return Recommendation(decision, text, rank_masters(masters, need, k))
