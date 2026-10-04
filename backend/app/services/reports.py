"""Community road/rescue reports, persisted to Snowflake REPORTS."""
from __future__ import annotations

import uuid

from ..db import snowflake_client as sf
from ..schemas.common import GeoPoint, ReportKind, VerificationState
from ..schemas.reports import Report, SubmitReportRequest
from ..util import now_utc
from . import events


def _row_to_report(row: dict) -> Report:
    return Report(
        report_id=row["REPORT_ID"],
        area_id=row["AREA_ID"],
        kind=ReportKind(row["KIND"]),
        message=row["MESSAGE"],
        location=GeoPoint(coordinates=[row["LONGITUDE"], row["LATITUDE"]]),
        verification_state=VerificationState(row["VERIFICATION_STATE"]),
        reported_at=row.get("REPORTED_AT"),
        received_at=row["RECEIVED_AT"],
        provenance=row.get("PROVENANCE") or "resident_report",
    )


def submit(req: SubmitReportRequest) -> tuple[Report, bool]:
    """Returns (report, created). Idempotent on idempotency_key when provided."""
    if req.idempotency_key:
        existing = sf.query_one(
            "SELECT * FROM REPORTS WHERE IDEMPOTENCY_KEY = %s AND AREA_ID = %s",
            [req.idempotency_key, req.area_id],
        )
        if existing:
            return _row_to_report(existing), False

    received_at = now_utc()
    report = Report(
        report_id=str(uuid.uuid4()),
        area_id=req.area_id,
        kind=req.kind,
        message=req.message,
        location=req.location,
        verification_state=VerificationState.unverified,
        reported_at=req.reported_at,
        received_at=received_at,
        provenance="resident_report",
    )
    sf.execute(
        """INSERT INTO REPORTS (
               REPORT_ID, AREA_ID, KIND, MESSAGE, LONGITUDE, LATITUDE,
               VERIFICATION_STATE, REPORTED_AT, RECEIVED_AT, IDEMPOTENCY_KEY, PROVENANCE
           ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        [
            report.report_id, report.area_id, report.kind.value, report.message,
            report.location.lng, report.location.lat,
            report.verification_state.value, report.reported_at, report.received_at,
            req.idempotency_key, report.provenance,
        ],
    )
    events.record_event(
        "distress_report" if req.kind != ReportKind.road_hazard else "road_closure",
        f"{req.kind.value} reported in {req.area_id}",
        req.area_id,
    )
    return report, True


def list_reports(
    area_id: str | None = None,
    kind: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Report]:
    clauses: list[str] = []
    params: list = []
    if area_id:
        clauses.append("AREA_ID = %s")
        params.append(area_id)
    if kind:
        clauses.append("KIND = %s")
        params.append(kind)
    if status:
        clauses.append("VERIFICATION_STATE = %s")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend([limit, offset])
    rows = sf.query(
        f"""SELECT * FROM REPORTS {where}
            ORDER BY RECEIVED_AT DESC LIMIT %s OFFSET %s""",
        params,
    )
    return [_row_to_report(r) for r in rows]
