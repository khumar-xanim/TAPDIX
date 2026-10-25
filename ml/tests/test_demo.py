import pytest

from tapdix_ml.data.generate import generate_listings, write_dataset
from tapdix_ml.demo import analyze
from tapdix_ml.nlp.classifier import ListingClassifier, listing_text
from tapdix_ml.vision.fusion import Detection


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    d = tmp_path_factory.mktemp("demo")
    write_dataset(d, n_per_type=3, n_masters=120, seed=4)
    rows = [
        r
        for r in generate_listings(n_per_type=30, seed=11)
        if r["text_quality"] == "clear" and r["split"] == "train"
    ]
    model = ListingClassifier().fit(
        [listing_text(r["title"], r["description"]) for r in rows],
        [r["labels"]["problem_type"] for r in rows],
    )
    return model, d / "masters.csv"


def test_demo_text_only(world) -> None:
    model, masters = world
    out = analyze(model, masters, "Mətbəx kranı su axıdır, təcili", urgency="Urgent")
    assert "category     : plumbing" in out and "source=text" in out and "TOP MASTERS" in out


def test_demo_photo_rescues_vague_text(world) -> None:
    model, masters = world
    out = analyze(
        model,
        masters,
        "Usta lazımdır, şəkildə görünür",
        detections=[Detection("ac_indoor_unit", 0.9)],
    )
    assert "source=photo" in out and "hvac_services" in out


def test_demo_vague_text_asks_the_customer(world) -> None:
    model, masters = world
    out = analyze(model, masters, "Kömək lazımdır")
    assert "ASK THE CUSTOMER" in out and "none - nothing to match" in out
