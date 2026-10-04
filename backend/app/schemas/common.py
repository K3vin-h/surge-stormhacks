"""Shared enums and small value objects used across routes."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# Canonical area IDs (API values). UI labels are mapped by the frontend.
AREA_IDS = ("sunsari", "saptari", "bardiya", "kathmandu_valley", "rasuwa")
AreaId = Literal["sunsari", "saptari", "bardiya", "kathmandu_valley", "rasuwa"]


class PublicationState(str, Enum):
    ready = "ready"
    uninitialized = "uninitialized"
    blocked = "blocked"


class InstructionType(str, Enum):
    evacuate = "evacuate"
    shelter_in_place = "shelter_in_place"
    advisory = "advisory"
    all_clear = "all_clear"


class Severity(str, Enum):
    critical = "critical"
    warning = "warning"
    advisory = "advisory"
    info = "info"


class RiskLevel(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    severe = "severe"


class ReportKind(str, Enum):
    road_hazard = "road_hazard"
    rescue_needed = "rescue_needed"
    rescue_seen = "rescue_seen"


class VerificationState(str, Enum):
    unverified = "unverified"
    reviewed = "reviewed"
    actioned = "actioned"
    resolved = "resolved"
    duplicate = "duplicate"
    false_report = "false_report"


class PublicationFreshness(BaseModel):
    publication_state: PublicationState
    current_instruction_id: str | None = None
    published_at: datetime | None = None
    next_update_at: datetime | None = None
    server_time: datetime


class GeoPoint(BaseModel):
    """GeoJSON point; coordinates are [longitude, latitude]."""

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(..., min_length=2, max_length=2)

    @property
    def lng(self) -> float:
        return self.coordinates[0]

    @property
    def lat(self) -> float:
        return self.coordinates[1]
