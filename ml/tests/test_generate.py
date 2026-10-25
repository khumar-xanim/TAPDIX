import re

import pytest

from tapdix_ml.data.generate import generate_listings, generate_masters, write_dataset
from tapdix_ml.data.index_photos import index_photos
from tapdix_ml.data.taxonomy import problem_index

PHONE = re.compile(r"\d[\d\s-]{7,}\d")


@pytest.fixture(scope="module")
def rows():
    return generate_listings(n_per_type=12, seed=1)


def test_generation_is_deterministic_and_seed_sensitive(rows) -> None:
    assert rows == generate_listings(n_per_type=12, seed=1)
    assert rows != generate_listings(n_per_type=12, seed=2)
    assert generate_masters(30, 1) == generate_masters(30, 1)


def test_labels_ids_and_structure(rows) -> None:
    assert len({r["listing_id"] for r in rows}) == len(rows) == 56 * 12
    idx = problem_index()
    for r in rows:
        lab = r["labels"]
        assert (
            lab["problem_type"] in idx and lab["category"] == idx[lab["problem_type"]]["category"]
        )
        assert lab["skills"] == idx[lab["problem_type"]]["skills"]
        b = r["budget"]
        assert (b["min"] is None) == (b["type"] == "Negotiable")
        if b["type"] == "Fixed":
            assert b["min"] == b["max"]
        if b["type"] == "Range":
            assert 0 < b["min"] < b["max"]
        assert r["photos"] == [] and r["urgency"] in {"Low", "Normal", "Urgent", "Emergency"}


def test_train_and_test_never_share_a_phrasing(rows) -> None:
    for r in rows:
        if r["text_quality"] == "clear":
            test_idx = {"az": 4, "ru": 1}[r["language"]]
            assert (r["split"] == "test") == (r["bundle"] == f"{r['language']}{test_idx}"), r[
                "bundle"
            ]
    train_titles = {
        (r["labels"]["problem_type"], r["bundle"])
        for r in rows
        if r["split"] == "train" and r["bundle"]
    }
    test_bundles = {
        (r["labels"]["problem_type"], r["bundle"])
        for r in rows
        if r["split"] == "test" and r["bundle"]
    }
    assert not train_titles & test_bundles


def test_no_phone_numbers_in_generated_text(rows) -> None:
    assert not [r for r in rows if PHONE.search(r["title"] + " " + r["description"])]


def test_masters_reference_real_skills_and_areas() -> None:
    from tapdix_ml.data.taxonomy import load_taxonomy

    all_skills = {s["code"] for c in load_taxonomy()["categories"] for s in c["skills"]}
    for m in generate_masters(60, 3):
        assert set(m["skills"]) <= all_skills and m["service_areas"]
        assert (m["rating_count"] == 0) == (m["average_rating"] == 0.0)


def test_write_dataset_and_manifest(tmp_path) -> None:
    stats = write_dataset(tmp_path, n_per_type=3, n_masters=10, seed=5)
    assert stats["n_listings"] == 56 * 3
    for name in (
        "listings.jsonl",
        "listings.csv",
        "masters.csv",
        "manifest.json",
        "DATASET_CARD.md",
    ):
        assert (tmp_path / name).exists()
    assert (tmp_path / "listings.csv").read_bytes().startswith(b"\xef\xbb\xbf"), (
        "CSV needs a BOM for Excel on Windows"
    )


def test_photo_indexer_validates_folders_and_dedupes(tmp_path) -> None:
    good = tmp_path / "plumbing" / "faucet_leak"
    good.mkdir(parents=True)
    (good / "a.jpg").write_bytes(b"photo-a")
    (good / "dup.jpg").write_bytes(b"photo-a")  # same bytes
    wrong = tmp_path / "plumbing" / "ac_water_leak"  # valid code, wrong category
    wrong.mkdir()
    (wrong / "b.png").write_bytes(b"photo-b")
    (tmp_path / "loose.jpg").write_bytes(b"x")  # not in <category>/<problem>/ layout
    rows, problems = index_photos(tmp_path)
    assert [r["path"] for r in rows] == ["images/plumbing/faucet_leak/a.jpg"]
    assert len(problems) == 3
