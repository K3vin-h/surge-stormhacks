"""Wipe committed reports, official messages, and the activity feed."""
from __future__ import annotations

from ..config import REPO_ROOT
from ..db import snowflake_client as sf
from . import cache

_TABLES = (
    ("REPORTS", "reports"),
    ("INSTRUCTIONS", "instructions"),
    ("EVENTS", "events"),
)
CLEARED_MARKER = REPO_ROOT / "backend" / ".demo-cleared"


def clear_slate() -> dict[str, int]:
    """Delete every report, instruction, and event, and drop the live cache."""
    counts: dict[str, int] = {}
    for table, key in _TABLES:
        row = sf.query_one(f"SELECT COUNT(*) AS N FROM {table}")
        counts[key] = int(next(iter(row.values()))) if row else 0
        sf.execute(f"DELETE FROM {table}")
    cache.hydrate({})
    CLEARED_MARKER.write_text("cleared\n", encoding="utf-8")
    return counts
