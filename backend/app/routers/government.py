"""Government workspace routes: dashboard, refresh, publish, alerts, reports."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..errors import not_found
from ..fixtures import areas as fx
from ..schemas.areas import AreaDetail
from ..schemas.common import AREA_IDS
from ..schemas.instructions import (
    GovAlertsResponse,
    GovDashboardResponse,
    InstructionGetResponse,
    PublishInstructionRequest,
    PublishResponse,
)
from ..schemas.reports import Report, ReportsResponse, UpdateReportStateRequest
from ..services import cache, events, instructions, models, reports as reports_svc, slate
from ..util import decode_cursor, next_cursor, now_utc

router = APIRouter(prefix="/api/government")


@router.get("/dashboard", response_model=GovDashboardResponse)
def dashboard() -> GovDashboardResponse:
    summaries = [models.build_summary(aid) for aid in AREA_IDS]
    ranked = sorted(summaries, key=lambda s: s.priority.score, reverse=True)
    areas = []
    for s in ranked:
        current = cache.get_current(s.area_id)
        areas.append({
            **s.model_dump(mode="json"),
            "current_instruction_id": current.publication_id if current else None,
            "current_instruction_type": current.instruction_type.value if current else None,
        })
    return GovDashboardResponse(
        areas=areas,
        events=events.list_events(limit=20),
        freshness=cache.freshness(),
        updated_at=now_utc(),
    )


@router.post("/areas/{area_id}/refresh", response_model=AreaDetail)
def refresh_area(area_id: str) -> AreaDetail:
    if fx.get_area(area_id) is None:
        raise not_found(f"Unknown area '{area_id}'.")
    area_reports = [r.model_dump(mode="json") for r in
                    reports_svc.list_reports(area_id=area_id, limit=50)]
    detail = models.build_detail(area_id, reports=area_reports)
    events.record_event("model_refresh", f"Snapshot recomputed for {area_id}", area_id)
    return detail


@router.get("/instructions/{area_id}", response_model=InstructionGetResponse)
def get_instruction(area_id: str) -> InstructionGetResponse:
    if fx.get_area(area_id) is None:
        raise not_found(f"Unknown area '{area_id}'.")
    inst = cache.get_current(area_id) or instructions.get_latest_for_area(area_id)
    return InstructionGetResponse(instruction=inst, freshness=cache.freshness(area_id))


@router.post("/instructions", response_model=PublishResponse)
def publish_instruction(req: PublishInstructionRequest) -> PublishResponse:
    if fx.get_area(req.area_id) is None:
        raise not_found(f"Unknown area '{req.area_id}'.")
    inst = instructions.publish(req)
    return PublishResponse(
        instruction=inst,
        alert=instructions.to_alert(inst),
        freshness=cache.freshness(req.area_id),
    )


@router.get("/alerts", response_model=GovAlertsResponse)
def gov_alerts(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> GovAlertsResponse:
    offset = decode_cursor(cursor)
    evs = events.list_events(limit=limit, offset=offset)
    return GovAlertsResponse(
        events=evs,
        next_cursor=next_cursor(offset, limit, len(evs)),
        freshness=cache.freshness(),
    )


@router.get("/reports", response_model=ReportsResponse)
def gov_reports(
    area_id: str | None = None,
    kind: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
) -> ReportsResponse:
    offset = decode_cursor(cursor)
    rows = reports_svc.list_reports(
        area_id=area_id, kind=kind, status=status, limit=limit, offset=offset
    )
    return ReportsResponse(
        reports=rows,
        next_cursor=next_cursor(offset, limit, len(rows)),
    )


@router.post("/reset")
def reset_slate() -> dict[str, int]:
    """Delete every report, official message, and activity entry."""
    return slate.clear_slate()


@router.patch("/reports/{report_id}", response_model=Report)
def update_report(report_id: str, req: UpdateReportStateRequest) -> Report:
    report = reports_svc.set_state(report_id, req.verification_state)
    if report is None:
        raise not_found(f"Unknown report '{report_id}'.")
    return report
