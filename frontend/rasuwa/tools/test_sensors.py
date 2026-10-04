import unittest

from shapely.geometry import shape
from shapely.ops import unary_union

from prepare import prepare
from test_prepare import fixture


class SensorTests(unittest.TestCase):
    def readings(self, rain=10, river=0.2, moisture=20):
        return {"provenance": "simulated", "readings": [{
            "ward_id": "ward", "observed_at": "2026-10-03T12:00:00Z",
            "rainfall_mm_24h": rain, "river_level_ratio": river,
            "soil_moisture_pct": moisture}]}

    def test_sensor_change_changes_risk_and_version(self):
        low = prepare(fixture(), self.readings())
        high = prepare(fixture(), self.readings(200, 1.4, 100))
        self.assertNotEqual(low["dataset_version"], high["dataset_version"])
        self.assertEqual({f["properties"]["risk_level"] for f in high["map"]["risk_zones"]["features"]}, {"Extreme"})
        self.assertFalse(high["graphs"]["walking"]["destinations"])

    def test_missing_sensor_covers_whole_ward_as_unknown(self):
        data = fixture()
        result = prepare(data, {"provenance": "simulated", "readings": []})
        zones = result["map"]["risk_zones"]["features"]
        self.assertEqual({f["properties"]["risk_level"] for f in zones}, {"Unknown"})
        self.assertTrue(unary_union([shape(f["geometry"]) for f in zones]).equals(shape(data["wards"][0]["geometry"])))
        self.assertFalse(result["graphs"]["walking"]["destinations"])

    def test_invalid_and_duplicate_sensor_values_are_rejected(self):
        for field, value in [("rainfall_mm_24h", -1), ("river_level_ratio", float("nan")), ("soil_moisture_pct", 101)]:
            sensors = self.readings()
            sensors["readings"][0][field] = value
            with self.assertRaises(ValueError):
                prepare(fixture(), sensors)
        sensors = self.readings()
        sensors["readings"] *= 2
        with self.assertRaises(ValueError):
            prepare(fixture(), sensors)


if __name__ == "__main__":
    unittest.main()
