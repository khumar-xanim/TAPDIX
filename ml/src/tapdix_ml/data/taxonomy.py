"""Loaders for the single source of truth: ml/data/taxonomy/*.json (also used to seed SQL)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[3] / "data"  # <repo>/ml/data


def _load(rel: str) -> dict[str, Any]:
    return json.loads((DATA_DIR / rel).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    return _load("taxonomy/taxonomy.json")


@lru_cache(maxsize=1)
def load_phrasebank() -> dict[str, Any]:
    return _load("taxonomy/phrasebank.json")


@lru_cache(maxsize=1)
def problem_index() -> dict[str, dict[str, Any]]:
    """problem_type code -> {category, name_en, name_az, skills, price_azn, urgency_probs, risk_flags}."""
    out: dict[str, dict[str, Any]] = {}
    for cat in load_taxonomy()["categories"]:
        for p in cat["problem_types"]:
            out[p["code"]] = {**p, "category": cat["slug"]}
    return out


def category_slugs() -> list[str]:
    return [c["slug"] for c in load_taxonomy()["categories"]]


def problem_codes() -> list[str]:
    return list(problem_index())


def category_of(problem_code: str) -> str:
    return problem_index()[problem_code]["category"]


def skills_for(problem_code: str) -> list[str]:
    return list(problem_index()[problem_code]["skills"])
