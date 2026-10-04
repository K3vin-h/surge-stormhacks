"""Community road/rescue report shapes."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .common import AreaId, GeoPoint, ReportKind, VerificationState


class SubmitReportRequest(BaseModel):
    area_id: AreaId
    kind: ReportKind
    message: str = Field(..., min_length=1, max_length=1000)
    location: GeoPoint
    reported_at: datetime | None = None
    # Optional client idempotency key to prevent duplicate SOS pins on retry.
    idempotency_key: str | None = Field(None, max_length=128)
    # Browser device id; one active rescue_needed per device. Never echoed back.
    device_id: str | None = Field(None, max_length=128)


class Report(BaseModel):
    report_id: str
    area_id: AreaId
    kind: ReportKind
    message: str
    location: GeoPoint
    verification_state: VerificationState
    reported_at: datetime | None = None
    received_at: datetime
    provenance: str = "resident_report"


class SubmitReportResponse(BaseModel):
    report: Report
    accepted: bool
    verification_state: VerificationState
    received_at: datetime
    moved: bool = False


class UpdateReportStateRequest(BaseModel):
    verification_state: VerificationState


class ReportsResponse(BaseModel):
    reports: list[Report]
    next_cursor: str | None = None
