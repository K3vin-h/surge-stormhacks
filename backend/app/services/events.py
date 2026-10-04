"""Government operational event feed, persisted to Snowflake EVENTS."""
from __future__ import annotations

import uuid

from ..db import snowflake_client as sf
from ..schemas.instructions import GovEvent
from ..util import now_utc


def record_event(kind: str, summary: str, area_id: str | None = None) -> GovEvent:
    event = GovEvent(
        event_id=str(uuid.uuid4()),
        kind=kind,
        area_id=area_id,
        summary=summary,
        created_at=now_utc(),
    )
    sf.execute(
        "INSERT INTO EVENTS (EVENT_ID, KIND, AREA_ID, SUMMARY, CREATED_AT) "
        "VALUES (%s, %s, %s, %s, %s)",
        [event.event_id, event.kind, event.area_id, event.summary, event.created_at],
    )
    return event


def list_events(limit: int = 20, offset: int = 0, area_id: str | None = None) -> list[GovEvent]:
    where = ""
    params: list = []
    if area_id:
        where = "WHERE AREA_ID = %s"
        params.append(area_id)
    params.extend([limit, offset])
    rows = sf.query(
        f"""SELECT EVENT_ID, KIND, AREA_ID, SUMMARY, CREATED_AT
            FROM EVENTS {where}
            ORDER BY CREATED_AT DESC
            LIMIT %s OFFSET %s""",
        params,
    )
    return [
        GovEvent(
            event_id=r["EVENT_ID"], kind=r["KIND"], area_id=r["AREA_ID"],
            summary=r["SUMMARY"], created_at=r["CREATED_AT"],
        )
        for r in rows
    ]
