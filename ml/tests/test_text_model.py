import json
from pathlib import Path

import pytest

from tapdix_ml.data.generate import generate_listings
from tapdix_ml.data.taxonomy import DATA_DIR
from tapdix_ml.nlp.classifier import ListingClassifier, listing_text
from tapdix_ml.nlp.evaluate import evaluate, max_category_confidence


@pytest.fixture(scope="module")
def trained():
    rows = [
        r
        for r in generate_listings(n_per_type=30, seed=11)
        if r["text_quality"] == "clear" and r["split"] == "train"
    ]
    return ListingClassifier().fit(
        [listing_text(r["title"], r["description"]) for r in rows],
        [r["labels"]["problem_type"] for r in rows],
    )


@pytest.fixture(scope="module")
def gold():
    return json.loads((DATA_DIR / "gold" / "gold.json").read_text(encoding="utf-8"))


def test_obvious_listings_get_the_right_category(trained) -> None:
    for text, cat in [
        ("Kran damır, mətbəxdə su sızır", "plumbing"),
        ("kondisioner soyutmur", "hvac_services"),
        ("qapi baglanib acar icerdedi", "locksmith"),
        ("Телевизор не включается", "electronics_repair"),
    ]:
        assert trained.predict(text).category == cat, text


def test_category_probability_is_sum_of_its_problem_probabilities(trained) -> None:
    p = trained.predict("rozetka işləmir, qığılcım çıxır")
    assert abs(sum(p.category_probs.values()) - 1) < 1e-6
    assert p.category_prob == max(p.category_probs.values())


def test_keywords_explain_the_prediction(trained) -> None:
    words = {w for w, _ in trained.predict("Kran damır, su axır", n_keywords=5).keywords}
    assert words & {"kran", "damir"}


def test_independent_gold_set_generalisation_floor(trained, gold) -> None:
    ev = evaluate(
        trained, [g["text"] for g in gold["clear"]], [g["problem_type"] for g in gold["clear"]]
    )
    assert ev["category_accuracy"] >= 0.85, (
        ev
    )  # measured ~0.99 with the full dataset; floor allows the small fixture
    assert ev["skill_hit_rate"] >= ev["problem_accuracy"]


def test_vague_texts_get_lower_confidence_than_clear_ones(trained, gold) -> None:
    clear = max_category_confidence(trained, [g["text"] for g in gold["clear"]])
    vague = max_category_confidence(trained, [g["text"] for g in gold["vague"]])
    assert float(clear.mean()) > float(vague.mean()) + 0.25


def test_model_round_trips_to_disk(trained, tmp_path: Path) -> None:
    trained.save(tmp_path / "m.joblib")
    again = ListingClassifier.load(tmp_path / "m.joblib")
    assert (
        again.predict("boyler isitmir").problem_type
        == trained.predict("boyler isitmir").problem_type
    )
