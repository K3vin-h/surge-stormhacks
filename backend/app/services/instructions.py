"""Publish, read, and hydrate government instructions.

The publish path is the system of record: validate -> resolve catalog IDs ->
derive severity -> snapshot route/shelter/roads -> write Snowflake -> update
the fast cache -> return success. The browser must not claim success earlier.
"""
from __future__ import annotations

import hashlib
import json

from ..db import snowflake_client as sf
from ..errors import conflict, not_found, validation_error
from ..fixtures import areas as fx
from ..schemas.common import InstructionType, Severity
from ..schemas.instructions import (
    Alert,
    PublishedInstruction,
    PublishInstructionRequest,
    RoadSnapshot,
    RouteSnapshot,
    ShelterSnapshot,
)
from ..util import now_utc
from . import cache, events

SEVERITY_BY_TYPE = {
    InstructionType.evacuate: Severity.critical,
    InstructionType.shelter_in_place: Severity.warning,
    InstructionType.advisory: Severity.advisory,
    InstructionType.all_clear: Severity.info,
}


def _fingerprint(req: PublishInstructionRequest) -> str:
    payload = {
        "area_id": req.area_id,
        "instruction_type": req.instruction_type.value,
        "emergency_message": req.emergency_message,
        "shelter_id": req.shelter_id,
        "approved_route_id": req.approved_route_id,
        "roads_to_avoid_ids": sorted(req.roads_to_avoid_ids),
        "cancels_instruction_id": req.cancels_instruction_id,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _validate(req: PublishInstructionRequest) -> None:
    if req.instruction_type == InstructionType.evacuate:
        if not req.shelter_id or not req.approved_route_id:
            raise validation_error(
                "evacuate requires both an approved shelter and route."
            )
    else:
        # Other types must not carry shelter/route per contract.
        if req.shelter_id or req.approved_route_id:
            raise validation_error(
                f"{req.instruction_type.value} must not include a shelter or route."
            )
    if req.instruction_type == InstructionType.all_clear and not req.cancels_instruction_id:
        raise validation_error(
            "all_clear requires cancels_instruction_id of the active instruction."
        )


def _resolve_snapshots(req: PublishInstructionRequest):
    shelter = route = None
    roads: list[RoadSnapshot] = []
    if req.shelter_id:
        s = fx.shelter_by_id(req.area_id, req.shelter_id)
        if not s:
            raise not_found(f"Unknown shelter_id '{req.shelter_id}'.")
        shelter = ShelterSnapshot(id=s["id"], name=s["name"], location=s.get("location"))
    if req.approved_route_id:
        r = fx.route_by_id(req.area_id, req.approved_route_id)
        if not r:
            raise not_found(f"Unknown approved_route_id '{req.approved_route_id}'.")
        route = RouteSnapshot(id=r["id"], name=r["name"], geometry=r.get("geometry"))
    for rid in req.roads_to_avoid_ids:
        rd = fx.road_by_id(req.area_id, rid)
        if not rd:
            raise not_found(f"Unknown road id '{rid}'.")
        roads.append(RoadSnapshot(id=rd["id"], name=rd["name"]))
    return shelter, route, roads


def _row_to_instruction(row: dict) -> PublishedInstruction:
    def _load(s):
        return json.loads(s) if s else None

    shelter = _load(row.get("SHELTER_JSON"))
    route = _load(row.get("APPROVED_ROUTE_JSON"))
    roads = _load(row.get("ROADS_TO_AVOID_JSON")) or []
    return PublishedInstruction(
        publication_id=row["PUBLICATION_ID"],
        area_id=row["AREA_ID"],
        instruction_type=InstructionType(row["INSTRUCTION_TYPE"]),
        severity=Severity(row["SEVERITY"]),
        emergency_message=row["EMERGENCY_MESSAGE"],
        shelter=ShelterSnapshot(**shelter) if shelter else None,
        approved_route=RouteSnapshot(**route) if route else None,
        roads_to_avoid=[RoadSnapshot(**r) for r in roads],
        cancels_instruction_id=row.get("CANCELS_INSTRUCTION_ID"),
        update_frequency_minutes=row.get("UPDATE_FREQUENCY_MINUTES"),
        next_update_at=row.get("NEXT_UPDATE_AT"),
        published_at=row["PUBLISHED_AT"],
    )


def get_by_id(publication_id: str) -> PublishedInstruction | None:
    row = sf.query_one(
        "SELECT * FROM INSTRUCTIONS WHERE PUBLICATION_ID = %s", [publication_id]
    )
    return _row_to_instruction(row) if row else None


def get_latest_for_area(area_id: str) -> PublishedInstruction | None:
    row = sf.query_one(
        """SELECT * FROM INSTRUCTIONS WHERE AREA_ID = %s
           ORDER BY PUBLISHED_AT DESC LIMIT 1""",
        [area_id],
    )
    return _row_to_instruction(row) if row else None


def list_history_for_area(
    area_id: str, limit: int = 20, offset: int = 0
) -> list[PublishedInstruction]:
    rows = sf.query(
        """SELECT * FROM INSTRUCTIONS WHERE AREA_ID = %s
           ORDER BY PUBLISHED_AT DESC LIMIT %s OFFSET %s""",
        [area_id, limit, offset],
    )
    return [_row_to_instruction(r) for r in rows]


def hydrate_cache() -> None:
    """Load the latest instruction per area into the cache on startup."""
    latest: dict[str, PublishedInstruction] = {}
    for area_id in fx.AREAS:
        inst = get_latest_for_area(area_id)
        if inst:
            latest[area_id] = inst
    cache.hydrate(latest)


def to_alert(inst: PublishedInstruction, superseded: bool = False) -> Alert:
    return Alert(
        instruction_id=inst.publication_id,
        area_id=inst.area_id,
        severity=inst.severity,
        instruction_type=inst.instruction_type,
        emergency_message=inst.emergency_message,
        published_at=inst.published_at,
        superseded=superseded,
    )


def publish(req: PublishInstructionRequest) -> PublishedInstruction:
    fingerprint = _fingerprint(req)
    existing = sf.query_one(
        "SELECT * FROM INSTRUCTIONS WHERE PUBLICATION_ID = %s", [req.publication_id]
    )
    if existing:
        # Idempotent replay (same id + same content) vs conflict.
        if existing.get("REQUEST_FINGERPRINT") == fingerprint:
            inst = _row_to_instruction(existing)
            cache.set_current(inst)
            return inst
        raise conflict(
            "publication_id already used with different content.",
            code="idempotency_conflict",
        )

    _validate(req)
    shelter, route, roads = _resolve_snapshots(req)
    severity = SEVERITY_BY_TYPE[req.instruction_type]
    published_at = now_utc()

    inst = PublishedInstruction(
        publication_id=req.publication_id,
        area_id=req.area_id,
        instruction_type=req.instruction_type,
        severity=severity,
        emergency_message=req.emergency_message,
        shelter=shelter,
        approved_route=route,
        roads_to_avoid=roads,
        cancels_instruction_id=req.cancels_instruction_id,
        update_frequency_minutes=req.update_frequency_minutes,
        next_update_at=req.next_update_at,
        published_at=published_at,
    )

    sf.execute(
        """INSERT INTO INSTRUCTIONS (
               PUBLICATION_ID, AREA_ID, INSTRUCTION_TYPE, SEVERITY, EMERGENCY_MESSAGE,
               SHELTER_ID, SHELTER_JSON, APPROVED_ROUTE_ID, APPROVED_ROUTE_JSON,
               ROADS_TO_AVOID_JSON, CANCELS_INSTRUCTION_ID, UPDATE_FREQUENCY_MINUTES,
               NEXT_UPDATE_AT, PUBLISHED_AT, REQUEST_FINGERPRINT
           ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        [
            inst.publication_id, inst.area_id, inst.instruction_type.value,
            inst.severity.value, inst.emergency_message,
            req.shelter_id, json.dumps(shelter.model_dump()) if shelter else None,
            req.approved_route_id, json.dumps(route.model_dump()) if route else None,
            json.dumps([r.model_dump() for r in roads]),
            req.cancels_instruction_id, req.update_frequency_minutes,
            inst.next_update_at, inst.published_at, fingerprint,
        ],
    )

    # Only after the durable write succeeds do we update the fast cache.
    cache.set_current(inst)
    events.record_event(
        "publication",
        f"{inst.instruction_type.value} published for {inst.area_id}",
        inst.area_id,
    )
    return inst
