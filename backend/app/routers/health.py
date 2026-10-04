"""Readiness + publication-cache state."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..db import snowflake_client as sf
from ..services import cache
from ..util import iso, now_utc

router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    db_ok = sf.ping()
    initialized = cache.is_initialized()
    ready = db_ok and initialized
    state = "ready" if initialized else "uninitialized"
    payload = {
        "status": "ok" if ready else "degraded",
        "publication_state": state,
        "server_time": iso(now_utc()),
    }
    # 503 = backend not ready; the frontend must not read this as "no instruction".
    return JSONResponse(status_code=200 if ready else 503, content=payload)
