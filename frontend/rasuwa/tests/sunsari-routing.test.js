import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { recommend } from '../routing.js';

const data = JSON.parse(await readFile(new URL('../../sunsari/data/prepared.json', import.meta.url), 'utf8'));
const origin = data.map.settlements.features.find(f => f.properties.name === 'Inaruwa').properties.id;
const roads = new Set(data.map.roads.features.map(f => f.properties.id));

for (const mode of ['walking', 'vehicle']) {
  test(`Sunsari ${mode} routes use mapped roads and avoid reported closures`, () => {
    const request = { origin, mode, maxDistance: 20000 };
    const first = recommend(data, request).candidates;
    assert.ok(first.length > 0);
    for (const candidate of first) {
      assert.ok(candidate.route.road_ids.length > 0);
      assert.ok(candidate.route.road_ids.every(id => roads.has(id)));
      assert.ok(candidate.route.geometry.coordinates.every(([lng, lat]) => lng > 86 && lng < 88 && lat > 26 && lat < 28));
    }
    const blocked = first[0].route.road_ids;
    const rerouted = recommend(data, { ...request, blocked }).candidates;
    assert.ok(rerouted.every(c => c.route.road_ids.every(id => !blocked.includes(id))));
    assert.ok(!rerouted.some(c => c.route.road_ids.join() === first[0].route.road_ids.join()));
  });
}

test('Sunsari geography contains the full district network and explicitly simulated regional colors', () => {
  assert.equal(data.manifest.region, 'sunsari');
  assert.equal(data.sensors.provenance, 'simulated');
  assert.ok(roads.size > 10000);
  assert.ok(data.map.settlements.features.length > 100);
  assert.equal(data.map.wards.features.filter(f => !f.properties.derived).length, 12);
  const levels = new Set(data.map.risk_zones.features.map(f => f.properties.sensor_risk_level));
  for (const level of ['Low', 'Moderate', 'High', 'Extreme']) assert.ok(levels.has(level));
});
