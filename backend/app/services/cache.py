"""In-memory publication cache: the latest committed instruction per area.

This is the fast read layer the resident polling hits. It is hydrated from
Snowflake on startup and updated synchronously after each successful publish.
Also caches recent assistant responses so TTS can resolve them by ID.
"""
from __future__ import annotations

import threading

from ..schemas.common import (
    PublicationFreshness,
    PublicationState,
)
from ..schemas.instructions import PublishedInstruction
from ..util import now_utc

_lock = threading.RLock()
# area_id -> PublishedInstruction (latest)
_current: dict[str, PublishedInstruction] = {}
_initialized = False

# response_id -> text, for TTS resolution (bounded LRU-ish).
_responses: dict[str, str] = {}
_response_order: list[str] = []
_MAX_RESPONSES = 500


def mark_initialized() -> None:
    global _initialized
    with _lock:
        _initialized = True


def is_initialized() -> bool:
    with _lock:
        return _initialized


def set_current(instruction: PublishedInstruction) -> None:
    with _lock:
        _current[instruction.area_id] = instruction


def get_current(area_id: str) -> PublishedInstruction | None:
    with _lock:
        return _current.get(area_id)


def hydrate(instructions: dict[str, PublishedInstruction]) -> None:
    with _lock:
        _current.clear()
        _current.update(instructions)
        mark_initialized()


def freshness(area_id: str | None = None) -> PublicationFreshness:
    with _lock:
        if not _initialized:
            state = PublicationState.uninitialized
        else:
            state = PublicationState.ready
        current = _current.get(area_id) if area_id else None
        return PublicationFreshness(
            publication_state=state,
            current_instruction_id=current.publication_id if current else None,
            published_at=current.published_at if current else None,
            next_update_at=current.next_update_at if current else None,
            server_time=now_utc(),
        )


def remember_response(response_id: str, text: str) -> None:
    with _lock:
        _responses[response_id] = text
        _response_order.append(response_id)
        while len(_response_order) > _MAX_RESPONSES:
            old = _response_order.pop(0)
            _responses.pop(old, None)


def get_response_text(response_id: str) -> str | None:
    with _lock:
        return _responses.get(response_id)
