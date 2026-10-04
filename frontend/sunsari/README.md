# Sunsari route planner

Open `/sunsari/` on the SURGE backend, or serve the entire `frontend/` directory over HTTP. The government dashboard opens this planner when Sunsari is selected. Both planner pages link to each other.

The page reuses the Rasuwa map, routing, and government modules, with its own frozen geographic dataset. Walking and vehicle searches follow actual shared OpenStreetMap road nodes and respect access tags, one-way roads, mode-specific barriers, and government road closures. Candidate destinations require review; they are not approved evacuation shelters. Routes exclude the unverified approach from a place or facility to its mapped access node.

The bundled snapshot contains 15,393 roads, 181 named origins, 336 mapped candidate facilities, and 12 municipal boundaries. A separate gray region identifies district land without a mapped municipal boundary. Missing sensors remain gray. All sensor readings are **simulated**, loaded from `data/sensors.json`; no observed flood extent or elevation certification is included.

## Rebuild the snapshot

Install `../rasuwa/tools/requirements.txt`, then run from the repository root:

```sh
python frontend/rasuwa/tools/import_sunsari.py
```

This downloads public data from Overpass for [Sunsari district relation 4589472](https://www.openstreetmap.org/relation/4589472), preserves shared road node IDs and access tags, and generates the source, simulated sensor JSON, and prepared graphs. Use `--snapshot path/to/overpass.json` to import an existing raw response.

After editing only the simulated sensor file, rebuild offline:

```sh
python frontend/rasuwa/tools/prepare.py \
  --source frontend/sunsari/data/source.json \
  --sensors frontend/sunsari/data/sensors.json \
  --output frontend/sunsari/data/prepared.json
```

Municipal boundaries use OSM administrative level 7; they are not certified ward boundaries. Snapshot provenance and retrieval time are recorded in `source.json` and `prepared.json`. Geography is © OpenStreetMap contributors, distributed under [ODbL 1.0](https://www.openstreetmap.org/copyright). Satellite imagery uses the shared Rasuwa configuration. Bundled geography and route search remain available when imagery cannot load.
