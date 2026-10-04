import { test } from 'node:test';
import assert from 'node:assert/strict';
import { planRoute, shouldRecompute, metresBetween } from '../resident-route.js';

const data = {
  dataset_version: 'v1',
  map: { settlements: { features: [] } },
  graphs: {
    walking: {
      nodes: { a: [85, 28], b: [85.001, 28], c: [85.002, 28], d: [85.001, 28.001] },
      edges: {
        a: [['b', 100, 'r-ab'], ['d', 300, 'r-ad']],
        b: [['a', 100, 'r-ab'], ['c', 100, 'r-bc']],
        c: [['b', 100, 'r-bc']],
        d: [['a', 300, 'r-ad']],
      },
      origins: {},
      destinations: [
        { id: 's-near', name: 'Near', kind: 'shelter', targets: ['c'], fallback: null, location: [85.002, 28], source: 'x' },
        { id: 's-far', name: 'Far', kind: 'shelter', targets: ['d'], fallback: null, location: [85.001, 28.001], source: 'x' },
      ],
      exclusions: {},
    },
  },
};
const point = [85, 28];

test('picks the nearest shelter by route distance', () => {
  const r = planRoute(data, { point });
  assert.equal(r.status, 'ok');
  assert.equal(r.destination.shelter_id, 's-near');
  assert.deepEqual(r.changedBecause, []);
});

test('reports why the route changed when a road on the previous route is blocked', () => {
  const prev = planRoute(data, { point });
  const r = planRoute(data, { point, blocked: ['r-bc'], previous: prev });
  assert.equal(r.destination.shelter_id, 's-far');
  assert.deepEqual(r.changedBecause, ['r-bc']);
});

test('ignores blocked roads that were not on the previous route', () => {
  const prev = planRoute(data, { point });
  const r = planRoute(data, { point, blocked: ['r-ad'], previous: prev });
  assert.deepEqual(r.changedBecause, []);
});

test('no_route when every road is blocked, still naming the cause', () => {
  const prev = planRoute(data, { point });
  const r = planRoute(data, { point, blocked: ['r-ab', 'r-ad', 'r-bc'], previous: prev });
  assert.equal(r.status, 'no_route');
  assert.equal(r.route, null);
  assert.deepEqual(r.changedBecause, ['r-ab', 'r-bc']);
});

test('no_location without a fix, too_far when off the road network', () => {
  assert.equal(planRoute(data, { point: null }).status, 'no_location');
  assert.equal(planRoute(data, { point: [90, 10] }).status, 'too_far');
});

test('shouldRecompute only after moving more than 50 m', () => {
  assert.equal(shouldRecompute(null, point), true);
  assert.equal(shouldRecompute(point, null), false);
  assert.equal(shouldRecompute(point, [85.0002, 28]), false);
  assert.equal(shouldRecompute(point, [85.001, 28]), true);
  assert.ok(Math.abs(metresBetween([85, 28], [85.001, 28]) - 98) < 3);
});
