import test from 'node:test';
import assert from 'node:assert/strict';
import { blockedIds, statusFeatures, roadLabel } from '../road-status.js';

const roads = { type: 'FeatureCollection', features: [
  { type: 'Feature', properties: { id: 'osm-way-1', name: 'Main' }, geometry: null },
  { type: 'Feature', properties: { id: 'osm-way-2' }, geometry: null }
] };

test('blockedIds returns sorted unique road ids', () => {
  assert.deepEqual(blockedIds([{ road_id: 'b', status: 'closed' }, { road_id: 'a', status: 'flooded' }, { road_id: 'b', status: 'closed' }]), ['a', 'b']);
});

test('statusFeatures keeps only roads with a status and tags it', () => {
  const out = statusFeatures(roads, [{ road_id: 'osm-way-2', status: 'flooded' }, { road_id: 'osm-way-9', status: 'closed' }]);
  assert.equal(out.length, 1);
  assert.equal(out[0].properties.status, 'flooded');
  assert.equal(roads.features[1].properties.status, undefined);
});

test('roadLabel falls back to the OSM id when the name is missing', () => {
  assert.equal(roadLabel({ id: 'osm-way-1', name: 'Main' }), 'Main (osm-way-1)');
  assert.equal(roadLabel({ id: 'osm-way-2' }), 'osm-way-2');
});
