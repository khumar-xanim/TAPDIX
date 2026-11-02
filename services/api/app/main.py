"""Tapdix API: understands a listing and ranks masters. Run: see docs/RUN_LOCALLY.md"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from tapdix_ml.data.taxonomy import load_phrasebank, load_taxonomy, problem_index
from tapdix_ml.pipeline import recommend
from tapdix_ml.vision.fusion import Detection

from .engine import Engine, get_engine
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CategoryMeta,
    DecisionOut,
    DetectionIn,
    Keyword,
    MasterOut,
    MatchOut,
    MetaResponse,
    PhotoPreset,
    RankedProblem,
    TextOut,
)

EXAMPLES = [
    "Mətbəx kranı su axıdır, təcili lazımdır",
    "paltaryuyan sixmir, cox ses salir",
    "Нет света в квартире, автомат выбивает",
    "Usta lazımdır, şəkildə görünür",
    "Kömək lazımdır",
]

# Simulated photo detections (labels must exist in ml/data/vision/classes.json; a test enforces it)
PHOTO_PRESETS = [
    PhotoPreset(
        id="ac_leak",
        label="Photo: AC unit with a water stain",
        detections=[
            DetectionIn(label="ac_indoor_unit", confidence=0.91),
            DetectionIn(label="water_leak_stain", confidence=0.74),
        ],
    ),
    PhotoPreset(
        id="faucet_leak",
        label="Photo: faucet and sink with a water stain",
        detections=[
            DetectionIn(label="faucet", confidence=0.90),
            DetectionIn(label="sink", confidence=0.80),
            DetectionIn(label="water_leak_stain", confidence=0.70),
        ],
    ),
    PhotoPreset(
        id="burnt_socket",
        label="Photo: socket with a burn mark",
        detections=[
            DetectionIn(label="socket", confidence=0.88),
            DetectionIn(label="burn_mark", confidence=0.72),
        ],
    ),
    PhotoPreset(
        id="laptop",
        label="Photo: a laptop",
        detections=[DetectionIn(label="laptop", confidence=0.85)],
    ),
    PhotoPreset(
        id="cracked_phone",
        label="Photo: phone with a cracked screen",
        detections=[
            DetectionIn(label="phone", confidence=0.90),
            DetectionIn(label="cracked_screen", confidence=0.80),
        ],
    ),
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_engine()  # warm up at server start so the first request is fast
    yield


app = FastAPI(title="Tapdix API", version="0.2.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    cats = [
        CategoryMeta(slug=c["slug"], name_en=c["name_en"], name_az=c["name_az"])
        for c in load_taxonomy()["categories"]
    ]
    return MetaResponse(
        categories=cats,
        cities=load_phrasebank()["geo"],
        urgencies=["Low", "Normal", "Urgent", "Emergency"],
        photo_presets=PHOTO_PRESETS,
        examples=EXAMPLES,
    )


def _cat_name(slug: str | None) -> str | None:
    return next((c["name_az"] for c in load_taxonomy()["categories"] if c["slug"] == slug), None)


def _problem_name(code: str | None) -> str | None:
    return problem_index()[code]["name_az"] if code else None


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, engine: Engine = Depends(get_engine)) -> AnalyzeResponse:  # noqa: B008
    rec = recommend(
        engine.model,
        engine.masters,
        title=req.title,
        description=req.description,
        city=req.city,
        district=req.district,
        urgency=req.urgency,
        detections=[Detection(d.label, d.confidence) for d in req.detections] or None,
        k=req.k,
    )
    t, d = rec.text, rec.decision
    by_id = engine.by_id
    return AnalyzeResponse(
        text=TextOut(
            category=t.category,
            category_prob=t.category_prob,
            problem_type=t.problem_type,
            problem_prob=t.problem_prob,
            top_k=[
                RankedProblem(problem_type=c, name_az=_problem_name(c) or c, probability=p)
                for c, p in t.top_k
            ],
            category_probs=t.category_probs,
            keywords=[Keyword(word=w, weight=s) for w, s in t.keywords],
        ),
        decision=DecisionOut(
            source=d.source,
            category=d.category,
            category_name_az=_cat_name(d.category),
            problem_type=d.problem_type,
            problem_name_az=_problem_name(d.problem_type),
            confidence=d.confidence,
            reasons=d.reasons,
            request_photo=d.request_photo,
            clarification_az=d.clarification_az,
            alternatives=d.alternatives,
        ),
        matches=[
            MatchOut(
                master=MasterOut(
                    master_id=m.master_id,
                    main_category=by_id[m.master_id].main_category,
                    years_experience=by_id[m.master_id].years_experience,
                    average_rating=by_id[m.master_id].average_rating,
                    rating_count=by_id[m.master_id].rating_count,
                    verification_status=by_id[m.master_id].verification_status,
                    accepts_emergency_jobs=by_id[m.master_id].accepts_emergency_jobs,
                ),
                score=m.score,
                reasons=m.reasons,
            )
            for m in rec.matches
        ],
    )
