"""Exercise the migrated preparation code without importing either backend."""
import copy
import hashlib
import json
import unittest

from shapely.geometry import shape

from prepare import ROOT, prepare


def polygon(west, south, east, north):
    return {"type": "Polygon", "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]]}


def feature(id, geometry, **properties):
    return {"type": "Feature", "geometry": geometry, "properties": {"id": id, "name": id, "source": "https://www.openstreetmap.org/way/1", **properties}}


def fixture():
    coverage = polygon(85, 28, 85.02, 28.02)
    return {
        "dataset_version": "fixture", "scenario": "SIMULATED", "manifest": {"hazard_provenance": "simulated"},
        "coverage": coverage, "hazards": polygon(85.016, 28.016, 85.019, 28.019),
        "district": [], "wards": [feature("ward", coverage)],
        "settlements": [feature("village", {"type": "Point", "coordinates": [85.001, 28.001]})],
        "facilities": [feature("school", {"type": "Point", "coordinates": [85.005, 28.001]})],
        "open_ground": [feature("grass", polygon(85.004, 28.0005, 85.006, 28.0015))],
        "roads": [feature("road", {"type": "LineString", "coordinates": [[85.001, 28.001], [85.005, 28.001]]},
                          node_ids=[1, 2], tags={"highway": "residential", "oneway": "yes"})],
        "closed_road_ids": [], "blocked_node_ids": [], "routing": {"max_snap_m": 250}
    }


class PreparationTests(unittest.TestCase):
    def test_bundled_snapshot_matches_self_contained_preparation(self):
        source = json.loads((ROOT / "data/source.json").read_text())
        bundled = json.loads((ROOT / "data/prepared.json").read_text())
        digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest(prepare(source)), digest(bundled), "Bundled data needs regeneration")

    def test_modes_preserve_vehicle_oneway_and_walking_bidirectional_edges(self):
        result = prepare(fixture())
        self.assertEqual(result["graphs"]["vehicle"]["edges"]["1"][0][0], "2")
        self.assertNotIn("2", result["graphs"]["vehicle"]["edges"])
        self.assertEqual(result["graphs"]["walking"]["edges"]["2"][0][0], "1")

    def test_access_permissions_can_allow_walking_but_exclude_vehicles(self):
        data = fixture()
        data["roads"][0]["properties"]["tags"].update(access="private", foot="yes")
        result = prepare(data)
        self.assertTrue(result["graphs"]["walking"]["nodes"])
        self.assertFalse(result["graphs"]["vehicle"]["nodes"])

    def test_closed_roads_and_blocked_nodes_never_enter_graph(self):
        for key, value in [("closed_road_ids", ["road"]), ("blocked_node_ids", [2])]:
            with self.subTest(key=key):
                data = fixture()
                data[key] = value
                result = prepare(data)
                self.assertFalse(result["graphs"]["walking"]["nodes"])
                self.assertFalse(result["graphs"]["vehicle"]["nodes"])

    def test_motorcar_permissions_override_general_motor_vehicle_prohibition(self):
        for permission in ("yes", "designated", "permissive"):
            with self.subTest(permission=permission):
                data = fixture()
                data["roads"][0]["properties"]["tags"].update(motor_vehicle="no", motorcar=permission)
                self.assertTrue(prepare(data)["graphs"]["vehicle"]["nodes"])
        data = fixture()
        data["roads"][0]["properties"]["tags"]["motor_vehicle"] = "no"
        self.assertFalse(prepare(data)["graphs"]["vehicle"]["nodes"])

    def test_hazard_crossing_edges_are_removed(self):
        data = fixture()
        data["hazards"] = polygon(85.003, 28.0005, 85.004, 28.0015)
        self.assertFalse(prepare(data)["graphs"]["walking"]["edges"])

    def test_ground_candidates_need_entire_assessed_low_risk_polygon(self):
        data = fixture()
        data["open_ground"] += [feature("flooded", polygon(85.016, 28.016, 85.017, 28.017)),
                                feature("outside", polygon(84.99, 28.001, 85.001, 28.002))]
        result = prepare(data)
        graph = result["graphs"]["walking"]
        self.assertEqual([d["id"] for d in graph["destinations"] if d["kind"] == "open_ground"], ["grass"])
        self.assertEqual(next(d for d in graph["destinations"] if d["id"] == "grass")["targets"], ["2"])
        self.assertIn("flooded", graph["exclusions"])
        self.assertIn("outside", graph["exclusions"])

    def test_outside_origin_has_no_graph_attachment(self):
        data = fixture()
        data["settlements"][0]["geometry"]["coordinates"] = [84.99, 28]
        self.assertIsNone(prepare(data)["graphs"]["walking"]["origins"]["village"])

    def test_four_risk_bands_remain_inside_assessed_coverage(self):
        data = fixture()
        features = prepare(data)["map"]["risk_zones"]["features"]
        self.assertEqual({f["properties"]["risk_level"] for f in features}, {"Extreme", "High", "Moderate", "Low"})
        self.assertTrue(all(shape(data["coverage"]).buffer(1e-7).covers(shape(f["geometry"])) for f in features))

    def test_changed_scenario_changes_prepared_version_without_mutating_input(self):
        data = fixture()
        original = copy.deepcopy(data)
        before = prepare(data)
        self.assertEqual(data, original)
        data["closed_road_ids"] = ["road"]
        after = prepare(data)
        self.assertNotEqual(before["dataset_version"], after["dataset_version"])


if __name__ == "__main__":
    unittest.main()
