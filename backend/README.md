# SURGE backend (FastAPI)

Implements the frontend–backend API contract. Sits behind the Next.js
`/api/*` rewrite. All provider secrets (Gemini, ElevenLabs, Snowflake key)
stay here.

## Run

From the repo root. `.env` is optional; see `.env.example`.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\python -m pip install -r backend/requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8008
```

macOS and Linux:

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8008
```

Without Snowflake settings, startup creates `backend/local.db` and seeds it from `app/db/seed.py` when the tables are empty. That file stays on the machine that is running the server and is not committed. Published directives and dismissed cases are stored there until a Snowflake account is configured.

Tests (run from `backend/`):

```bash
../.venv/bin/python -m pip install -r requirements-dev.txt
../.venv/bin/python -m pytest
node ../frontend/tests/device-id.test.cjs
```

## What it does

- **Snowflake (optional):** published instructions, community reports, gov events.
  Tables auto-created on startup (`app/db/bootstrap.py`). Key-pair auth via
  `rsa_key.p8`. If the account, user, or key file is missing, the same tables
  are stored in local SQLite instead.
- **Fast read cache:** latest instruction per area, hydrated from Snowflake on
  startup, updated synchronously after each publish. This is what resident
  polling (`/api/public/status/{area_id}`) reads every 3s.
- **Gemini:** bounded topic classification only (`status | shelter | route |
  roads_to_avoid | next_update | unsupported`). Never authors directives.
  Falls back to a deterministic keyword classifier if the key is missing/invalid.
- **ElevenLabs:** `/api/voice` (Scribe STT) and `/api/tts` (audio/mpeg). Text is
  resolved server-side by ID; arbitrary text is never synthesized.
- **Models:** risk/damage/priority are transparent deterministic heuristics
  (`app/services/models.py`). Swap in real models there without touching routes.

## Area IDs

`sunsari`, `saptari`, `bardiya`, `kathmandu_valley`. Static catalog (shelters,
routes, roads, hospitals, geometry, signals) lives in `app/fixtures/areas.py`.

## Provider status flags

On startup the log prints
`Gemini enabled: <bool> (auth=<mode>) | ElevenLabs enabled: <bool>`.
Gemini is enabled whenever `GEMINI_API_KEY` is set. The auth mode is detected
from the value: a key starting with `AIza` is sent as an AI Studio API key
(`x-goog-api-key`); anything else is sent as an OAuth access token
(`Authorization: Bearer`). Any call failure degrades to the deterministic
keyword fallback, so the app keeps working.
