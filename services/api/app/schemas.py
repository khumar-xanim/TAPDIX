"""Request / response contracts of the Tapdix API (validated by Pydantic)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from tapdix_ml.vision.fusion import load_vision_classes

Urgency = Literal["Low", "Normal", "Urgent", "Emergency"]
Source = Literal["text", "photo", "text+photo", "ask_user"]


class DetectionIn(BaseModel):
    """One simulated photo detection (what a YOLO model would return)."""

    label: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("label")
    @classmethod
    def label_must_be_known(cls, v: str) -> str:
        classes = load_vision_classes()
        if v not in classes["objects"] and v not in classes["defects"]:
            raise ValueError(f"unknown detection label: {v}")
        return v


class AnalyzeRequest(BaseModel):
    title: str = Field("", max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    city: str = Field("Bakı", min_length=1, max_length=60)
    district: str = Field("Nəsimi", min_length=1, max_length=60)
    urgency: Urgency = "Normal"
    detections: list[DetectionIn] = Field(default_factory=list, max_length=20)
    k: int = Field(5, ge=1, le=10)

    @field_validator("description")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be blank")
        return v


class RankedProblem(BaseModel):
    problem_type: str
    name_az: str
    probability: float


class Keyword(BaseModel):
    word: str
    weight: float


class TextOut(BaseModel):
    category: str
    category_prob: float
    problem_type: str
    problem_prob: float
    top_k: list[RankedProblem]
    category_probs: dict[str, float]
    keywords: list[Keyword]


class DecisionOut(BaseModel):
    source: Source
    category: str | None
    category_name_az: str | None
    problem_type: str | None
    problem_name_az: str | None
    confidence: float
    reasons: list[str]
    request_photo: bool
    clarification_az: str | None
    alternatives: list[str]


class MasterOut(BaseModel):
    master_id: str
    main_category: str
    years_experience: float
    average_rating: float
    rating_count: int
    verification_status: str
    accepts_emergency_jobs: bool


class MatchOut(BaseModel):
    master: MasterOut
    score: float
    reasons: list[str]


class AnalyzeResponse(BaseModel):
    text: TextOut
    decision: DecisionOut
    matches: list[MatchOut]
    note: str = "Masters are synthetic demo data."


class CategoryMeta(BaseModel):
    slug: str
    name_en: str
    name_az: str


class PhotoPreset(BaseModel):
    id: str
    label: str
    detections: list[DetectionIn]


class MetaResponse(BaseModel):
    categories: list[CategoryMeta]
    cities: dict[str, list[str]]
    urgencies: list[str]
    photo_presets: list[PhotoPreset]
    examples: list[str]
