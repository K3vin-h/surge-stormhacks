"""Persisted road status (closed / flooded) for the resident router."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SetRoadStatusRequest(BaseModel):
    status: Literal["open", "closed", "flooded"]
    note: str | None = Field(None, max_length=200)


class RoadStatus(BaseModel):
    road_id: str
    status: Literal["open", "closed", "flooded"]
    note: str | None = None
    updated_at: datetime


class RoadStatusResponse(BaseModel):
    version: str
    roads: list[RoadStatus]
