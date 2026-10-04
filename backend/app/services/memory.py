"""Per-device conversation memory for the assistant.

In-memory and bounded (same trade-off as the response cache in cache.py):
history is lost on restart, and the oldest-used devices are evicted first.
Keyed by the client's device UUID.
"""

from __future__ import annotations

import threading
from collections import OrderedDict, deque

MAX_MESSAGES_PER_DEVICE = 20  # stored
PROMPT_MESSAGES = 10  # replayed into the model prompt (5 exchanges)
MAX_DEVICES = 1000
MAX_MESSAGE_CHARS = 1000

_lock = threading.Lock()
# device_id -> deque[(role, text)], least recently used first.
_history: OrderedDict[str, deque[tuple[str, str]]] = OrderedDict()


def _clean(text: str) -> str:
    # Bound memory and keep stored text from forging the prompt's "===" section markers (newlines collapsed too).
    return " ".join(text[:MAX_MESSAGE_CHARS].split()).replace("===", "=")


def get(device_id: str | None) -> list[tuple[str, str]]:
    """Most recent messages, oldest first, as (role, text); role is 'resident' or 'assistant'."""
    if not device_id:
        return []
    with _lock:
        msgs = _history.get(device_id)
        return list(msgs)[-PROMPT_MESSAGES:] if msgs else []


def add_turn(device_id: str | None, question: str, reply: str) -> None:
    if not device_id:
        return
    with _lock:
        msgs = _history.setdefault(device_id, deque(maxlen=MAX_MESSAGES_PER_DEVICE))
        msgs.append(("resident", _clean(question)))
        msgs.append(("assistant", _clean(reply)))
        _history.move_to_end(device_id)
        while len(_history) > MAX_DEVICES:
            _history.popitem(last=False)


def clear() -> None:
    with _lock:
        _history.clear()
