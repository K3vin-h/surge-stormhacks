"""Per-device conversation memory for the assistant.

In-memory and bounded (same trade-off as the response cache in cache.py):
history is lost on restart, idle conversations expire after IDLE_TTL_SECONDS,
and the oldest-used keys are evicted first. The caller picks the key; the
assistant uses device id + area + current instruction, so a new official
instruction or a different area starts a fresh history.
"""

from __future__ import annotations

import re
import threading
import time
from collections import OrderedDict, deque

MAX_MESSAGES_PER_DEVICE = 20  # stored
PROMPT_MESSAGES = 10  # replayed into the model prompt (5 exchanges)
MAX_DEVICES = 1000
MAX_MESSAGE_CHARS = 1000
IDLE_TTL_SECONDS = 3600

_lock = threading.Lock()
# key -> (messages, last_used), least recently used first.
_history: OrderedDict[str, tuple[deque[tuple[str, str]], float]] = OrderedDict()


def _clean(text: str) -> str:
    # Collapse whitespace and any run of "=" so stored text can't forge the
    # prompt's "===" section markers, then bound its size.
    return re.sub(r"=+", "=", " ".join(text.split()))[:MAX_MESSAGE_CHARS]


def get(key: str | None) -> list[tuple[str, str]]:
    """Most recent messages, oldest first, as (role, text); role is 'resident' or 'assistant'."""
    if not key:
        return []
    with _lock:
        entry = _history.get(key)
        if entry is None:
            return []
        msgs, last_used = entry
        if time.monotonic() - last_used > IDLE_TTL_SECONDS:
            del _history[key]
            return []
        return list(msgs)[-PROMPT_MESSAGES:]


def add_turn(key: str | None, question: str, reply: str) -> None:
    if not key:
        return
    with _lock:
        msgs = (
            _history[key][0]
            if key in _history
            else deque(maxlen=MAX_MESSAGES_PER_DEVICE)
        )
        msgs.append(("resident", _clean(question)))
        msgs.append(("assistant", _clean(reply)))
        _history[key] = (msgs, time.monotonic())
        _history.move_to_end(key)
        while len(_history) > MAX_DEVICES:
            _history.popitem(last=False)


def clear() -> None:
    with _lock:
        _history.clear()
