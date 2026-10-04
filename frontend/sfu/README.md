# SFU Burnaby campus walking map

A basic walking map for Simon Fraser University's Burnaby campus, at 8888 University Drive West. Choose a start and destination, swap them, or click a landmark to route to it.

## Run

The SURGE backend serves this page at `/sfu/`. The standalone map server also serves it:

```sh
cd frontend/rasuwa
npm ci
npm run serve
```

Open http://127.0.0.1:3010/sfu/. The government dashboard's route planner includes an **SFU Burnaby** button; both regional planner sidebars also link here.

## Data and routing

`data/campus.json` contains a bundled OpenStreetMap snapshot of campus pedestrian paths, selected building outlines, and eight landmarks. The graph uses shared mapped node IDs during extraction, retaining the largest connected pedestrian network around the main campus. Distances use mapped path lengths and the shared Dijkstra route search. Landmark markers connect to the nearest node in that network; final approaches to building entrances are not included in the distance.

Routes may include stairs, covered paths, and mapped indoor connections. They do not provide floor-by-floor directions, verified step-free access, or live closure information.

## Simulated sensors and flooded regions

`data/sensors.json` defines three fictional campus sectors: West (Low risk), Central (High risk), and East (Extreme risk and simulated flooding). These rectangular sectors are demo boundaries, not official SFU regions or observed flood extents. Each has simulated 24-hour rainfall, a water-level-to-warning ratio for fictional campus drainage, soil moisture, and a timezone-aware timestamp.

The browser calculates the same weighted heuristic used by the regional planners: `0.45 × min(rainfall/150, 1) + 0.40 × min(water_ratio/1.2, 1) + 0.15 × soil_moisture/100`. Thresholds are 0.30 Moderate, 0.55 High, and 0.80 Extreme. Missing readings remain Unknown. The separate `simulated_flood` flag defines the fictional flooded extent; the sensor score is not a flood prediction.

The map shows colored sectors, a legend, sensor cards, and region-click details. **Avoid simulated flooded areas** is enabled by default. It conservatively blocks an entire mapped path if any segment touches a flooded sector. Destinations in that sector may have no route. Unchecking the option restores ordinary campus walking routes while retaining the flood overlay. Changes to this JSON file are used on reload without rebuilding the campus geography.

Background tiles require internet. Bundled paths, landmarks, and route search remain available if tiles fail. Campus location names can be checked against the [official SFU campus map](https://www.sfu.ca/campuses/maps-and-directions/burnaby-map/).

Geographic data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), licensed under ODbL 1.0. Dataset source and retrieval timestamp are recorded in the snapshot. MapLibre assets retain their existing license.
