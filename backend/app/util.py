"""Small shared helpers."""
from __future__ import annotations

import base64
from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"offset:{offset}".encode()).decode()


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        return int(raw.split(":", 1)[1])
    except Exception:
        return 0


def next_cursor(offset: int, limit: int, count: int) -> str | None:
    # Only emit a cursor when a full page came back (more may remain).
    return encode_cursor(offset + limit) if count == limit else None
