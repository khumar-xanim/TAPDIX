from pathlib import Path

import pytest

from tapdix_ml.data.generate import generate_listings, write_dataset
from tapdix_ml.data.taxonomy_sql import build
from tapdix_ml.nlp.classifier import ListingClassifier, listing_text
from tapdix_ml.pipeline import load_masters, recommend
from tapdix_ml.vision.fusion import Detection

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    d = tmp_path_factory.mktemp("ds")
    write_dataset(d, n_per_type=3, n_masters=150, seed=9)
    rows = [
        r
        for r in generate_listings(n_per_type=30, seed=11)
        if r["text_quality"] == "clear" and r["split"] == "train"
    ]
    model = ListingClassifier().fit(
        [listing_text(r["title"], r["description"]) for r in rows],
        [r["labels"]["problem_type"] for r in rows],
    )
    return model, load_masters(d / "masters.csv")


def test_end_to_end_text_only(world) -> None:
    model, masters = world
    rec = recommend(
        model,
        masters,
        title="Mətbəx kranı su axıdır",
        description="Kranın altından su damır.",
        city="Bakı",
        district="Nəsimi",
    )
    assert rec.decision.category == "plumbing" and rec.decision.source == "text"
    assert rec.matches and all(m.score > 0 for m in rec.matches)


def test_end_to_end_vague_text_uses_photo(world) -> None:
    model, masters = world
    rec = recommend(
        model,
        masters,
        title="Usta lazımdır",
        description="Şəkildə görünür, baxın.",
        city="Bakı",
        district="Nəsimi",
        detections=[Detection("ac_indoor_unit", 0.92), Detection("water_leak_stain", 0.7)],
    )
    assert rec.decision.source == "photo" and rec.decision.category == "hvac_services"


def test_end_to_end_unclear_returns_a_question_not_a_guess(world) -> None:
    model, masters = world
    rec = recommend(
        model,
        masters,
        title="Kömək",
        description="Salam, usta lazımdır.",
        city="Bakı",
        district="Nəsimi",
    )
    assert rec.decision.source == "ask_user" and rec.matches == [] and rec.decision.clarification_az


def test_committed_sql_seed_matches_the_taxonomy_json() -> None:
    """If this fails: python -m tapdix_ml.data.taxonomy_sql > db/seed_taxonomy.sql"""
    assert (REPO / "db" / "seed_taxonomy.sql").read_text(encoding="utf-8") == build()
