import unittest

try:
    from import_sunsari import convert
except ModuleNotFoundError:
    convert = None


def snapshot():
    ring = [{"lon": x, "lat": y} for x, y in [(87, 26), (87.02, 26), (87.02, 26.02), (87, 26.02), (87, 26)]]
    return {"elements": [
        {"type": "relation", "id": 4589472, "tags": {"name": "Sunsari", "admin_level": "6"},
         "members": [{"type": "way", "role": "outer", "geometry": ring}]},
        {"type": "relation", "id": 10, "tags": {"name:en": "Inaruwa", "admin_level": "7"},
         "members": [{"type": "way", "role": "outer", "geometry": ring}]},
        {"type": "way", "id": 20, "nodes": [1, 2], "tags": {"highway": "residential", "oneway": "yes"},
         "geometry": [{"lon": 87.001, "lat": 26.001}, {"lon": 87.005, "lat": 26.001}]},
        {"type": "way", "id": 21, "nodes": [2, 3], "tags": {"highway": "residential"},
         "geometry": [{"lon": 87.005, "lat": 26.001}, {"lon": 87.009, "lat": 26.001}]},
        {"type": "node", "id": 1, "lon": 87.001, "lat": 26.001, "tags": {"place": "town", "name": "Inaruwa"}},
        {"type": "node", "id": 3, "lon": 87.009, "lat": 26.001, "tags": {"amenity": "school", "name": "School"}},
    ]}


class SunsariImportTests(unittest.TestCase):
    def test_vehicle_graph_includes_highway_link_roads(self):
        from prepare import prepare
        raw = snapshot()
        raw['elements'][3]['tags']['highway'] = 'primary_link'
        source, sensors = convert(raw, '2026-10-04T00:00:00Z')
        self.assertIn('3', prepare(source, sensors)['graphs']['vehicle']['nodes'])

    def test_bollards_allow_walking_but_block_vehicles(self):
        from prepare import prepare
        raw = snapshot()
        raw['elements'].append({'type': 'node', 'id': 2, 'lon': 87.005, 'lat': 26.001,
                                'tags': {'barrier': 'bollard', 'foot': 'yes'}})
        source, sensors = convert(raw, '2026-10-04T00:00:00Z')
        graphs = prepare(source, sensors)['graphs']
        self.assertIn('2', graphs['walking']['nodes'])
        self.assertNotIn('2', graphs['vehicle']['nodes'])

    def test_permitted_gate_does_not_disconnect_routes(self):
        from prepare import prepare
        raw = snapshot()
        raw['elements'].append({'type': 'node', 'id': 2, 'lon': 87.005, 'lat': 26.001,
                                'tags': {'barrier': 'gate', 'access': 'yes'}})
        source, sensors = convert(raw, '2026-10-04T00:00:00Z')
        for graph in prepare(source, sensors)['graphs'].values():
            self.assertIn('2', graph['nodes'])

    def test_boundary_holes_are_preserved(self):
        from import_sunsari import polygon
        from shapely.geometry import Point
        relation = snapshot()['elements'][0]
        relation['members'].append({'type': 'way', 'role': 'inner', 'geometry': [
            {'lon': x, 'lat': y} for x, y in [(87.01, 26.01), (87.015, 26.01),
                                            (87.015, 26.015), (87.01, 26.015), (87.01, 26.01)]]})
        area = polygon(relation)
        self.assertFalse(area.covers(Point(87.012, 26.012)))
        self.assertTrue(area.covers(Point(87.001, 26.001)))

    def test_roads_preserve_shared_node_ids_and_access_tags(self):
        self.assertTrue(callable(convert), "Sunsari OSM importer is missing")
        source, sensors = convert(snapshot(), "2026-10-04T00:00:00Z")
        self.assertEqual(source["roads"][0]["properties"]["node_ids"], [1, 2])
        self.assertEqual(source["roads"][1]["properties"]["node_ids"][0], 2)
        self.assertEqual(source["roads"][0]["properties"]["tags"]["oneway"], "yes")
        self.assertEqual(source["manifest"]["region"], "sunsari")
        self.assertEqual(sensors["provenance"], "simulated")

    def test_preparation_routes_on_the_imported_roads(self):
        self.assertTrue(callable(convert), "Sunsari OSM importer is missing")
        from prepare import prepare
        source, sensors = convert(snapshot(), "2026-10-04T00:00:00Z")
        prepared = prepare(source, sensors)
        graph = prepared["graphs"]["vehicle"]
        self.assertIn("1", graph["nodes"])
        self.assertEqual(graph["edges"]["1"][0][0], "2")
        self.assertFalse(any(edge[0] == "1" for edge in graph["edges"]["2"]))
        self.assertEqual(len(graph["destinations"]), 1)
