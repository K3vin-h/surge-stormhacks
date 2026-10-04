# Rasuwa map and route planner

This extends the standalone Rasuwa map and evacuation-candidate routing migrated from [`stormhacks-26`](https://github.com/awang1809/stormhacks-26), source commit `8b3c7ad189edc6f2cd354e5479ec59a7238c3edb`. It uses plain HTML/JavaScript, a JSON sensor heuristic, and an optional government workspace connected to the existing SURGE API. It does not import the source repository's backend or trained models.

## Run without a backend

Use Node.js 20 or newer and Python 3 for the static development server:

```sh
cd frontend/rasuwa
npm ci
npm run serve
```

Open **http://127.0.0.1:3010/rasuwa/**. The SURGE home page also links to the planner. `npm ci` copies the pinned MapLibre distribution, worker, shared module, CSS, and license into the ignored `vendor/` directory. No bundler or Next.js server is needed. Do not open the HTML as a `file://` URL: browser module and data fetching require HTTP.

The existing SURGE backend already serves `frontend/` as static files. Once `npm ci` has prepared the assets, `/rasuwa/` can also be opened on that existing server. Local routing makes **no `/api/` requests** until **Connect government API** is clicked. On the backend server, that button loads ranked areas, current directives, operational events, and reports, and enables publishing and model refresh. The API areas are Sunsari, Saptari, Bardiya, and Kathmandu Valley; they are explicitly separate from the Rasuwa geographic map. A static-only server shows an unavailable status for government operations while local routing continues.

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

The assessed transport corridor is **85.25–85.45°E, 28.10–28.40°N**, intersected with the included wards. All district/ward geography is colored; gray marks unassessed geography or missing sensor readings. Within coverage, the JSON sensor risk is combined with the synthetic river footprint and 100 m/300 m proximity bands, taking the higher risk. These colors are not validated flood predictions or operational safety assessments.

Edit `data/sensors.json`, then run `tools/prepare.py` to update the bundled map and routing eligibility. Each ward reading includes `ward_id`, a timezone-aware `observed_at`, `rainfall_mm_24h`, `river_level_ratio` (level divided by the local warning level), and `soil_moisture_pct`. The included readings are explicitly simulated. The heuristic score is `0.45 × min(rainfall/150, 1) + 0.40 × min(river_ratio/1.2, 1) + 0.15 × soil_moisture/100`. Thresholds are 0.30 Moderate, 0.55 High, and 0.80 Extreme. Missing readings are Unknown and cannot qualify a destination as Low risk. Invalid numeric values and duplicate ward readings fail preparation. Readings, provenance, and timestamps appear in the UI and region click details. This is a frozen snapshot, not a live sensor feed.

Destinations must be in the assessed Low zone; entire ground patches must also have assessed coverage and avoid the configured hazard. Walking/vehicle graphs preserve mapped access restrictions, barriers, configured road closures, and vehicle one-way direction. A route is never invented across unmapped ground. No available route means this snapshot/scenario found no admissible connection, not that no real-world route exists.

Permission, capacity, structural condition/ground usability, landslide exposure, current field access, and final approaches remain unverified. No reviewed elevation dataset is present, so **high-ground certification is not implemented**. Camera tilt does not provide measured terrain.

## Components

| File | Responsibility |
|---|---|
| `index.html`, `styles.css`, `app.js` | Standalone planner UI, data loading, review and selection |
| `map-view.js` | MapLibre geographic layers, village clicks, route display and camera controls |
| `routing.js` | Browser-side Dijkstra search, candidate ranking, mode/distance validation |
| `config.js` | Public imagery URL, attribution, and optional label glyph source |
| `government.js` | Ranked areas, reports, events, model refresh and directive publishing through the existing API |
| `data/sensors.json` | Editable simulated per-ward sensor readings used during preparation |
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

The Node suite compares all **56 origin/mode combinations** against an independently exported reference, allowing only destinations excluded by the new sensor risk to differ. Remaining candidate IDs, distances, and road IDs must match. It also verifies that route segments are permitted directed graph edges. Browser tests use a static server on port 3011 and cover local routing, load failure, mobile layout, government API failure, and publication to the selected area using intercepted API responses. They also verify that community report content renders as text. These tests do not publish a live directive.

To check or regenerate geographic preparation, use Python **3.11+**:

```sh
cd frontend/rasuwa
python3 -m venv tools/.venv
tools/.venv/bin/python -m pip install -r tools/requirements.txt
tools/.venv/bin/python -m unittest discover -s tools -p 'test_*.py' -v
# After deliberately changing the source scenario or sensors.json:
tools/.venv/bin/python tools/prepare.py
```

Preparation uses Shapely/pyproj to compute overlays and graph admission, once per dataset. It repairs polygon topology and clips projected bands back to original geographic coverage/wards. The prepared version includes a content fingerprint, so changing the scenario changes the version. The bundled-snapshot test detects drift. Regeneration has no network/provider dependency, no server process, and no training step. No importer refresh against live OSM is included: this migration intentionally retains the verified frozen source snapshot.

The source-reference snapshot remains tied to the original geographic scenario. Sensor eligibility changes may exclude destinations, while remaining routes retain the original reference distances and roads.

## Verification

- 6 Node tests passed, including all 56 reference cases with sensor exclusions.
- 13 preparation tests passed, including sensor changes, unknown coverage, invalid readings and explicit motorcar permission overrides.
- 6 Chromium browser tests passed, including government publication with intercepted API responses.
- `backend/` and the source repository's implementation were not modified.

Live government publication and provider integrations were not exercised. The government UI reuses the existing backend contract; it does not add Rasuwa to that backend's area catalog.
