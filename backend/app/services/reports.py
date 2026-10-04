"""Community road/rescue reports, persisted to Snowflake REPORTS."""
from __future__ import annotations

import math
import threading
import uuid

from ..db import snowflake_client as sf
from ..errors import conflict
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


# A repeat SOS within this distance (same area) is a duplicate, not a move.
SAME_SPOT_METERS = 25.0
# The duplicate guard only applies to a live SOS (not dismissed as duplicate /
# false_report) that was last sent recently; older ones are refreshed instead.
LIVE_SOS_STATES = {VerificationState.unverified, VerificationState.reviewed, VerificationState.actioned}
SOS_GUARD_SECONDS = 60 * 60


def _meters_apart(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    return 6371000.0 * math.hypot(dlat, dlng)  # equirectangular, fine at this scale


# Serializes check-then-write so a double-tap can't insert two SOS rows.
# ponytail: per-process lock; use a DB-level guard if running multiple workers.
_submit_lock = threading.Lock()


def submit(req: SubmitReportRequest) -> tuple[Report, bool, bool]:
    with _submit_lock:
        return _submit(req)


def _remember_request(area_id: str, key: str | None, report_id: str) -> None:
    if not key:
        return
    sf.execute(
        """INSERT INTO REPORT_REQUEST_KEYS (AREA_ID, IDEMPOTENCY_KEY, REPORT_ID)
           SELECT %s, %s, %s WHERE NOT EXISTS (
               SELECT 1 FROM REPORT_REQUEST_KEYS WHERE AREA_ID = %s AND IDEMPOTENCY_KEY = %s
           )""",
        [area_id, key, report_id, area_id, key],
    )


def _submit(req: SubmitReportRequest) -> tuple[Report, bool, bool]:
    """Returns (report, created, moved). Idempotent on idempotency_key when provided.

    A rescue_needed from a device that already has an unresolved one moves that
    report (same REPORT_ID) instead of creating another, or raises a 409
    `sos_already_sent` if the device has not moved.
    """
    if req.idempotency_key:
        existing = sf.query_one(
            """SELECT r.* FROM REPORT_REQUEST_KEYS k JOIN REPORTS r ON r.REPORT_ID = k.REPORT_ID
               WHERE k.IDEMPOTENCY_KEY = %s AND k.AREA_ID = %s""",
            [req.idempotency_key, req.area_id],
        )
        if existing:
            return _row_to_report(existing), False, False
        # Legacy rows and a write interrupted before key registration still
        # retain their latest key on REPORTS. Preserve it before the next move.
        existing = sf.query_one(
            "SELECT * FROM REPORTS WHERE IDEMPOTENCY_KEY = %s AND AREA_ID = %s",
            [req.idempotency_key, req.area_id],
        )
        if existing:
            _remember_request(req.area_id, req.idempotency_key, existing["REPORT_ID"])
            return _row_to_report(existing), False, False

    received_at = now_utc()
    if req.kind == ReportKind.rescue_needed and req.device_id:
        prior = sf.query_one(
            """SELECT * FROM REPORTS WHERE DEVICE_ID = %s AND KIND = %s
               AND VERIFICATION_STATE <> %s ORDER BY RECEIVED_AT DESC LIMIT 1""",
            [req.device_id, ReportKind.rescue_needed.value, VerificationState.resolved.value],
        )
        if prior:
            prior_report = _row_to_report(prior)
            same_spot = prior["AREA_ID"] == req.area_id and _meters_apart(
                prior["LATITUDE"], prior["LONGITUDE"], req.location.lat, req.location.lng
            ) <= SAME_SPOT_METERS
            # Same spot, still a live recent SOS: keep the pin and state, only take a new message.
            refresh_only = (
                same_spot
                and prior_report.verification_state in LIVE_SOS_STATES
                and (received_at - prior_report.received_at).total_seconds() < SOS_GUARD_SECONDS
            )
            if refresh_only and req.message == prior["MESSAGE"]:
                raise conflict(
                    "Your location is already shared and you have already requested SOS. "
                    "Responders can see you. Only send again if you have moved.",
                    code="sos_already_sent",
                )
            _remember_request(prior["AREA_ID"], prior.get("IDEMPOTENCY_KEY"), prior["REPORT_ID"])
            if refresh_only:
                lng, lat, state = prior["LONGITUDE"], prior["LATITUDE"], prior["VERIFICATION_STATE"]
            else:
                lng, lat, state = req.location.lng, req.location.lat, VerificationState.unverified.value
            sf.execute(
                """UPDATE REPORTS SET AREA_ID = %s, LONGITUDE = %s, LATITUDE = %s,
                       MESSAGE = %s, REPORTED_AT = %s, RECEIVED_AT = %s,
                       VERIFICATION_STATE = %s, IDEMPOTENCY_KEY = %s WHERE REPORT_ID = %s""",
                [
                    req.area_id, lng, lat, req.message,
                    req.reported_at, received_at,
                    state, req.idempotency_key, prior["REPORT_ID"],
                ],
            )
            prior.update(
                AREA_ID=req.area_id, LONGITUDE=lng, LATITUDE=lat,
                MESSAGE=req.message, REPORTED_AT=req.reported_at, RECEIVED_AT=received_at,
                VERIFICATION_STATE=state,
            )
            _remember_request(req.area_id, req.idempotency_key, prior["REPORT_ID"])
            events.record_event(
                "report_update",
                f"rescue_needed {'updated' if refresh_only else 'moved'} in {req.area_id}",
                req.area_id,
            )
            return _row_to_report(prior), False, not refresh_only

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
               VERIFICATION_STATE, REPORTED_AT, RECEIVED_AT, IDEMPOTENCY_KEY, PROVENANCE, DEVICE_ID
           ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        [
            report.report_id, report.area_id, report.kind.value, report.message,
            report.location.lng, report.location.lat,
            report.verification_state.value, report.reported_at, report.received_at,
            req.idempotency_key, report.provenance, req.device_id,
        ],
    )
    _remember_request(req.area_id, req.idempotency_key, report.report_id)
    events.record_event(
        "distress_report" if req.kind != ReportKind.road_hazard else "road_closure",
        f"{req.kind.value} reported in {req.area_id}",
        req.area_id,
    )
    return report, True, False


def set_state(report_id: str, state: VerificationState) -> Report | None:
    row = sf.query_one("SELECT * FROM REPORTS WHERE REPORT_ID = %s", [report_id])
    if row is None:
        return None
    sf.execute(
        "UPDATE REPORTS SET VERIFICATION_STATE = %s WHERE REPORT_ID = %s",
        [state.value, report_id],
    )
    row["VERIFICATION_STATE"] = state.value
    report = _row_to_report(row)
    events.record_event(
        "report_update",
        f"{report.kind.value} marked {state.value} in {report.area_id}",
        report.area_id,
    )
    return report


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
