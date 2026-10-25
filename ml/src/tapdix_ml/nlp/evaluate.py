"""Evaluation helpers: accuracy / macro-F1, top confusions, and risk-coverage (when should we abstain?)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, f1_score

from tapdix_ml.data.taxonomy import category_of, skills_for
from tapdix_ml.nlp.classifier import ListingClassifier


def evaluate(
    model: ListingClassifier, texts: Sequence[str], truth: Sequence[str]
) -> dict[str, Any]:
    proba = model.predict_proba(texts)
    pred = [model.classes_[i] for i in proba.argmax(axis=1)]
    cat_true = [category_of(t) for t in truth]
    cat_p = model.category_proba(proba)
    cats = list(cat_p)
    cat_pred = [cats[i] for i in np.stack([cat_p[c] for c in cats], axis=1).argmax(axis=1)]
    conf = Counter((t, p) for t, p in zip(truth, pred, strict=True) if t != p)
    # matching-relevant view: a "wrong" problem type that needs the same repair skill still finds the right masters
    skill_hit = [
        bool(set(skills_for(t)) & set(skills_for(p))) for t, p in zip(truth, pred, strict=True)
    ]
    return {
        "n": len(truth),
        "problem_accuracy": round(accuracy_score(truth, pred), 4),
        "problem_macro_f1": round(f1_score(truth, pred, average="macro"), 4),
        "skill_hit_rate": round(float(np.mean(skill_hit)), 4),
        "category_accuracy": round(accuracy_score(cat_true, cat_pred), 4),
        "category_macro_f1": round(f1_score(cat_true, cat_pred, average="macro"), 4),
        "top_confusions": [{"true": t, "pred": p, "count": n} for (t, p), n in conf.most_common(5)],
    }


def max_category_confidence(model: ListingClassifier, texts: Sequence[str]) -> np.ndarray:
    cp = model.category_proba(model.predict_proba(texts))
    return np.max(np.stack(list(cp.values()), axis=1), axis=1)


def risk_coverage(
    model: ListingClassifier,
    texts: Sequence[str],
    truth: Sequence[str],
    thresholds: Sequence[float] = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9),
) -> list[dict[str, float]]:
    """If we only auto-accept predictions with category confidence >= t: what share do we keep, how accurate?"""
    proba = model.predict_proba(texts)
    cp = model.category_proba(proba)
    cats = list(cp)
    mat = np.stack([cp[c] for c in cats], axis=1)
    pred = np.array([cats[i] for i in mat.argmax(axis=1)])
    conf = mat.max(axis=1)
    cat_true = np.array([category_of(t) for t in truth])
    rows = []
    for t in thresholds:
        keep = conf >= t
        rows.append(
            {
                "threshold": t,
                "coverage": round(float(keep.mean()), 3),
                "accuracy_on_kept": round(float((pred[keep] == cat_true[keep]).mean()), 3)
                if keep.any()
                else float("nan"),
            }
        )
    return rows
