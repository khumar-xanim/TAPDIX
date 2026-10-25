"""Decide what to trust: the customer's text, the photo, or both - and when to ask the customer.

The detector itself (YOLO) lives elsewhere; this module consumes its output (list of Detection), so the decision
logic is testable without a GPU, weights or photos.

Policy (all thresholds in FusionConfig, tuned on the text model's risk-coverage curve, see ml/reports):
  text confident, no photo/weak photo     -> use TEXT
  text vague, photo confident              -> use PHOTO            ("announcement wasn't enough, use the photo")
  both confident and agree                 -> TEXT+PHOTO, confidence boosted
  both confident and disagree              -> the clearly stronger one wins, otherwise ASK the customer
  neither confident                        -> ASK (and ask for a photo if none was uploaded)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from tapdix_ml.data.taxonomy import DATA_DIR, load_taxonomy, problem_index
from tapdix_ml.nlp.classifier import TextPrediction

Source = Literal["text", "photo", "text+photo", "ask_user"]


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: tuple[float, float, float, float] | None = None  # x1, y1, x2, y2 (normalised), optional


@dataclass(frozen=True)
class VisionPrediction:
    category: str | None
    category_conf: float
    problem_hints: dict[str, float] = field(default_factory=dict)  # problem_type -> score
    detections: tuple[Detection, ...] = ()


@dataclass(frozen=True)
class FusionConfig:
    text_category_min: float = (
        0.30  # 61% of clear listings kept at 98.7% accuracy; 3% of vague ones slip through
    )
    text_problem_min: float = 0.30
    vision_min: float = 0.50
    conflict_margin: float = 0.20
    agreement_boost: float = 0.50


DEFAULT_CONFIG = FusionConfig()


@dataclass(frozen=True)
class FusionDecision:
    category: str | None
    problem_type: str | None
    source: Source
    confidence: float
    reasons: list[str]
    request_photo: bool = False
    clarification_az: str | None = None
    alternatives: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def load_vision_classes() -> dict:
    return json.loads((DATA_DIR / "vision" / "classes.json").read_text(encoding="utf-8"))


def _noisy_or(values: list[float]) -> float:
    p = 1.0
    for v in values:
        p *= 1.0 - min(max(v, 0.0), 1.0)
    return 1.0 - p


def vision_from_detections(dets: list[Detection]) -> VisionPrediction:
    """Turn raw detector output into a category guess + problem-type hints.

    category score = P(at least one object of that category really is there) (noisy-OR), then penalised when a
    second category competes. Heuristic until we can calibrate on real labelled photos.
    """
    classes = load_vision_classes()
    per_cat: dict[str, list[float]] = {}
    per_problem: dict[str, list[float]] = {}
    for d in dets:
        if d.label in classes["objects"]:
            per_cat.setdefault(classes["objects"][d.label]["category"], []).append(d.confidence)
        elif d.label in classes["defects"]:
            for p in classes["defects"][d.label]["problem_hints"]:
                per_problem.setdefault(p, []).append(d.confidence)
    if not per_cat:
        return VisionPrediction(None, 0.0, {}, tuple(dets))
    scores = {c: _noisy_or(v) for c, v in per_cat.items()}
    top = max(scores, key=lambda k: scores[k])
    share = scores[top] / sum(scores.values())
    hints = {
        p: _noisy_or(v) for p, v in per_problem.items() if problem_index()[p]["category"] == top
    }
    return VisionPrediction(
        top,
        round(scores[top] * share, 4),
        dict(sorted(hints.items(), key=lambda kv: -kv[1])),
        tuple(dets),
    )


def _name_az(slug: str) -> str:
    return next(c["name_az"] for c in load_taxonomy()["categories"] if c["slug"] == slug)


def _best_hint(v: VisionPrediction | None, minimum: float) -> tuple[str | None, float]:
    if v and v.problem_hints:
        p, s = next(iter(v.problem_hints.items()))
        if s >= minimum:
            return p, s
    return None, 0.0


def fuse(
    text: TextPrediction | None, vision: VisionPrediction | None, cfg: FusionConfig = DEFAULT_CONFIG
) -> FusionDecision:
    t_ok = text is not None and text.category_prob >= cfg.text_category_min
    v_ok = (
        vision is not None
        and vision.category is not None
        and vision.category_conf >= cfg.vision_min
    )
    has_photo = vision is not None and len(vision.detections) > 0
    hint, hint_s = _best_hint(vision, cfg.vision_min * 0.6)

    if t_ok and v_ok:
        assert text is not None and vision is not None
        if text.category == vision.category:
            problem = text.problem_type if text.problem_prob >= cfg.text_problem_min else hint
            conf = (
                text.category_prob
                + (1 - text.category_prob) * vision.category_conf * cfg.agreement_boost
            )
            why = ["Mətn və şəkil eyni kateqoriyanı göstərir"]
            if problem == hint and hint is not None and problem != text.problem_type:
                why.append("Dəqiq problem şəkildən müəyyən edildi")
            return FusionDecision(
                text.category, problem, "text+photo", round(min(conf, 0.99), 3), why
            )
        gap = text.category_prob - vision.category_conf
        if gap >= cfg.conflict_margin:
            return FusionDecision(
                text.category,
                text.problem_type if text.problem_prob >= cfg.text_problem_min else None,
                "text",
                round(text.category_prob, 3),
                ["Mətn və şəkil fərqlidir; mətn daha əminlidir"],
                alternatives=[vision.category or ""],
            )
        if -gap >= cfg.conflict_margin:
            return FusionDecision(
                vision.category,
                hint,
                "photo",
                round(vision.category_conf, 3),
                ["Mətn və şəkil fərqlidir; şəkil daha əminlidir"],
                alternatives=[text.category],
            )
        a, b = text.category, vision.category or ""
        return FusionDecision(
            None,
            None,
            "ask_user",
            round(max(text.category_prob, vision.category_conf), 3),
            ["Mətn və şəkil bərabər əminliklə fərqli kateqoriya göstərir"],
            clarification_az=f"Bu problem {_name_az(a)} yoxsa {_name_az(b)} ilə bağlıdır?",
            alternatives=[a, b],
        )
    if t_ok:
        assert text is not None
        return FusionDecision(
            text.category,
            text.problem_type if text.problem_prob >= cfg.text_problem_min else None,
            "text",
            round(text.category_prob, 3),
            ["Elanın mətni kifayət qədər aydındır"],
        )
    if v_ok:
        assert vision is not None
        why = (
            ["Mətn qeyri-müəyyəndir, şəkildən istifadə olundu"]
            if text is not None
            else ["Mətn yoxdur, şəkildən istifadə olundu"]
        )
        return FusionDecision(vision.category, hint, "photo", round(vision.category_conf, 3), why)

    alts = [c for c, p in (text.category_probs.items() if text else []) if p >= 0.15][:2]
    if len(alts) == 2:
        question = f"Bu problem {_name_az(alts[0])} yoxsa {_name_az(alts[1])} ilə bağlıdır?"
    elif has_photo:
        question = "Problemi bir az ətraflı yazın."
    else:
        question = "Problemi bir az ətraflı yazın və ya şəkil əlavə edin."
    return FusionDecision(
        None,
        None,
        "ask_user",
        round(text.category_prob if text else 0.0, 3),
        ["Nə mətn, nə də şəkil kifayət qədər aydın deyil"],
        request_photo=not has_photo,
        clarification_az=question,
        alternatives=alts,
    )
