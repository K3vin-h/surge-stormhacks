"""Import a reproducible Sunsari OSM snapshot, then use the shared preparation engine.

Run with --snapshot for an existing Overpass JSON response, or without it to
download public OSM data. Sensor values are explicitly simulated.
"""
import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from shapely import make_valid
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import polygonize, unary_union

from prepare import prepare

RELATION_ID = 4589472
ENDPOINT = "https://overpass-api.de/api/interpreter"
QUERY = f"""[out:json][timeout:180];
rel({RELATION_ID})->.boundary;
.boundary map_to_area->.district;
(.boundary;
 way(area.district)[highway];
 node(area.district)[place~"^(city|town|village|hamlet)$"];
 nwr(area.district)[amenity~"^(school|community_centre|hospital|shelter)$"];
 rel(area.district)[boundary=administrative][admin_level=7];
 node(area.district)[barrier];
);out geom;"""


def polygon(element):
    """Assemble the outer/inner ways of an OSM administrative relation."""
    rings = {"outer": [], "inner": []}
    for member in element.get("members", []):
        geometry = member.get("geometry") or []
        if member.get("type") == "way" and len(geometry) >= 2:
            role = member.get("role") or "outer"
            if role in rings:
                rings[role].append(LineString([(p["lon"], p["lat"]) for p in geometry]))
    outer = unary_union(list(polygonize(unary_union(rings["outer"]))))
    inner = unary_union(list(polygonize(unary_union(rings["inner"]))))
    return make_valid(outer.difference(inner))


def feature(element, geometry, **extra):
    tags = element.get("tags", {})
    ident = f"osm-{element['type']}-{element['id']}"
    name = tags.get("name:en") or tags.get("name") or f"{tags.get('amenity', 'Mapped feature').replace('_', ' ').title()} ({ident})"
    return {"type": "Feature", "geometry": mapping(geometry), "properties": {
        "id": ident, "name": name, "source": f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
        **extra,
    }}


def convert(snapshot, observed_at):
    elements = snapshot["elements"]
    boundary = next(e for e in elements if e["type"] == "relation" and e["id"] == RELATION_ID)
    district = polygon(boundary)
    if district.is_empty or district.area == 0:
        raise ValueError("Sunsari boundary could not be assembled")
    wards = []
    for element in elements:
        if element["type"] == "relation" and element.get("tags", {}).get("admin_level") == "7":
            geometry = polygon(element).intersection(district)
            if not geometry.is_empty and geometry.area > 0:
                wards.append(feature(element, geometry))
    wards.sort(key=lambda f: f["properties"]["id"])
    if not wards:
        wards = [feature(boundary, district)]
    covered = unary_union([shape(f["geometry"]) for f in wards])
    remainder = district.difference(covered)
    if remainder.area > district.area * .001:
        wards.append(feature(boundary, remainder, name="Sunsari: municipal boundary unavailable", derived=True))

    roads, settlements, facilities = [], [], []
    barriers = {"walking": [], "vehicle": []}
    for element in elements:
        tags = element.get("tags", {})
        if element["type"] == "way" and tags.get("highway"):
            coords = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
            nodes = element.get("nodes", [])
            if len(coords) < 2 or len(coords) != len(nodes):
                raise ValueError(f"Incomplete road geometry for way {element['id']}")
            roads.append(feature(element, LineString(coords), tags=tags, node_ids=nodes))
        if element["type"] == "node":
            point = Point(element["lon"], element["lat"])
            if not district.covers(point):
                continue
            if tags.get("place") and (tags.get("name") or tags.get("name:en")):
                settlements.append(feature(element, point))
            if tags.get("barrier"):
                for mode in barriers:
                    specific = tags.get("foot") if mode == "walking" else tags.get("motorcar", tags.get("motor_vehicle", tags.get("vehicle")))
                    access = specific or tags.get("access")
                    physical = tags["barrier"] in ("wall", "fence", "block", "jersey_barrier") or (
                        mode == "vehicle" and tags["barrier"] in ("bollard", "cycle_barrier", "stile", "turnstile", "kissing_gate"))
                    if access in ("no", "private") or (physical and access not in ("yes", "designated", "permissive")):
                        barriers[mode].append(element["id"])
        if tags.get("amenity") in ("school", "community_centre", "hospital", "shelter"):
            if element["type"] == "node":
                point = Point(element["lon"], element["lat"])
            elif element["type"] == "way":
                coords = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
                if len(coords) < 2:
                    continue
                point = LineString(coords).centroid
            else:
                geometry = polygon(element)
                if geometry.is_empty:
                    continue
                point = geometry.representative_point()
            if district.covers(point):
                facilities.append(feature(element, point, amenity=tags["amenity"]))
    if not roads or not settlements or not facilities:
        raise ValueError("Snapshot must contain roads, named places, and candidate facilities")
    roads.sort(key=lambda f: f["properties"]["id"])
    settlements.sort(key=lambda f: f["properties"]["name"])
    facilities.sort(key=lambda f: f["properties"]["id"])
    readings = []
    # Deterministic demo readings; never present these as observations from sensors.
    for index, ward in enumerate(wards):
        if ward["properties"].get("derived"):
            continue
        rain, river, soil = [(10, .15, 20), (70, .6, 55), (110, .9, 75), (170, 1.3, 92)][index % 4]
        readings.append({"ward_id": ward["properties"]["id"], "observed_at": observed_at,
                         "rainfall_mm_24h": rain, "river_level_ratio": river, "soil_moisture_pct": soil})
    sensors = {"provenance": "simulated", "readings": readings}
    west, south, east, north = district.bounds
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()[:20]
    source = {
        "dataset_version": digest, "scenario": "SIMULATED municipal sensor readings; no observed flood extent or safety assessment",
        "manifest": {"source": ENDPOINT, "relation_id": RELATION_ID, "license": "ODbL 1.0",
                     "attribution": "© OpenStreetMap contributors", "retrieved_at": observed_at,
                     "region": "sunsari", "ward_authority": "OSM municipal boundaries, not certified wards",
                     "elevation": "unavailable; no high-ground recommendations", "hazard_provenance": "simulated",
                     "view": {"center": [(west + east) / 2, (south + north) / 2], "zoom": 10}},
        "district": [feature(boundary, district)], "wards": wards, "roads": roads,
        "settlements": settlements, "facilities": facilities, "open_ground": [],
        "coverage": mapping(district), "hazards": {"type": "Polygon", "coordinates": []},
        "closed_road_ids": [], "blocked_node_ids": [], "blocked_nodes_by_mode": barriers,
        "routing": {"max_snap_m": 250, "max_connector_m": 250,
                    "rationale": "Demo graph attachment limit; not an emergency safety threshold"},
    }
    return source, sensors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2] / "sunsari" / "data")
    args = parser.parse_args()
    if args.snapshot:
        snapshot = json.loads(args.snapshot.read_text())
    else:
        request = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode({"data": QUERY}).encode(),
                                         headers={"User-Agent": "SURGE route planner snapshot importer"})
        with urllib.request.urlopen(request, timeout=240) as response:
            snapshot = json.load(response)
    observed = datetime.now(timezone.utc).isoformat()
    source, sensors = convert(snapshot, observed)
    prepared = prepare(source, sensors)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in [("source.json", source), ("sensors.json", sensors), ("prepared.json", prepared)]:
        (args.output / name).write_text(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n")
    print(f"Imported Sunsari: {len(source['roads'])} roads, {len(source['settlements'])} origins, {len(source['wards'])} municipal regions, {len(source['facilities'])} candidate facilities")


if __name__ == "__main__":
    main()
