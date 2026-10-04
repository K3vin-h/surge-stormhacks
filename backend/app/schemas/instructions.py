"""Government instruction publish/read and alert/event projections."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import AreaId, InstructionType, PublicationFreshness, Severity


class PublishInstructionRequest(BaseModel):
    publication_id: str = Field(..., min_length=1)
    area_id: AreaId
    instruction_type: InstructionType
    emergency_message: str = Field(..., min_length=1)
    shelter_id: str | None = None
    approved_route_id: str | None = None
    roads_to_avoid_ids: list[str] = []
    cancels_instruction_id: str | None = None
    update_frequency_minutes: int | None = None
    next_update_at: datetime | None = None


class RouteSnapshot(BaseModel):
    id: str
    name: str
    geometry: dict[str, Any] | None = None


class ShelterSnapshot(BaseModel):
    id: str
    name: str
    location: dict[str, Any] | None = None


class RoadSnapshot(BaseModel):
    id: str
    name: str


class PublishedInstruction(BaseModel):
    publication_id: str
    area_id: AreaId
    instruction_type: InstructionType
    severity: Severity
    emergency_message: str
    shelter: ShelterSnapshot | None = None
    approved_route: RouteSnapshot | None = None
    roads_to_avoid: list[RoadSnapshot] = []
    cancels_instruction_id: str | None = None
    update_frequency_minutes: int | None = None
    next_update_at: datetime | None = None
    published_at: datetime


class Alert(BaseModel):
    """A projection of a committed instruction (not a separate write)."""

    instruction_id: str
    area_id: AreaId
    severity: Severity
    instruction_type: InstructionType
    emergency_message: str
    published_at: datetime
    superseded: bool = False


class GovEvent(BaseModel):
    event_id: str
    kind: str  # publication | model_refresh | road_closure | distress_report
    area_id: AreaId | None = None
    summary: str
    created_at: datetime


class InstructionGetResponse(BaseModel):
    instruction: PublishedInstruction | None
    freshness: PublicationFreshness


class PublishResponse(BaseModel):
    instruction: PublishedInstruction
    alert: Alert
    freshness: PublicationFreshness


class GovAlertsResponse(BaseModel):
    events: list[GovEvent]
    next_cursor: str | None = None
    freshness: PublicationFreshness


class PublicAlertsResponse(BaseModel):
    alerts: list[Alert]
    next_cursor: str | None = None
    freshness: PublicationFreshness


class GovDashboardResponse(BaseModel):
    areas: list[dict[str, Any]]
    events: list[GovEvent]
    freshness: PublicationFreshness
    updated_at: datetime


class PublicStatusResponse(BaseModel):
    area_id: AreaId
    name: str
    summary: dict[str, Any]
    instruction: PublishedInstruction | None
    freshness: PublicationFreshness


class PublicMapResponse(BaseModel):
    area_id: AreaId
    geometry: dict[str, Any] | None = None
    risk_level: str | None = None
    current_instruction_id: str | None = None
    shelter: ShelterSnapshot | None = None
    approved_route: RouteSnapshot | None = None
    closed_roads: list[dict[str, Any]] = []
    hospitals: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    provenance: str
    freshness: PublicationFreshness
    fetched_at: datetime
