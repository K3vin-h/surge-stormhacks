# Rasuwa map and route planner

This is a standalone migration of the Rasuwa geographic map and evacuation-candidate routing from [`stormhacks-26`](https://github.com/awang1809/stormhacks-26), source commit `8b3c7ad189edc6f2cd354e5479ec59a7238c3edb`. It uses this repository's plain HTML/JavaScript frontend. It imports neither repository's backend, the rainfall model, nor the satellite-damage/priority models. Government publication and the assistant are outside this migration.

## Run without a backend

Use Node.js 20 or newer and Python 3 for the static development server:

```sh
cd frontend/rasuwa
npm ci
npm run serve
```

Open **http://127.0.0.1:3010/rasuwa/**. The SURGE home page also links to the planner. `npm ci` copies the pinned MapLibre distribution, worker, shared module, CSS, and license into the ignored `vendor/` directory. No bundler or Next.js server is needed. Do not open the HTML as a `file://` URL: browser module and data fetching require HTTP.

The existing SURGE backend already serves `frontend/` as static files. Once `npm ci` has prepared the assets, `/rasuwa/` can also be opened on that existing server without changing its code. The planner makes **no `/api/` requests** and does not require Snowflake, Gemini, ElevenLabs, or API keys. The backend, original government dashboard, and resident app are unchanged.

For any static deployment, publish `frontend/` with the generated `rasuwa/vendor/` assets included. Do not deploy just the HTML page or omit its modules/data. Existing government/resident pages still require their existing backend; this standalone serving command is specifically for the new planner.

## Try the nearby destination

1. Set **Walking limit (metres)** to **500** and **Vehicle limit (metres)** to **500**.
2. Select **National Rainbow Trout Research Station, Dhunche** from the origin list, or click a mapped origin.
3. Select **Pasture demonstration plots**. The walking route is **334.9 m**; the vehicle route is **344.6 m**.
4. Inspect the source and the listed access/suitability uncertainties. Switching mode recomputes routes; it does not reuse the selected walking path.
5. Set the active limit to **100 m**. The option and selected route disappear.
6. Click **Map overview** to inspect the broader ward boundaries and red/orange/yellow/green overlays. Zoom, pan, and camera tilt are available.

Limits have no automatic default. Distances are along mapped graph edges, excluding unverified approaches from markers to the road/path. Selecting a candidate only changes the current page. It resets on reload and does not publish an evacuation instruction.

## Included geography and scenario

The bundled source contains one Rasuwa district outline, six Gosaikunda ward boundaries, 28 mapped origin/settlement points, 12 facilities, 1,008 transport ways, and five open-ground polygons. Some origin labels are mapped research stations or unnamed OSM points rather than verified villages. Features retain OpenStreetMap IDs, tags, and source links; the snapshot's source manifest is included in both JSON files.

The assessed transport corridor is **85.25–85.45°E, 28.10–28.40°N**, intersected with the included wards. Uncolored geography outside coverage is context, not assessed territory. The river-buffer footprint is synthetic. Red is the simulated footprint; orange/yellow are illustrative 100 m/300 m proximity bands; green is the remaining assessed coverage. These colors are not flood predictions or operational safety assessments.

Destinations must be in the simulated Low zone; entire ground patches must also have assessed coverage and avoid the configured hazard. Walking/vehicle graphs preserve mapped access restrictions, barriers, configured road closures, and vehicle one-way direction. A route is never invented across unmapped ground. No available route means this snapshot/scenario found no admissible connection, not that no real-world route exists.

Permission, capacity, structural condition/ground usability, landslide exposure, current field access, and final approaches remain unverified. No reviewed elevation dataset is present, so **high-ground certification is not implemented**. Camera tilt does not provide measured terrain.

## Components

| File | Responsibility |
|---|---|
| `index.html`, `styles.css`, `app.js` | Standalone planner UI, data loading, review and selection |
| `map-view.js` | MapLibre geographic layers, village clicks, route display and camera controls |
| `routing.js` | Browser-side Dijkstra search, candidate ranking, mode/distance validation |
| `config.js` | Public imagery URL, attribution, and optional label glyph source |
| `data/source.json` | Frozen, provenance-bearing OSM geography and synthetic scenario |
| `data/prepared.json` | Risk overlays, filtered graphs, origins and candidate access-node metadata |
| `tools/prepare.py` | Self-contained offline preparation; no backend imports |
| `tools/requirements.txt` | Geographic preparation dependencies only |
| `tests/`, `tools/test_prepare.py` | Routing parity, exclusions, startup/offline UI, mobile, and snapshot checks |

Satellite tiles and label glyphs need internet; local geometry and routing work without them. The renderer initializes local layers on style readiness rather than waiting for remote imagery. Edit `config.js` to change the imagery source, or set `satelliteTiles` to `''` to disable satellite imagery. WebGL is needed to draw the map; a renderer failure leaves list-based route search available.

The EOX 2025 mosaic is contextual background, not before/after flood evidence. Preserve the configured EOxCloudless attribution and check its [noncommercial licensing terms](https://cloudless.eox.at/) for your deployment. Geographic data is © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), under ODbL. MapLibre's BSD license is copied with the installed assets.

## Tests

```sh
cd frontend/rasuwa
npm ci
npm test
npx playwright install chromium
npm run test:browser
```

The Node suite compares all **56 origin/mode combinations** against an independently exported reference from the source model, including candidate IDs, distances, and road IDs. It also verifies that reconstructed route segments are permitted directed graph edges. Browser tests use a **static server only** on port 3011, abort external imagery/glyph requests, and assert that the planner sends no API requests. They cover distance/mode changes clearing selection, explicit load failure, and a 390 px mobile layout.

To check or regenerate geographic preparation, use Python **3.11+**:

```sh
cd frontend/rasuwa
python3 -m venv tools/.venv
tools/.venv/bin/python -m pip install -r tools/requirements.txt
tools/.venv/bin/python -m unittest discover -s tools -p 'test_*.py' -v
# Only after deliberately changing the source scenario:
tools/.venv/bin/python tools/prepare.py
```

Preparation uses Shapely/pyproj to compute overlays and graph admission, once per dataset. It repairs polygon topology and clips projected bands back to original geographic coverage/wards. The prepared version includes a content fingerprint, so changing the scenario changes the version. The bundled-snapshot test detects drift. Regeneration has no network/provider dependency, no server process, and no training step. No importer refresh against live OSM is included: this migration intentionally retains the verified frozen source snapshot.

The source-reference snapshot remains tied to the original scenario. If you deliberately change that scenario, review/update the reference expectations rather than treating a parity failure as harmless.

## Verification of this migration

- 6 Node tests passed, including all 56 source-reference cases.
- 9 preparation tests passed in an environment installed only from `tools/requirements.txt`.
- 4 Chromium browser tests passed using only a static server, with imagery/glyphs unavailable.
- Dependency audit reported 0 vulnerabilities.
- `backend/` and the source repository's implementation were not modified.

Live government publication, provider integrations, and the existing backend's behavior are not claimed as tested by this frontend migration.
