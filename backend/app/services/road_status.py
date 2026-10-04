"""Government-set road status, persisted in ROAD_STATUS (open roads have no row)."""

from __future__ import annotations

import functools
import hashlib
import json
import threading

from ..config import REPO_ROOT
from ..db import snowflake_client as sf
from ..errors import ApiError
from ..schemas.roads import RoadStatus, RoadStatusResponse
from ..util import now_utc
from . import events

AREA_ID = "rasuwa"

# Writers replace a row with DELETE + INSERT and readers must never see the gap
# (a closed road reading as open), so both sides hold this lock.
# ponytail: single-process lock; use one MERGE/upsert statement if the API ever runs multi-process.
_lock = threading.Lock()


PREPARED_JSON = REPO_ROOT / "frontend" / "rasuwa" / "data" / "prepared.json"

# ponytail: this process is the only writer, so the cache is never stale; multi-process needs a TTL or version row.
_cache: RoadStatusResponse | None = None


@functools.lru_cache(maxsize=1)
def allowed_road_ids() -> frozenset[str]:
    """Rasuwa road ids from the prepared graph; fails closed if it is unreadable."""
    try:
        data = json.loads(PREPARED_JSON.read_text(encoding="utf-8"))
        return frozenset(f["properties"]["id"] for f in data["map"]["roads"]["features"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ApiError(503, "road_data_unavailable", "Road network data is unavailable.") from exc


def invalidate() -> None:
    """Drop the cached response; the next read rebuilds it from the DB."""
    global _cache
    with _lock:
        _cache = None


def list_roads() -> RoadStatusResponse:
    global _cache
    with _lock:
        if _cache is None:
            _cache = _build()
        return _cache


def _build() -> RoadStatusResponse:
    """Read ROAD_STATUS; caller must hold _lock."""
    rows = sf.query(
        "SELECT ROAD_ID, STATUS, NOTE, UPDATED_AT FROM ROAD_STATUS ORDER BY ROAD_ID"
    )
    roads = [
        RoadStatus(
            road_id=r["ROAD_ID"],
            status=r["STATUS"],
            note=None if r["NOTE"] is None else str(r["NOTE"]),
            updated_at=r["UPDATED_AT"],
        )
        for r in rows
    ]
    # Content hash: changes whenever any road, status, note, or timestamp changes.
    digest = hashlib.sha1(
        "|".join(
            f"{r.road_id},{r.status},{r.note},{r.updated_at.isoformat()}" for r in roads
        ).encode()
    ).hexdigest()[:12]
    return RoadStatusResponse(version=digest if roads else "0", roads=roads)


def set_status(road_id: str, status: str, note: str | None) -> RoadStatus:
    global _cache
    now = now_utc()
    with _lock:
        existed = sf.query_one(
            "SELECT 1 AS X FROM ROAD_STATUS WHERE ROAD_ID = %s", [road_id]
        )
        sf.execute("DELETE FROM ROAD_STATUS WHERE ROAD_ID = %s", [road_id])
        if status != "open":
            sf.execute(
                "INSERT INTO ROAD_STATUS (ROAD_ID, STATUS, NOTE, UPDATED_AT) VALUES (%s, %s, %s, %s)",
                [road_id, status, note, now],
            )
        _cache = _build()
    if existed or status != "open":
        events.record_event("road_status", f"Road {road_id} set to {status}", AREA_ID)
    return RoadStatus(road_id=road_id, status=status, note=note, updated_at=now)
