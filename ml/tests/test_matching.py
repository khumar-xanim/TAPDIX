from tapdix_ml.matching import Master, Need, bayesian_rating, rank_masters, score_master


def master(
    mid="m1",
    cat="plumbing",
    skills=("faucet_repair",),
    years=5,
    rating=4.5,
    n=20,
    ver="Verified",
    avail=True,
    emergency=False,
    areas=(("Bakı", "Nəsimi"),),
) -> Master:
    return Master(
        mid, cat, frozenset(skills), years, rating, n, ver, avail, emergency, tuple(areas)
    )


NEED = Need("plumbing", {"faucet_repair": 1.0, "faucet_replacement": 1.0}, "Bakı", "Nəsimi")


def test_one_perfect_review_no_longer_beats_many_good_ones() -> None:  # legacy defect #7
    assert bayesian_rating(5.0, 1) < bayesian_rating(4.8, 50)
    one = master("one", rating=5.0, n=1)
    many = master("many", rating=4.8, n=50)
    assert [r.master_id for r in rank_masters([one, many], NEED)] == ["many", "one"]


def test_skill_match_beats_no_skill_and_exclusions_apply() -> None:
    ranked = rank_masters(
        [
            master("skilled"),
            master("generalist", skills=("pipe_repair",)),
            master("electrician", cat="electrical", skills=("socket_repair",)),
            master("away", avail=False),
            master("rejected", ver="Rejected"),
            master("other_city", areas=(("Gəncə", "Kəpəz"),)),
        ],
        NEED,
    )
    ids = [r.master_id for r in ranked]
    assert ids[0] == "skilled" and ids[1] == "generalist"
    assert not {"electrician", "away", "rejected", "other_city"} & set(ids)


def test_same_district_beats_same_city() -> None:
    near, far = master("near"), master("far", areas=(("Bakı", "Xətai"),))
    assert score_master(near, NEED).score > score_master(far, NEED).score


def test_urgent_jobs_prefer_masters_who_take_emergencies() -> None:
    urgent = Need(NEED.category, NEED.skill_weights, NEED.city, NEED.district, "Emergency")
    a, b = master("takes", emergency=True), master("declines", emergency=False)
    assert [r.master_id for r in rank_masters([b, a], urgent)] == ["takes", "declines"]


def test_ranking_is_deterministic_and_inputs_are_not_mutated() -> None:
    ms = [master(f"m{i}") for i in range(5)]
    snapshot = list(ms)
    assert [r.master_id for r in rank_masters(ms, NEED)] == [
        r.master_id for r in rank_masters(list(reversed(ms)), NEED)
    ]
    assert ms == snapshot


def test_reasons_are_human_readable_azerbaijani() -> None:
    reasons = score_master(master(), NEED).reasons
    assert any(r.startswith("Bacarıq:") for r in reasons) and "Eyni rayon" in reasons
