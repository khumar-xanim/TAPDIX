"""Parity: the Python baseline must reproduce the ORIGINAL TypeScript engine exactly.

Ground truth lives in fixtures/legacy_cases.json, produced by running the real TS code
(legacy/tools/gen_fixtures.ts). Regenerate with:  npx -y tsx legacy/tools/gen_fixtures.ts
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tapdix_ml.baseline import (
    JobListing,
    Review,
    WorkerProfile,
    find_similar_successful_workers,
    get_personalized_recommendations,
    recommend_workers_for_job,
    score_worker,
)

DATA = json.loads(
    (Path(__file__).parent / "fixtures" / "legacy_cases.json").read_text(encoding="utf-8")
)
AS_OF = datetime.fromtimestamp(DATA["meta"]["fixedNowMs"] / 1000, tz=UTC)


def to_review(d: dict) -> Review:
    return Review(
        client_id=d["clientId"],
        rating=d["rating"],
        quality=d["quality"],
        communication=d["communication"],
        professionalism=d["professionalism"],
        timeliness=d["timeliness"],
        date=datetime.fromisoformat(d["date"].replace("Z", "+00:00")),
    )


def to_worker(d: dict) -> WorkerProfile:
    return WorkerProfile(
        id=d["id"],
        category=d["category"],
        location=d["location"],
        age=d["age"],
        experience=d["experience"],
        completed_jobs=d["completedJobs"],
        rating=d["rating"],
        success_rate=d["successRate"],
        response_time=d["responseTime"],
        certifications=list(d["certifications"]),
        reviews=[to_review(r) for r in d["reviews"]],
    )


def to_job(d: dict) -> JobListing:
    return JobListing(
        id=d["id"], category=d["category"], location=d["location"], complexity=d["complexity"]
    )


def assert_same(py, ts: dict) -> None:
    assert py.worker_id == ts["workerId"]
    assert py.total_score == ts["totalScore"]
    b, tb = py.breakdown, ts["breakdown"]
    assert (
        b.experience_score,
        b.quality_score,
        b.reliability_score,
        b.match_score,
        b.reputation_score,
    ) == (
        tb["experienceScore"],
        tb["qualityScore"],
        tb["reliabilityScore"],
        tb["matchScore"],
        tb["reputationScore"],
    )
    assert py.confidence == ts["confidence"]
    assert py.recommendation == ts["recommendation"]
    assert py.reasoning == ts["reasoning"]


@pytest.mark.parametrize("i", range(len(DATA["score"])))
def test_score_worker(i: int) -> None:
    case = DATA["score"][i]
    assert_same(
        score_worker(to_worker(case["worker"]), to_job(case["job"]), AS_OF), case["expected"]
    )


@pytest.mark.parametrize("i", range(len(DATA["recommend"])))
def test_recommend_order_and_scores(i: int) -> None:
    case = DATA["recommend"][i]
    got = recommend_workers_for_job(
        [to_worker(w) for w in case["workers"]], to_job(case["job"]), case["limit"], AS_OF
    )
    assert [r.worker_id for r in got] == [e["workerId"] for e in case["expected"]]
    for g, e in zip(got, case["expected"], strict=True):
        assert_same(g, e)


@pytest.mark.parametrize("i", range(len(DATA["personalized"])))
def test_personalized(i: int) -> None:
    case = DATA["personalized"][i]
    got = get_personalized_recommendations(
        [to_worker(w) for w in case["workers"]], [to_job(j) for j in case["history"]], case["limit"]
    )
    assert [w.id for w in got] == case["expected"]


@pytest.mark.parametrize("i", range(len(DATA["similar"])))
def test_similar(i: int) -> None:
    case = DATA["similar"][i]
    got = find_similar_successful_workers(
        to_job(case["job"]), [to_worker(w) for w in case["workers"]], case["limit"]
    )
    assert [w.id for w in got] == case["expected"]
