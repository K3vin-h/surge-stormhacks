"""Area summary / detail and the stateless model-result shapes."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .common import AreaId, RiskLevel


class RiskResult(BaseModel):
    score: float
    risk_level: RiskLevel
    model_version: str
    provenance: str
    evaluated_at: datetime


class DamageResult(BaseModel):
    score: float
    change_percentage: float
    model_version: str
    provenance: str
    note: str = "Visual change is not verified flood damage."
    evaluated_at: datetime


class PriorityFactor(BaseModel):
    name: str
    normalized: float
    weight: float
    contribution: float


class PriorityResult(BaseModel):
    score: float
    priority_level: str
    factors: list[PriorityFactor]
    model_version: str
    evaluated_at: datetime


class AreaSummary(BaseModel):
    area_id: AreaId
    name: str
    risk: RiskResult
    damage: DamageResult
    priority: PriorityResult


class RoadRef(BaseModel):
    id: str
    name: str
    status: str  # open | closed
    geometry: dict[str, Any] | None = None


class ShelterRef(BaseModel):
    id: str
    name: str
    capacity: int | None = None
    location: dict[str, Any] | None = None


class HospitalRef(BaseModel):
    id: str
    name: str
    location: dict[str, Any] | None = None


class RouteRef(BaseModel):
    id: str
    name: str
    geometry: dict[str, Any] | None = None


class AreaDetail(BaseModel):
    area_id: AreaId
    name: str
    risk: RiskResult
    damage: DamageResult
    priority: PriorityResult
    geometry: dict[str, Any] | None = None
    population: int | None = None
    distress_calls: int | None = None
    injuries: int | None = None
    vulnerable_population: int | None = None
    road_accessibility: float | None = None
    roads: list[RoadRef] = []
    shelters: list[ShelterRef] = []
    hospitals: list[HospitalRef] = []
    routes: list[RouteRef] = []
    reports: list[dict[str, Any]] = []
    provenance: str
    updated_at: datetime


class AreasResponse(BaseModel):
    areas: list[AreaSummary]
    updated_at: datetime
