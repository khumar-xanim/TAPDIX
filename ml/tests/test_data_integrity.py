import json

from tapdix_ml.data.taxonomy import (
    DATA_DIR,
    category_of,
    category_slugs,
    load_phrasebank,
    load_taxonomy,
    problem_codes,
    problem_index,
    skills_for,
)
from tapdix_ml.text.normalize import normalize
from tapdix_ml.vision.fusion import load_vision_classes


def test_eight_core_categories_with_seven_problem_types_each() -> None:
    assert len(category_slugs()) == 8
    assert len(problem_codes()) == 56
    for c in load_taxonomy()["categories"]:
        assert len(c["problem_types"]) == 7, c["slug"]


def test_every_problem_type_uses_existing_skills_and_valid_priors() -> None:
    for cat in load_taxonomy()["categories"]:
        skills = {s["code"] for s in cat["skills"]}
        for p in cat["problem_types"]:
            assert p["skills"] and set(p["skills"]) <= skills, p["code"]
            assert abs(sum(p["urgency_probs"].values()) - 1) < 1e-9, p["code"]
            assert 0 < p["price_azn"][0] < p["price_azn"][1], p["code"]
    assert category_of("faucet_leak") == "plumbing" and "faucet_repair" in skills_for("faucet_leak")


def test_phrasebank_covers_every_problem_type_with_5_az_and_2_ru_bundles() -> None:
    bank = load_phrasebank()["bundles"]
    assert set(bank) == set(problem_index())
    for code, b in bank.items():
        assert len(b["az"]) == 5 and len(b["ru"]) == 2, code


def test_gold_set_is_valid_and_independent_of_the_phrasebank() -> None:
    gold = json.loads((DATA_DIR / "gold" / "gold.json").read_text(encoding="utf-8"))
    valid = {(problem_index()[c]["category"], c) for c in problem_index()}
    for g in gold["clear"]:
        assert (g["category"], g["problem_type"]) in valid, g
    seen = {
        normalize(s)
        for v in load_phrasebank()["bundles"].values()
        for b in v["az"] + v["ru"]
        for s in b
    }
    assert not [g["text"] for g in gold["clear"] if normalize(g["text"]) in seen], (
        "gold text copied from phrasebank"
    )
    assert len(gold["clear"]) >= 80 and len(gold["vague"]) >= 10


def test_vision_label_set_is_consistent_with_taxonomy() -> None:
    vc = load_vision_classes()
    assert {o["category"] for o in vc["objects"].values()} == set(category_slugs())
    for d in vc["defects"].values():
        assert set(d["problem_hints"]) <= set(problem_codes())
