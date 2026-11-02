import pytest
from fastapi.testclient import TestClient

from app.engine import Engine, get_engine
from app.main import PHOTO_PRESETS, app
from tapdix_ml.data.generate import generate_listings, write_dataset
from tapdix_ml.nlp.classifier import ListingClassifier, listing_text
from tapdix_ml.pipeline import load_masters
from tapdix_ml.vision.fusion import load_vision_classes


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    d = tmp_path_factory.mktemp("api")
    write_dataset(d, n_per_type=3, n_masters=200, seed=6)
    rows = [
        r
        for r in generate_listings(n_per_type=30, seed=11)
        if r["text_quality"] == "clear" and r["split"] == "train"
    ]
    model = ListingClassifier().fit(
        [listing_text(r["title"], r["description"]) for r in rows],
        [r["labels"]["problem_type"] for r in rows],
    )
    engine = Engine(model=model, masters=load_masters(d / "masters.csv"))
    app.dependency_overrides[get_engine] = lambda: engine
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_meta_lists_what_the_page_needs(client) -> None:
    r = client.get("/api/meta").json()
    assert (
        len(r["categories"]) == 8
        and "Bakı" in r["cities"]
        and r["urgencies"] == ["Low", "Normal", "Urgent", "Emergency"]
    )
    assert len(r["photo_presets"]) >= 4 and len(r["examples"]) >= 3


def test_every_photo_preset_uses_real_detector_labels() -> None:
    classes = load_vision_classes()
    known = set(classes["objects"]) | set(classes["defects"])
    for p in PHOTO_PRESETS:
        assert {d.label for d in p.detections} <= known, p.id


def test_clear_text_is_understood_and_masters_are_ranked(client) -> None:
    r = client.post(
        "/api/analyze",
        json={
            "description": "Mətbəx kranı su axıdır, təcili",
            "district": "Nəsimi",
            "urgency": "Urgent",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["source"] == "text" and body["decision"]["category"] == "plumbing"
    assert body["decision"]["category_name_az"] == "Santexnika" and body["text"]["keywords"]
    scores = [m["score"] for m in body["matches"]]
    assert body["matches"] and scores == sorted(scores, reverse=True)
    assert all(0 <= m["master"]["average_rating"] <= 5 for m in body["matches"])


def test_vague_text_with_photo_uses_the_photo(client) -> None:
    ac = next(p for p in PHOTO_PRESETS if p.id == "ac_leak")
    r = client.post(
        "/api/analyze",
        json={
            "description": "Usta lazımdır, şəkildə görünür",
            "detections": [d.model_dump() for d in ac.detections],
        },
    )
    assert (
        r.json()["decision"]["source"] == "photo"
        and r.json()["decision"]["category"] == "hvac_services"
    )


def test_vague_text_without_photo_asks_the_customer(client) -> None:
    body = client.post("/api/analyze", json={"description": "Kömək lazımdır"}).json()
    assert (
        body["decision"]["source"] == "ask_user"
        and body["decision"]["clarification_az"]
        and body["matches"] == []
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"description": ""},
        {"description": "   "},
        {"description": "x" * 2001},
        {"description": "kran", "urgency": "Whenever"},
        {"description": "kran", "k": 99},
        {"description": "kran", "detections": [{"label": "unicorn", "confidence": 0.9}]},
        {"description": "kran", "detections": [{"label": "faucet", "confidence": 1.5}]},
    ],
)
def test_bad_input_is_rejected_with_422(client, payload) -> None:
    assert client.post("/api/analyze", json=payload).status_code == 422
