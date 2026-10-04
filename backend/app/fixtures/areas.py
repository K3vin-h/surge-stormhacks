"""Static per-area catalog for the four demo areas (Nepal flood scenario).

These are reference facts (geometry, shelters, routes, roads, hospitals, and
baseline signals). Published instructions and community reports are durable
and live in Snowflake; this catalog does not.
"""
from __future__ import annotations

from typing import Any


def _poly(lng: float, lat: float, d: float = 0.08) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[
            [lng - d, lat - d],
            [lng + d, lat - d],
            [lng + d, lat + d],
            [lng - d, lat + d],
            [lng - d, lat - d],
        ]],
    }


AREAS: dict[str, dict[str, Any]] = {
    "sunsari": {
        "name": "Sunsari",
        "center": [87.182, 26.627],
        "population": 926_000,
        "distress_calls": 48,
        "injuries": 12,
        "vulnerable_population": 180_000,
        "road_accessibility": 0.55,
        "signals": {
            "rainfall_mm": 210,
            "river_level_m": 6.4,
            "elevation_m": 120,
            "slope_deg": 2.0,
            "soil_moisture": 0.88,
            "forecast_severity": 0.8,
        },
        "shelters": [
            {"id": "koshi_community_school", "name": "Koshi Community School",
             "capacity": 1200, "location": {"type": "Point", "coordinates": [87.201, 26.641]}},
            {"id": "inaruwa_stadium", "name": "Inaruwa Stadium",
             "capacity": 3000, "location": {"type": "Point", "coordinates": [87.150, 26.606]}},
        ],
        "routes": [
            {"id": "east_canal_route", "name": "East Canal Evacuation Route",
             "geometry": {"type": "LineString", "coordinates": [
                 [87.182, 26.627], [87.195, 26.634], [87.201, 26.641]]}},
        ],
        "roads": [
            {"id": "mahendra_underpass", "name": "Mahendra Highway Underpass", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [87.170, 26.620]}},
            {"id": "koshi_bridge", "name": "Koshi Barrage Bridge", "status": "open",
             "geometry": {"type": "Point", "coordinates": [87.155, 26.612]}},
        ],
        "hospitals": [
            {"id": "koshi_hospital", "name": "Koshi Hospital",
             "location": {"type": "Point", "coordinates": [87.164, 26.633]}},
        ],
    },
    "saptari": {
        "name": "Saptari",
        "center": [86.998, 26.616],
        "population": 639_000,
        "distress_calls": 33,
        "injuries": 7,
        "vulnerable_population": 140_000,
        "road_accessibility": 0.62,
        "signals": {
            "rainfall_mm": 165,
            "river_level_m": 5.1,
            "elevation_m": 95,
            "slope_deg": 1.5,
            "soil_moisture": 0.79,
            "forecast_severity": 0.6,
        },
        "shelters": [
            {"id": "rajbiraj_highschool", "name": "Rajbiraj High School",
             "capacity": 900, "location": {"type": "Point", "coordinates": [86.745, 26.538]}},
        ],
        "routes": [
            {"id": "rajbiraj_ring", "name": "Rajbiraj Ring Road Route",
             "geometry": {"type": "LineString", "coordinates": [
                 [86.998, 26.616], [86.870, 26.575], [86.745, 26.538]]}},
        ],
        "roads": [
            {"id": "khado_culvert", "name": "Khado River Culvert", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [86.930, 26.600]}},
        ],
        "hospitals": [
            {"id": "gajendra_hospital", "name": "Gajendra Narayan Singh Hospital",
             "location": {"type": "Point", "coordinates": [86.748, 26.543]}},
        ],
    },
    "bardiya": {
        "name": "Bardiya",
        "center": [81.433, 28.300],
        "population": 460_000,
        "distress_calls": 21,
        "injuries": 4,
        "vulnerable_population": 90_000,
        "road_accessibility": 0.71,
        "signals": {
            "rainfall_mm": 140,
            "river_level_m": 4.3,
            "elevation_m": 150,
            "slope_deg": 2.5,
            "soil_moisture": 0.70,
            "forecast_severity": 0.5,
        },
        "shelters": [
            {"id": "gulariya_campus", "name": "Gulariya Multiple Campus",
             "capacity": 1500, "location": {"type": "Point", "coordinates": [81.345, 28.206]}},
        ],
        "routes": [
            {"id": "gulariya_route", "name": "Gulariya Highland Route",
             "geometry": {"type": "LineString", "coordinates": [
                 [81.433, 28.300], [81.390, 28.250], [81.345, 28.206]]}},
        ],
        "roads": [
            {"id": "babai_bridge", "name": "Babai River Bridge", "status": "open",
             "geometry": {"type": "Point", "coordinates": [81.410, 28.270]}},
        ],
        "hospitals": [
            {"id": "bardiya_hospital", "name": "Bardiya District Hospital",
             "location": {"type": "Point", "coordinates": [81.348, 28.210]}},
        ],
    },
    "kathmandu_valley": {
        "name": "Kathmandu Valley",
        "center": [85.324, 27.709],
        "population": 2_900_000,
        "distress_calls": 64,
        "injuries": 19,
        "vulnerable_population": 420_000,
        "road_accessibility": 0.48,
        "signals": {
            "rainfall_mm": 180,
            "river_level_m": 3.9,
            "elevation_m": 1400,
            "slope_deg": 6.0,
            "soil_moisture": 0.82,
            "forecast_severity": 0.7,
        },
        "shelters": [
            {"id": "tudikhel_ground", "name": "Tundikhel Open Ground",
             "capacity": 5000, "location": {"type": "Point", "coordinates": [85.316, 27.701]}},
        ],
        "routes": [
            {"id": "ring_road_north", "name": "Ring Road North Evacuation",
             "geometry": {"type": "LineString", "coordinates": [
                 [85.324, 27.709], [85.330, 27.730], [85.340, 27.745]]}},
        ],
        "roads": [
            {"id": "bagmati_bridge", "name": "Bagmati Bridge (Thapathali)", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [85.317, 27.693]}},
        ],
        "hospitals": [
            {"id": "bir_hospital", "name": "Bir Hospital",
             "location": {"type": "Point", "coordinates": [85.313, 27.704]}},
        ],
    },
}


def get_area(area_id: str) -> dict[str, Any] | None:
    return AREAS.get(area_id)


def geometry_for(area_id: str) -> dict[str, Any] | None:
    a = AREAS.get(area_id)
    if not a:
        return None
    lng, lat = a["center"]
    return _poly(lng, lat)


def shelter_by_id(area_id: str, shelter_id: str) -> dict[str, Any] | None:
    a = AREAS.get(area_id) or {}
    return next((s for s in a.get("shelters", []) if s["id"] == shelter_id), None)


def route_by_id(area_id: str, route_id: str) -> dict[str, Any] | None:
    a = AREAS.get(area_id) or {}
    return next((r for r in a.get("routes", []) if r["id"] == route_id), None)


def road_by_id(area_id: str, road_id: str) -> dict[str, Any] | None:
    a = AREAS.get(area_id) or {}
    return next((r for r in a.get("roads", []) if r["id"] == road_id), None)
