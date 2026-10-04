# SURGE

The existing government and resident interfaces are served by the [SURGE backend](backend/README.md).

The migrated **Rasuwa map and route planner** runs independently at `/rasuwa/`. It includes real ward/village geography, nearby destination candidates, risk overlays, and separate walking/vehicle route searches. See [its setup, demo, and tests](frontend/rasuwa/README.md).

```sh
cd frontend/rasuwa
npm ci
npm run serve
```

Open http://127.0.0.1:3010/rasuwa/. No backend, API keys, or model training is required for this planner.
