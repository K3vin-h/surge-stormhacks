import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { campusRoute } from '../../sfu/routing.mjs';

const load = async () => JSON.parse(await readFile(new URL('../../sfu/data/campus.json', import.meta.url)));

test('SFU routes reach the chosen landmark using connected mapped walking paths', async () => {
  const data = await load();
  for (const from of data.landmarks) {
    for (const to of data.landmarks) {
      if (from.id === to.id) continue;
      const result = campusRoute(data, { from: from.id, to: to.id });
      assert.equal(result.status, 'ok', `${from.name} to ${to.name}`);
      assert.ok(result.route.distance_m > 0);
      assert.ok(result.route.road_ids.length > 0);
      const permitted = new Set(data.paths.flatMap(path => path.nodes.slice(1).flatMap((node, i) => [
        `${data.points[path.nodes[i]].join(',')}|${data.points[node].join(',')}`,
        `${data.points[node].join(',')}|${data.points[path.nodes[i]].join(',')}`
      ])));
      const coords = result.route.geometry.coordinates;
      for (let i = 1; i < coords.length; i++) {
        assert.ok(permitted.has(`${coords[i - 1].join(',')}|${coords[i].join(',')}`), 'Route stays on mapped paths');
      }
    }
  }
});

test('SFU route search handles matching locations, unknown places, and blocked paths', async () => {
  const data = await load();
  const [from, to] = data.landmarks;
  assert.equal(campusRoute(data, { from: from.id, to: from.id }).status, 'same_place');
  assert.throws(() => campusRoute(data, { from: 'unknown', to: to.id }), /Unknown campus location/);
  assert.equal(campusRoute(data, { from: from.id, to: to.id, blocked: data.paths.map(path => path.id) }).status, 'no_route');
});
