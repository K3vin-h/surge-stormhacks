# SURGE backend (FastAPI)

Implements the frontend–backend API contract. Sits behind the Next.js
`/api/*` rewrite. All provider secrets (Gemini, ElevenLabs, Snowflake key)
stay here.

## Run

From the repo root (the venv and `.env` live there):

```bash
source .venv/Scripts/activate           # Windows Git Bash
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8008
```

Point `API_PROXY_TARGET` (Next.js) at `http://127.0.0.1:8008`.

## What it does

- **Snowflake (durable):** published instructions, community reports, gov events.
  Tables auto-created on startup (`app/db/bootstrap.py`). Key-pair auth via
  `rsa_key.p8`.
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
