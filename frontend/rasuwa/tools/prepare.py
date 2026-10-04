"""Prepare geographic overlays and admissible transport graphs, without a server.

Run only when changing the bundled scenario. Browser searches require no Python.
Ported from stormhacks-26's Rasuwa service; no backend imports or provider keys.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
VEHICLE_ROADS = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "service", "living_street"}


def sensor_index(sensors):
    readings = {}
    for reading in sensors["readings"]:
        ward = reading["ward_id"]
        if ward in readings:
            raise ValueError(f"Duplicate sensor reading for {ward}")
        for field, maximum in [("rainfall_mm_24h", None), ("river_level_ratio", None), ("soil_moisture_pct", 100)]:
            value = reading[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or (maximum is not None and value > maximum):
                raise ValueError(f"Invalid {field} for {ward}")
        observed = datetime.fromisoformat(reading["observed_at"].replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("Sensor timestamps must include a timezone")
        score = (0.45 * min(reading["rainfall_mm_24h"] / 150, 1)
                 + 0.40 * min(reading["river_level_ratio"] / 1.2, 1)
                 + 0.15 * reading["soil_moisture_pct"] / 100)
        level = "Extreme" if score >= .8 else "High" if score >= .55 else "Moderate" if score >= .3 else "Low"
        readings[ward] = {**reading, "sensor_score": round(score, 3), "sensor_risk_level": level}
    return readings


def risk_zones(data, sensors=None):
    project = Transformer.from_crs(4326, 32645, always_xy=True).transform
    unproject = Transformer.from_crs(32645, 4326, always_xy=True).transform
    coverage = make_valid(shape(data["coverage"]))
    assessed = transform(project, coverage)
    flooded = transform(project, shape(data["hazards"])).intersection(assessed)
    high = flooded.buffer(100).intersection(assessed)
    moderate = flooded.buffer(300).intersection(assessed)
    bands = [("Extreme", flooded), ("High", high.difference(flooded)),
             ("Moderate", moderate.difference(high)), ("Low", assessed.difference(moderate))]
    features = []
    readings = sensor_index(sensors) if sensors is not None else {}
    levels = ["Low", "Moderate", "High", "Extreme"]
    wards = data.get("wards") or [{"properties": {"id": "coverage", "name": "Analysis coverage"}, "geometry": data["coverage"]}]
    for ward in wards:
        ward_shape = make_valid(shape(ward["geometry"]))
        cell = transform(project, ward_shape)
        reading = readings.get(ward["properties"]["id"])
        common = {"ward_id": ward["properties"]["id"], "ward_name": ward["properties"]["name"],
                  "provenance": sensors.get("provenance", "unspecified") if sensors is not None else "simulated_proximity_bands",
                  "model_version": "sensor-hazard-heuristic-v1" if sensors is not None else "demo-bands-v1",
                  **(reading or {})}
        if sensors is not None:
            unknown = ward_shape if reading is None else ward_shape.difference(coverage)
            if not unknown.is_empty and unknown.area > 0:
                features.append({"type": "Feature", "geometry": mapping(unknown), "properties": {**common, "risk_level": "Unknown"}})
            if reading is None:
                continue
        for level, band in bands:
            polygon = band.intersection(cell)
            if polygon.is_empty or polygon.area < 1:
                continue
            polygon = polygon.simplify(0.5, preserve_topology=True)
            # Projection round trips can extend a band a few centimetres beyond
            # the original geographic boundary. Clip again in the source CRS.
            geographic = make_valid(transform(unproject, polygon)).intersection(coverage).intersection(ward_shape)
            if geographic.is_empty or geographic.area == 0:
                continue
            effective = levels[max(levels.index(level), levels.index(reading["sensor_risk_level"]))] if reading else level
            features.append({"type": "Feature", "geometry": mapping(geographic), "properties": {**common, "risk_level": effective}})
    return {"type": "FeatureCollection", "features": features}


def prepare(data, sensors=None):
    coverage, hazard = shape(data["coverage"]), shape(data["hazards"])
    project = Transformer.from_crs(4326, 32645, always_xy=True).transform
    zones = risk_zones(data, sensors)
    low = unary_union([shape(f["geometry"]) for f in zones["features"] if f["properties"]["risk_level"] == "Low"])
    closed, barriers = set(data["closed_road_ids"]), set(data.get("blocked_node_ids", []))
    graphs = {}
    for mode in ("walking", "vehicle"):
        nodes, adjacency = {}, {}
        for road in data["roads"]:
            props = road["properties"]
            tags = props["tags"]
            coords, ids = road["geometry"]["coordinates"], props["node_ids"]
            if props["id"] in closed or len(ids) != len(coords):
                continue
            specific = tags.get("foot") if mode == "walking" else tags.get("motorcar", tags.get("motor_vehicle", tags.get("vehicle")))
            if specific in ("no", "private") or (tags.get("access") in ("no", "private") and specific not in ("yes", "designated", "permissive")):
                continue
            if mode == "vehicle" and tags.get("highway") not in VEHICLE_ROADS:
                continue
            if mode == "walking" and tags.get("highway") in ("motorway", "motorway_link", "construction", "proposed"):
                continue
            for a, b, ca, cb in zip(ids, ids[1:], coords, coords[1:]):
                line = LineString([ca, cb])
                if a in barriers or b in barriers or not coverage.covers(line) or hazard.intersects(line):
                    continue
                a, b = str(a), str(b)
                nodes[a], nodes[b] = ca, cb
                length = math.dist(project(*ca), project(*cb))
                oneway = tags.get("oneway", "yes" if tags.get("junction") == "roundabout" else "no")
                if mode == "walking" or oneway != "-1":
                    adjacency.setdefault(a, {})[b] = [b, length, props["id"]]
                if mode == "walking" or oneway not in ("yes", "1", "true"):
                    adjacency.setdefault(b, {})[a] = [a, length, props["id"]]

        projected = {n: project(*c) for n, c in nodes.items()}

        def attach(coordinate):
            point = Point(coordinate)
            if not coverage.covers(point) or hazard.intersects(point):
                return None
            position = project(*coordinate)
            options = []
            for node, c in nodes.items():
                distance = math.dist(position, projected[node])
                if distance > data["routing"]["max_snap_m"]:
                    continue
                connector = LineString([coordinate, c])
                if coverage.covers(connector) and not hazard.intersects(connector):
                    options.append((distance, node))
            return min(options)[1] if options else None

        destinations, exclusions = [], {}
        entries = [(f, "facility") for f in data["facilities"]] + [(f, "open_ground") for f in data.get("open_ground", [])]
        for feature, kind in sorted(entries, key=lambda entry: entry[0]["properties"]["id"]):
            p = feature["properties"]
            targets = []
            if kind == "open_ground":
                polygon = shape(feature["geometry"])
                if not coverage.covers(polygon) or hazard.intersects(polygon) or not low.covers(polygon):
                    exclusions[p["id"]] = "Open ground is not wholly inside an assessed Low-risk zone."
                    continue
                targets = [n for n, c in nodes.items() if polygon.covers(Point(c))]
                location = list(polygon.representative_point().coords[0])
            else:
                location = feature["geometry"]["coordinates"]
                if not low.covers(Point(location)):
                    exclusions[p["id"]] = "Facility is outside the assessed Low-risk zones."
                    continue
            destinations.append({"id": p["id"], "name": p["name"], "source": p["source"], "kind": kind,
                                 "targets": targets, "fallback": attach(location), "location": location})
        graphs[mode] = {"nodes": nodes, "edges": {n: list(adj.values()) for n, adj in adjacency.items()},
                        "origins": {f["properties"]["id"]: attach(f["geometry"]["coordinates"]) for f in data["settlements"]},
                        "destinations": destinations, "exclusions": exclusions}
    map_data = {k: {"type": "FeatureCollection", "features": data.get(k, [])} for k in ("district", "wards", "settlements", "facilities", "open_ground")}
    map_data.update(risk_zones=zones, coverage=data["coverage"], hazards=data["hazards"], roads={"type": "FeatureCollection", "features": [
        {**road, "properties": {**road["properties"], "closed": road["properties"]["id"] in closed,
                              "highway": road["properties"]["tags"].get("highway", "unknown")}} for road in data["roads"]]})
    fingerprint = hashlib.sha256(json.dumps([data, sensors], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()[:12]
    return {"format_version": 1, "dataset_version": f"{data['dataset_version']}-{fingerprint}", "source_dataset_version": data["dataset_version"], "scenario": data["scenario"],
            "manifest": data["manifest"], "sensors": sensors, "map": map_data, "graphs": graphs}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data" / "source.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "prepared.json")
    parser.add_argument("--sensors", type=Path, default=ROOT / "data" / "sensors.json")
    args = parser.parse_args()
    result = prepare(json.loads(args.source.read_text()), json.loads(args.sensors.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    print(f"Prepared {result['dataset_version']}: {len(result['map']['settlements']['features'])} origins; walking and vehicle graphs")
