"""Resident-facing routes: status, alerts, map, and report submit/read."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request, Response

from ..errors import not_found
from ..fixtures import areas as fx
from ..schemas.common import InstructionType
from ..schemas.instructions import (
    PublicAlertsResponse,
    PublicMapResponse,
    PublicStatusResponse,
)
from ..schemas.roads import RoadStatusResponse
from ..schemas.reports import ReportsResponse, SubmitReportRequest, SubmitReportResponse
from ..services import answers, cache, instructions, models, reports as reports_svc, road_status
from ..util import decode_cursor, next_cursor, now_utc

router = APIRouter(prefix="/api/public")


def _require_area(area_id: str) -> None:
    if fx.get_area(area_id) is None:
        raise not_found(f"Unknown area '{area_id}'.")


@router.get("/roads/status", response_model=RoadStatusResponse)  # ponytail: ETag is the version; no Cache-Control
def roads_status(request: Request, response: Response) -> RoadStatusResponse | Response:
    data = road_status.list_roads()
    etag = f'"{data.version}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return data


@router.get("/status/{area_id}", response_model=PublicStatusResponse)
def status(area_id: str) -> PublicStatusResponse:
    _require_area(area_id)
    summary = models.build_summary(area_id)
    inst = cache.get_current(area_id)
    if fx.get_area(area_id).get("placeholder"):
        # summary is a free-form dict, so "unknown" needs no schema change.
        return PublicStatusResponse(
            area_id=area_id,
            name=summary.name,
            summary={"risk_level": "unknown", "risk_score": None, "priority_level": "unknown"},
            instruction=inst,
            freshness=cache.freshness(area_id),
        )
    return PublicStatusResponse(
        area_id=area_id,
        name=summary.name,
        summary={
            "risk_level": summary.risk.risk_level.value,
            "risk_score": summary.risk.score,
            "priority_level": summary.priority.priority_level,
        },
        instruction=inst,
        freshness=cache.freshness(area_id),
    )


@router.post("/update-briefing")
def update_briefing(payload: dict):
    """Auto-briefing when the government changes the instruction.

    The client calls this when its polled instruction_id changes, passing the
    id it last saw. Returns a short spoken summary of what changed and whether
    it affects the user; {"briefing": null} when there is nothing new.
    """
    area_id = payload.get("area_id")
    _require_area(area_id)
    current = cache.get_current(area_id)
    if current is None:
        return {"briefing": None}
    prev_id = payload.get("previous_instruction_id")
    if prev_id == current.publication_id:
        return {"briefing": None}  # no change since the client last saw it
    previous = instructions.get_by_id(prev_id) if prev_id else None
    language = payload.get("language") or "en"
    return {"briefing": answers.render_update_briefing(area_id, previous, current, language)}


@router.get("/alerts/{area_id}", response_model=PublicAlertsResponse)
def alerts(
    area_id: str,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> PublicAlertsResponse:
    _require_area(area_id)
    offset = decode_cursor(cursor)
    # Alerts are projections of committed instructions, newest first.
    history = instructions.list_history_for_area(area_id, limit=limit, offset=offset)
    current = cache.get_current(area_id)
    current_id = current.publication_id if current else None
    alert_list = [
        instructions.to_alert(i, superseded=(i.publication_id != current_id))
        for i in history
    ]
    return PublicAlertsResponse(
        alerts=alert_list,
        next_cursor=next_cursor(offset, limit, len(history)),
        freshness=cache.freshness(area_id),
    )


@router.get("/map/{area_id}", response_model=PublicMapResponse)
def area_map(area_id: str) -> PublicMapResponse:
    _require_area(area_id)
    a = fx.get_area(area_id)
    summary = models.build_summary(area_id)
    inst = cache.get_current(area_id)

    # Draw a route only for an active evacuation; all_clear cancels it.
    shelter = route = None
    if inst and inst.instruction_type == InstructionType.evacuate:
        shelter = inst.shelter
        route = inst.approved_route

    closed_roads = [r for r in a["roads"] if r["status"] == "closed"]
    report_points = [
        {
            "report_id": r.report_id,
            "kind": r.kind.value,
            "message": r.message,
            "location": r.location.model_dump(),
            "verification_state": r.verification_state.value,
        }
        for r in reports_svc.list_reports(area_id=area_id, limit=50)
    ]
    return PublicMapResponse(
        area_id=area_id,
        geometry=fx.geometry_for(area_id),
        risk_level="unknown" if a.get("placeholder") else summary.risk.risk_level.value,
        current_instruction_id=inst.publication_id if inst else None,
        shelter=shelter,
        approved_route=route,
        closed_roads=closed_roads,
        hospitals=a["hospitals"],
        reports=report_points,
        provenance="fixture catalog + committed instruction (demo)",
        freshness=cache.freshness(area_id),
        fetched_at=now_utc(),
    )


@router.post("/reports", response_model=SubmitReportResponse)
def submit_report(req: SubmitReportRequest) -> SubmitReportResponse:
    _require_area(req.area_id)
    report, _created, moved = reports_svc.submit(req)
    return SubmitReportResponse(
        report=report,
        accepted=True,
        verification_state=report.verification_state,
        received_at=report.received_at,
        moved=moved,
    )


@router.get("/reports/{area_id}", response_model=ReportsResponse)
def public_reports(
    area_id: str,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
) -> ReportsResponse:
    _require_area(area_id)
    offset = decode_cursor(cursor)
    rows = reports_svc.list_reports(area_id=area_id, limit=limit, offset=offset)
    return ReportsResponse(
        reports=rows,
        next_cursor=next_cursor(offset, limit, len(rows)),
    )
