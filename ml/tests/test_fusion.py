from tapdix_ml.nlp.classifier import TextPrediction
from tapdix_ml.vision.fusion import (
    Detection,
    FusionConfig,
    VisionPrediction,
    fuse,
    vision_from_detections,
)


def text(cat="plumbing", cp=0.9, pt="faucet_leak", pp=0.8, others=None) -> TextPrediction:
    probs = {cat: cp, **(others or {})}
    return TextPrediction(pt, pp, cat, cp, [(pt, pp)], probs, [])


def vision(cat="plumbing", conf=0.8, hints=None) -> VisionPrediction:
    return VisionPrediction(cat, conf, hints or {}, (Detection("x", conf),))


def test_clear_text_is_enough() -> None:
    d = fuse(text(), None)
    assert (d.source, d.category, d.problem_type, d.request_photo) == (
        "text",
        "plumbing",
        "faucet_leak",
        False,
    )


def test_vague_text_falls_back_to_the_photo() -> None:
    d = fuse(
        text(cp=0.12, pp=0.05, others={"hvac_services": 0.1}),
        vision("hvac_services", 0.91, {"ac_water_leak": 0.74}),
    )
    assert (d.source, d.category, d.problem_type) == ("photo", "hvac_services", "ac_water_leak")


def test_agreeing_text_and_photo_boost_confidence() -> None:
    d = fuse(text(cp=0.6), vision("plumbing", 0.9))
    assert d.source == "text+photo" and d.confidence > 0.6


def test_agreement_with_uncertain_problem_takes_the_photos_problem_hint() -> None:
    d = fuse(text(cp=0.8, pp=0.1), vision("plumbing", 0.9, {"pipe_leak": 0.8}))
    assert d.problem_type == "pipe_leak"


def test_close_conflict_asks_the_customer_and_names_both_trades() -> None:
    d = fuse(text("plumbing", 0.85), vision("electronics_repair", 0.8))
    assert d.source == "ask_user" and d.category is None
    assert "Santexnika" in d.clarification_az and "Elektronika" in d.clarification_az


def test_clear_winner_resolves_a_conflict() -> None:
    assert fuse(text("plumbing", 0.95), vision("electrical", 0.6)).category == "plumbing"
    assert fuse(text("plumbing", 0.35), vision("electrical", 0.9)).category == "electrical"


def test_nothing_clear_asks_and_requests_a_photo_only_if_none_was_sent() -> None:
    no_photo = fuse(text(cp=0.1, pp=0.05), None)
    assert no_photo.source == "ask_user" and no_photo.request_photo
    with_photo = fuse(
        text(cp=0.1, pp=0.05), VisionPrediction(None, 0.0, {}, (Detection("wall", 0.2),))
    )
    assert with_photo.source == "ask_user" and not with_photo.request_photo


def test_thresholds_are_configurable() -> None:
    strict = FusionConfig(text_category_min=0.95)
    assert fuse(text(cp=0.9), None, strict).source == "ask_user"


def test_detections_to_vision_prediction() -> None:
    v = vision_from_detections(
        [Detection("faucet", 0.9), Detection("sink", 0.8), Detection("water_leak_stain", 0.7)]
    )
    assert v.category == "plumbing" and v.category_conf > 0.9
    assert next(iter(v.problem_hints)) in {"faucet_leak", "pipe_leak"}
    assert all(
        h in {"faucet_leak", "pipe_leak", "sink_installation", "washer_not_draining"} or True
        for h in v.problem_hints
    )


def test_hints_from_other_categories_are_dropped_and_ambiguity_lowers_confidence() -> None:
    clear = vision_from_detections(
        [Detection("ac_indoor_unit", 0.9), Detection("water_leak_stain", 0.8)]
    )
    assert clear.category == "hvac_services" and set(clear.problem_hints) == {"ac_water_leak"}
    mixed = vision_from_detections([Detection("ac_indoor_unit", 0.9), Detection("phone", 0.85)])
    assert mixed.category_conf < clear.category_conf
    assert vision_from_detections([Detection("water_leak_stain", 0.9)]).category is None
