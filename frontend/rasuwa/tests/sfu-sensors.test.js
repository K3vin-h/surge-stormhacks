import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { assessRegions, floodedRoadIds } from '../../sfu/sensors.mjs';
import { campusRoute } from '../../sfu/routing.mjs';

const load = async name => JSON.parse(await readFile(new URL(`../../sfu/data/${name}.json`, import.meta.url)));

test('campus sensor readings distinguish risk from the simulated flooded extent', async () => {
  const regions = assessRegions(await load('sensors'));
  assert.deepEqual(regions.map(region => region.risk_level), ['Low', 'High', 'Extreme']);
  assert.deepEqual(regions.map(region => region.simulated_flood), [false, false, true]);
  assert.equal(regions[1].sensor_score, .743);
});

test('missing readings stay Unknown and invalid or duplicate readings are rejected', async () => {
  const data = await load('sensors');
  data.readings = data.readings.slice(1);
  assert.equal(assessRegions(data)[0].risk_level, 'Unknown');
  data.readings[0].soil_moisture_pct = 101;
  assert.throws(() => assessRegions(data), /Invalid soil_moisture_pct/);
  data.readings[0].soil_moisture_pct = 75;
  data.readings.push({ ...data.readings[0] });
  assert.throws(() => assessRegions(data), /Duplicate sensor reading/);
});

test('flood closure detects a crossing with both endpoints outside the region', () => {
  const campus = {
    points: [[-2, 0], [2, 0], [-2, 2], [2, 2]],
    paths: [{ id: 'crossing', nodes: [0, 1] }, { id: 'outside', nodes: [2, 3] }]
  };
  assert.deepEqual(floodedRoadIds(campus, [{ bounds: [-1, -1, 1, 1], simulated_flood: true }]), ['crossing']);
  assert.deepEqual(floodedRoadIds(campus, [{ bounds: [-1, -1, 1, 1], simulated_flood: false }]), []);
});

test('SFU flood avoidance blocks the east campus destination while retaining central routes', async () => {
  const campus = await load('campus');
  const regions = assessRegions(await load('sensors'));
  const blocked = floodedRoadIds(campus, regions);
  assert.ok(blocked.length > 0);
  assert.equal(campusRoute(campus, { from: 'library', to: 'asb', blocked }).status, 'no_route');
  const route = campusRoute(campus, { from: 'library', to: 'aq', blocked });
  assert.equal(route.status, 'ok');
  assert.ok(route.route.road_ids.every(id => !blocked.includes(id)));
  assert.equal(campusRoute(campus, { from: 'library', to: 'asb' }).status, 'ok');
});
