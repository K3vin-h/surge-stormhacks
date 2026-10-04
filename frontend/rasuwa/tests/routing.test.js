import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const load = async () => import('../routing.js');
const fixture = {
  dataset_version: 'test-v1',
  map: { settlements: { features: [{ properties: { id: 'village', name: 'Village' } }] } },
  graphs: {
    walking: {
      nodes: { a: [85, 28], b: [85.001, 28], c: [85.002, 28] },
      edges: { a: [['c', 500, 'long-road'], ['b', 100, 'path']], b: [['c', 150, 'path']], c: [] },
      origins: { village: 'a' },
      destinations: [{ id: 'grass', name: 'Grass plot', kind: 'open_ground', source: 'https://www.openstreetmap.org/way/1', targets: ['c'], fallback: 'c', location: [85.002, 28] }],
      exclusions: { flooded: 'Inside flood scenario' }
    },
    vehicle: { nodes: { a: [85, 28], c: [85.002, 28] }, edges: { a: [], c: [['a', 200, 'oneway']] }, origins: { village: 'a' }, destinations: [{ id: 'grass', name: 'Grass plot', kind: 'open_ground', targets: ['c'], fallback: 'c', location: [85.002, 28] }], exclusions: {} }
  }
};

test('finds shortest mapped path and removes destinations beyond the official limit', async () => {
  const { recommend } = await load();
  const result = recommend(fixture, { origin: 'village', mode: 'walking', maxDistance: 250, version: 'test-v1' });
  assert.equal(result.candidates.length, 1);
  assert.equal(result.candidates[0].route.distance_m, 250);
  assert.deepEqual(result.candidates[0].route.geometry.coordinates, [[85, 28], [85.001, 28], [85.002, 28]]);
  assert.equal(result.candidates[0].destination.destination_kind, 'open_ground');
  assert.ok(result.candidates[0].unknowns.some(s => s.includes('Permission')));
  assert.equal(recommend(fixture, { origin: 'village', mode: 'walking', maxDistance: 249 }).candidates.length, 0);
});

test('vehicle routing respects directed edges and never invents a connector', async () => {
  const { recommend } = await load();
  assert.equal(recommend(fixture, { origin: 'village', mode: 'vehicle', maxDistance: 1000 }).candidates.length, 0);
});

test('rejects invalid limits, unknown villages, modes and stale dataset versions', async () => {
  const { recommend } = await load();
  for (const maxDistance of [0, -1, NaN, Infinity, 50001, '', '250']) {
    assert.throws(() => recommend(fixture, { origin: 'village', mode: 'walking', maxDistance }), /distance/i);
  }
  assert.throws(() => recommend(fixture, { origin: 'missing', mode: 'walking', maxDistance: 500 }), /village/i);
  assert.throws(() => recommend(fixture, { origin: 'village', mode: 'plane', maxDistance: 500 }), /mode/i);
  assert.throws(() => recommend(fixture, { origin: 'village', mode: 'walking', maxDistance: 500, version: 'stale' }), /changed/i);
});

test('uses an interior ground node when reachable and falls back only when no interior node is reachable', async () => {
  const { recommend } = await load();
  const data = structuredClone(fixture);
  data.graphs.walking.destinations[0].targets = ['missing'];
  assert.equal(recommend(data, { origin: 'village', mode: 'walking', maxDistance: 500 }).candidates[0].route.distance_m, 250);
  data.graphs.walking.destinations[0].targets = ['b', 'c'];
  assert.equal(recommend(data, { origin: 'village', mode: 'walking', maxDistance: 500 }).candidates[0].route.distance_m, 100);
});

test('real migrated geography returns the nearby plot and removes it below 100 m', async () => {
  const { recommend } = await load();
  const data = JSON.parse(await readFile(new URL('../data/prepared.json', import.meta.url)));
  const origin = data.map.settlements.features.find(f => f.properties.name === 'National Rainbow Trout Research Station, Dhunche').properties.id;
  const result = recommend(data, { origin, mode: 'walking', maxDistance: 500 });
  const plot = result.candidates.find(c => c.destination.name === 'Pasture demonstration plots');
  assert.ok(plot);
  assert.equal(plot.route.distance_m, 334.9);
  assert.equal(recommend(data, { origin, mode: 'walking', maxDistance: 100 }).candidates.length, 0);
  assert.deepEqual(new Set(data.map.risk_zones.features.map(f => f.properties.risk_level)), new Set(['Extreme', 'High', 'Moderate', 'Low']));
});

test('all 28 village origins in both travel modes match the original model reference', async () => {
  const { recommend } = await load();
  const data = JSON.parse(await readFile(new URL('../data/prepared.json', import.meta.url)));
  const reference = JSON.parse(await readFile(new URL('./source-reference.json', import.meta.url)));
  for (const sample of reference.cases) {
    const result = recommend(data, { origin: sample.origin, mode: sample.mode, maxDistance: 50000 });
    assert.deepEqual(result.candidates.map(c => ({ id: c.destination.shelter_id, distance: c.route.distance_m, roads: c.route.road_ids })), sample.candidates, `${sample.origin} ${sample.mode}`);
    for (const candidate of result.candidates) {
      const graph = data.graphs[sample.mode];
      const nodes = new Map(Object.entries(graph.nodes).map(([id, coord]) => [coord.join(','), id]));
      const coordinates = candidate.route.geometry.coordinates;
      for (let i = 1; i < coordinates.length; i++) {
        const previous = nodes.get(coordinates[i - 1].join(','));
        const next = nodes.get(coordinates[i].join(','));
        assert.ok(graph.edges[previous].some(edge => edge[0] === next), 'Route must only follow a permitted directed graph edge');
      }
    }
  }
});
