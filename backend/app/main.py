"""SURGE backend: FastAPI app behind the Next.js /api/* proxy."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import snowflake_client as sf
from .db.bootstrap import ensure_schema
from .errors import ApiError, api_error_handler, unhandled_error_handler
from .routers import areas, chat, demo_models, government, health, public
from .services import cache, instructions

log = logging.getLogger("surge")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("Gemini enabled: %s (auth=%s) | ElevenLabs enabled: %s",
             settings.gemini_enabled, settings.gemini_auth_mode,
             settings.elevenlabs_enabled)
    try:
        if sf.ping():
            ensure_schema()
            instructions.hydrate_cache()
            log.info("Snowflake ready; schema ensured; cache hydrated.")
        else:
            log.warning("Snowflake ping failed at startup; routes needing it will 503.")
    except Exception:  # pragma: no cover - startup resilience
        log.exception("Startup DB init failed; continuing in degraded mode.")
    yield


app = FastAPI(title="SURGE API", version="0.1.0", lifespan=lifespan)

# The browser hits same-origin /api/* via the Next.js rewrite, but allow direct
# localhost dev origins too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


@app.exception_handler(RequestValidationError)
async def _validation_handler(request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Invalid input.",
                "retryable": False,
                "request_id": request.headers.get("x-request-id", "n/a"),
                "detail": exc.errors(),
            }
        },
    )


app.include_router(health.router)
app.include_router(areas.router)
app.include_router(government.router)
app.include_router(public.router)
app.include_router(chat.router)
app.include_router(demo_models.router)

# Serve the bare-bones static frontend (gov dashboard + victim view).
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

# Clean URLs (no .html). Served WITHOUT a trailing slash so the pages'
# relative "common.js" still resolves to /common.js. Registered before the
# static mount so they take precedence.
_PAGES = {"/": "index.html", "/gov": "gov.html", "/victim": "victim.html"}


def _make_page_route(filename: str):
    def _route() -> FileResponse:
        return FileResponse(FRONTEND_DIR / filename)
    return _route


if FRONTEND_DIR.exists():
    for _path, _file in _PAGES.items():
        app.add_api_route(_path, _make_page_route(_file), include_in_schema=False)
    # Static mount last: serves common.js, assets, and the raw .html files too.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
