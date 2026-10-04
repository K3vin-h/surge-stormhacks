# SURGE

Flood response intelligence: a government dashboard, a resident app, and the Rasuwa route planner. Pages and demo data live in this repo. Nothing has to be created on one person's machine first.

## Run

From the repo root, with Python 3.11+:

```sh
python -m venv .venv
```

Windows:

```sh
.venv\Scripts\python -m pip install -r backend/requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8008
```

macOS and Linux:

```sh
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8008
```

Open http://127.0.0.1:8008/ . The same server serves the home page, `/gov`, `/victim`, and `/rasuwa/`.

No `.env`, Snowflake account, Gemini key, or ElevenLabs key is required. Without them the API stores instructions, reports, and events in `backend/local.db` (gitignored, created on first start) and fills an empty database from `backend/app/db/seed.py`. Everyone who clones the repo gets the same demo. Copy `.env.example` to `.env` only when connecting a real Snowflake account or the voice providers.

The migrated **Rasuwa map and route planner** is also linked from the government page. Its geography and MapLibre files are in the repo. See [its demo and tests](frontend/rasuwa/README.md). The planner alone can be served with `npm run serve` from `frontend/rasuwa`.

```sh
cd frontend/rasuwa
npm ci
npm run serve
```

Open http://127.0.0.1:3010/rasuwa/. No backend, API keys, or model training is required for this planner.
