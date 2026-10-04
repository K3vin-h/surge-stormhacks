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
            {"id": "duhabi_secondary", "name": "Duhabi Secondary School",
             "capacity": 800, "location": {"type": "Point", "coordinates": [87.232, 26.655]}},
            {"id": "ramdhuni_hall", "name": "Ramdhuni Community Hall",
             "capacity": 650, "location": {"type": "Point", "coordinates": [87.206, 26.598]}},
            {"id": "jhumka_army_camp", "name": "Jhumka Army Camp Grounds",
             "capacity": 2200, "location": {"type": "Point", "coordinates": [87.240, 26.615]}},
        ],
        "routes": [
            {"id": "east_canal_route", "name": "East Canal Evacuation Route",
             "geometry": {"type": "LineString", "coordinates": [
                 [87.182, 26.627], [87.195, 26.634], [87.201, 26.641]]}},
            {"id": "inaruwa_west_bypass", "name": "Inaruwa West Bypass",
             "geometry": {"type": "LineString", "coordinates": [
                 [87.182, 26.627], [87.168, 26.618], [87.150, 26.606]]}},
            {"id": "duhabi_north_corridor", "name": "Duhabi North Corridor",
             "geometry": {"type": "LineString", "coordinates": [
                 [87.182, 26.627], [87.208, 26.643], [87.232, 26.655]]}},
            {"id": "ramdhuni_south_link", "name": "Ramdhuni South Link",
             "geometry": {"type": "LineString", "coordinates": [
                 [87.182, 26.627], [87.196, 26.611], [87.206, 26.598]]}},
            {"id": "jhumka_highway_east", "name": "Jhumka Highway East",
             "geometry": {"type": "LineString", "coordinates": [
                 [87.182, 26.627], [87.212, 26.622], [87.240, 26.615]]}},
        ],
        "roads": [
            {"id": "mahendra_underpass", "name": "Mahendra Highway Underpass", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [87.170, 26.620]}},
            {"id": "koshi_bridge", "name": "Koshi Barrage Bridge", "status": "open",
             "geometry": {"type": "Point", "coordinates": [87.155, 26.612]}},
            {"id": "sapta_koshi_embankment", "name": "Sapta Koshi Embankment Road", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [87.158, 26.641]}},
            {"id": "inaruwa_bazaar_road", "name": "Inaruwa Bazaar Road", "status": "restricted",
             "geometry": {"type": "Point", "coordinates": [87.146, 26.603]}},
            {"id": "budhi_khola_ford", "name": "Budhi Khola Ford", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [87.214, 26.633]}},
            {"id": "dharan_link_road", "name": "Dharan Link Road", "status": "open",
             "geometry": {"type": "Point", "coordinates": [87.228, 26.666]}},
        ],
        "hospitals": [
            {"id": "koshi_hospital", "name": "Koshi Hospital",
             "location": {"type": "Point", "coordinates": [87.164, 26.633]}},
            {"id": "inaruwa_district_hospital", "name": "Inaruwa District Hospital",
             "location": {"type": "Point", "coordinates": [87.143, 26.611]}},
            {"id": "duhabi_health_post", "name": "Duhabi Health Post",
             "location": {"type": "Point", "coordinates": [87.226, 26.650]}},
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
            {"id": "kanchanpur_campus", "name": "Kanchanpur Campus Hall",
             "capacity": 1100, "location": {"type": "Point", "coordinates": [87.030, 26.640]}},
            {"id": "bhardaha_school", "name": "Bhardaha Secondary School",
             "capacity": 700, "location": {"type": "Point", "coordinates": [86.968, 26.592]}},
            {"id": "shambhunath_temple_grounds", "name": "Shambhunath Temple Grounds",
             "capacity": 1800, "location": {"type": "Point", "coordinates": [87.015, 26.660]}},
        ],
        "routes": [
            {"id": "rajbiraj_ring", "name": "Rajbiraj Ring Road Route",
             "geometry": {"type": "LineString", "coordinates": [
                 [86.998, 26.616], [86.870, 26.575], [86.745, 26.538]]}},
            {"id": "kanchanpur_east_road", "name": "Kanchanpur East Road",
             "geometry": {"type": "LineString", "coordinates": [
                 [86.998, 26.616], [87.014, 26.628], [87.030, 26.640]]}},
            {"id": "bhardaha_canal_path", "name": "Bhardaha Canal Path",
             "geometry": {"type": "LineString", "coordinates": [
                 [86.998, 26.616], [86.984, 26.604], [86.968, 26.592]]}},
            {"id": "shambhunath_highland_route", "name": "Shambhunath Highland Route",
             "geometry": {"type": "LineString", "coordinates": [
                 [86.998, 26.616], [87.006, 26.640], [87.015, 26.660]]}},
        ],
        "roads": [
            {"id": "khado_culvert", "name": "Khado River Culvert", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [86.930, 26.600]}},
            {"id": "koshi_east_embankment", "name": "Koshi East Embankment", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [87.040, 26.610]}},
            {"id": "rajbiraj_market_road", "name": "Rajbiraj Market Road", "status": "restricted",
             "geometry": {"type": "Point", "coordinates": [86.985, 26.622]}},
            {"id": "mahendra_highway_saptari", "name": "Mahendra Highway (Kanchanpur)", "status": "open",
             "geometry": {"type": "Point", "coordinates": [87.022, 26.650]}},
            {"id": "trijuga_bridge", "name": "Trijuga River Bridge", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [86.975, 26.635]}},
        ],
        "hospitals": [
            {"id": "gajendra_hospital", "name": "Gajendra Narayan Singh Hospital",
             "location": {"type": "Point", "coordinates": [86.748, 26.543]}},
            {"id": "kanchanpur_health_centre", "name": "Kanchanpur Primary Health Centre",
             "location": {"type": "Point", "coordinates": [87.026, 26.645]}},
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
            {"id": "rajapur_school", "name": "Rajapur Secondary School",
             "capacity": 950, "location": {"type": "Point", "coordinates": [81.400, 28.330]}},
            {"id": "thakurdwara_hall", "name": "Thakurdwara Community Hall",
             "capacity": 600, "location": {"type": "Point", "coordinates": [81.470, 28.320]}},
            {"id": "bansgadhi_stadium", "name": "Bansgadhi Stadium",
             "capacity": 2000, "location": {"type": "Point", "coordinates": [81.455, 28.270]}},
        ],
        "routes": [
            {"id": "gulariya_route", "name": "Gulariya Highland Route",
             "geometry": {"type": "LineString", "coordinates": [
                 [81.433, 28.300], [81.390, 28.250], [81.345, 28.206]]}},
            {"id": "rajapur_west_road", "name": "Rajapur West Road",
             "geometry": {"type": "LineString", "coordinates": [
                 [81.433, 28.300], [81.418, 28.316], [81.400, 28.330]]}},
            {"id": "thakurdwara_park_road", "name": "Thakurdwara Park Road",
             "geometry": {"type": "LineString", "coordinates": [
                 [81.433, 28.300], [81.452, 28.311], [81.470, 28.320]]}},
            {"id": "bansgadhi_east_link", "name": "Bansgadhi East Link",
             "geometry": {"type": "LineString", "coordinates": [
                 [81.433, 28.300], [81.445, 28.285], [81.455, 28.270]]}},
        ],
        "roads": [
            {"id": "babai_bridge", "name": "Babai River Bridge", "status": "open",
             "geometry": {"type": "Point", "coordinates": [81.410, 28.270]}},
            {"id": "karnali_levee_road", "name": "Karnali Levee Road", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [81.395, 28.315]}},
            {"id": "orahi_khola_crossing", "name": "Orahi Khola Crossing", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [81.442, 28.292]}},
            {"id": "gulariya_bazaar_road", "name": "Gulariya Bazaar Road", "status": "restricted",
             "geometry": {"type": "Point", "coordinates": [81.352, 28.215]}},
        ],
        "hospitals": [
            {"id": "bardiya_hospital", "name": "Bardiya District Hospital",
             "location": {"type": "Point", "coordinates": [81.348, 28.210]}},
            {"id": "rajapur_health_post", "name": "Rajapur Health Post",
             "location": {"type": "Point", "coordinates": [81.405, 28.325]}},
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
            {"id": "maharajgunj_campus", "name": "Maharajgunj Campus Grounds",
             "capacity": 2500, "location": {"type": "Point", "coordinates": [85.330, 27.735]}},
            {"id": "patan_durbar_square", "name": "Patan Durbar Square Shelter",
             "capacity": 1800, "location": {"type": "Point", "coordinates": [85.325, 27.673]}},
            {"id": "bhaktapur_stadium", "name": "Bhaktapur Stadium",
             "capacity": 3200, "location": {"type": "Point", "coordinates": [85.390, 27.676]}},
            {"id": "swayambhu_hill", "name": "Swayambhu Hill Assembly Point",
             "capacity": 1400, "location": {"type": "Point", "coordinates": [85.290, 27.715]}},
        ],
        "routes": [
            {"id": "ring_road_north", "name": "Ring Road North Evacuation",
             "geometry": {"type": "LineString", "coordinates": [
                 [85.324, 27.709], [85.330, 27.730], [85.340, 27.745]]}},
            {"id": "kantipath_route", "name": "Kantipath to Tundikhel",
             "geometry": {"type": "LineString", "coordinates": [
                 [85.324, 27.709], [85.318, 27.705], [85.316, 27.701]]}},
            {"id": "patan_south_route", "name": "Patan South Corridor",
             "geometry": {"type": "LineString", "coordinates": [
                 [85.324, 27.709], [85.328, 27.690], [85.325, 27.673]]}},
            {"id": "araniko_east_route", "name": "Araniko Highway East",
             "geometry": {"type": "LineString", "coordinates": [
                 [85.324, 27.709], [85.355, 27.690], [85.390, 27.676]]}},
            {"id": "swayambhu_west_route", "name": "Swayambhu West Climb",
             "geometry": {"type": "LineString", "coordinates": [
                 [85.324, 27.709], [85.305, 27.712], [85.290, 27.715]]}},
        ],
        "roads": [
            {"id": "bagmati_bridge", "name": "Bagmati Bridge (Thapathali)", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [85.317, 27.693]}},
            {"id": "teku_road", "name": "Teku Riverside Road", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [85.305, 27.695]}},
            {"id": "bishnumati_link", "name": "Bishnumati Link Road", "status": "restricted",
             "geometry": {"type": "Point", "coordinates": [85.298, 27.708]}},
            {"id": "sinamangal_road", "name": "Sinamangal Airport Road", "status": "open",
             "geometry": {"type": "Point", "coordinates": [85.350, 27.698]}},
            {"id": "manohara_bridge", "name": "Manohara Bridge", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [85.365, 27.690]}},
        ],
        "hospitals": [
            {"id": "bir_hospital", "name": "Bir Hospital",
             "location": {"type": "Point", "coordinates": [85.313, 27.704]}},
            {"id": "teaching_hospital", "name": "Tribhuvan University Teaching Hospital",
             "location": {"type": "Point", "coordinates": [85.332, 27.736]}},
            {"id": "patan_hospital", "name": "Patan Hospital",
             "location": {"type": "Point", "coordinates": [85.319, 27.668]}},
        ],
    },
    # SFU Burnaby Mountain campus (Simon Fraser University), Burnaby BC. A
    # SIMULATED mock flood for the live demo: an atmospheric-river flash flood
    # plus landslides on Burnaby Mountain that wash out the access roads and
    # strand people on campus. Coordinates are real SFU/Burnaby locations;
    # the counts and signals are invented for the scenario.
    "sfu": {
        "name": "SFU (Burnaby Mtn)",
        "center": [-122.9199, 49.2781],
        "population": 35_000,
        "distress_calls": 57,
        "injuries": 9,
        "vulnerable_population": 6_000,
        "road_accessibility": 0.40,
        "signals": {
            "rainfall_mm": 305,       # extreme atmospheric river
            "river_level_m": 5.2,     # Stoney/Eagle Creek + stormwater surge proxy
            "elevation_m": 365,       # Burnaby Mountain summit
            "slope_deg": 18.0,        # steep mountain flanks -> landslide risk
            "soil_moisture": 0.95,    # fully saturated
            "forecast_severity": 0.9,
        },
        "shelters": [
            {"id": "lorne_davies_complex", "name": "Lorne Davies Complex (Recreation)",
             "capacity": 2500, "location": {"type": "Point", "coordinates": [-122.9215, 49.2767]}},
            {"id": "sfu_sub", "name": "SFU Student Union Building",
             "capacity": 1500, "location": {"type": "Point", "coordinates": [-122.9178, 49.2788]}},
            {"id": "wac_bennett_library", "name": "W.A.C. Bennett Library",
             "capacity": 1200, "location": {"type": "Point", "coordinates": [-122.9143, 49.2786]}},
            {"id": "convocation_mall", "name": "Convocation Mall (covered)",
             "capacity": 1800, "location": {"type": "Point", "coordinates": [-122.9166, 49.2792]}},
            {"id": "univercity_community_centre", "name": "UniverCity Community Centre",
             "capacity": 900, "location": {"type": "Point", "coordinates": [-122.9120, 49.2797]}},
        ],
        "routes": [
            {"id": "gaglardi_descent", "name": "Gaglardi Way Descent",
             "geometry": {"type": "LineString", "coordinates": [
                 [-122.9199, 49.2781], [-122.9150, 49.2700], [-122.9050, 49.2620]]}},
            {"id": "production_way_trail", "name": "Production Way Station Trail",
             "geometry": {"type": "LineString", "coordinates": [
                 [-122.9199, 49.2781], [-122.9180, 49.2680], [-122.9179, 49.2546]]}},
            {"id": "university_dr_west_exit", "name": "University Drive West Exit",
             "geometry": {"type": "LineString", "coordinates": [
                 [-122.9199, 49.2781], [-122.9280, 49.2760], [-122.9380, 49.2720]]}},
            {"id": "burnaby_mtn_pkwy_north", "name": "Burnaby Mountain Parkway North",
             "geometry": {"type": "LineString", "coordinates": [
                 [-122.9199, 49.2781], [-122.9250, 49.2850], [-122.9350, 49.2900]]}},
            {"id": "curtis_street_link", "name": "Curtis Street Link",
             "geometry": {"type": "LineString", "coordinates": [
                 [-122.9199, 49.2781], [-122.9300, 49.2830], [-122.9450, 49.2830]]}},
        ],
        "roads": [
            {"id": "gaglardi_way", "name": "Gaglardi Way", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [-122.9120, 49.2680]}},
            {"id": "tower_road", "name": "Tower Road (Bus Loop)", "status": "closed",
             "geometry": {"type": "Point", "coordinates": [-122.9220, 49.2780]}},
            {"id": "burnaby_mountain_parkway", "name": "Burnaby Mountain Parkway", "status": "restricted",
             "geometry": {"type": "Point", "coordinates": [-122.9300, 49.2870]}},
            {"id": "south_science_road", "name": "South Science Road", "status": "restricted",
             "geometry": {"type": "Point", "coordinates": [-122.9170, 49.2762]}},
            {"id": "university_drive_east", "name": "University Drive East", "status": "open",
             "geometry": {"type": "Point", "coordinates": [-122.9130, 49.2790]}},
            {"id": "university_high_street", "name": "University High Street", "status": "open",
             "geometry": {"type": "Point", "coordinates": [-122.9120, 49.2800]}},
        ],
        "hospitals": [
            {"id": "burnaby_hospital", "name": "Burnaby Hospital",
             "location": {"type": "Point", "coordinates": [-122.9856, 49.2486]}},
            {"id": "sfu_health_counselling", "name": "SFU Health & Counselling (Maggie Benston)",
             "location": {"type": "Point", "coordinates": [-122.9185, 49.2790]}},
            {"id": "eagle_ridge_hospital", "name": "Eagle Ridge Hospital (Port Moody)",
             "location": {"type": "Point", "coordinates": [-122.8430, 49.2830]}},
        ],
    },
    # Resident routing for Rasuwa uses the client-side road graph, so the
    # catalog is empty. Counts and signals are PLACEHOLDER simulated values,
    # not observations.
    "rasuwa": {
        "placeholder": True,  # no real risk data; callers must not rank or score it
        "name": "Rasuwa",
        "center": [85.46, 28.17],
        "population": 0,
        "distress_calls": 0,
        "injuries": 0,
        "vulnerable_population": 0,
        "road_accessibility": 1.0,
        "signals": {
            "rainfall_mm": 0,
            "river_level_m": 0,
            "elevation_m": 1500,
            "slope_deg": 10.0,
            "soil_moisture": 0.0,
            "forecast_severity": 0.0,
        },
        "shelters": [],
        "routes": [],
        "roads": [],
        "hospitals": [],
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
