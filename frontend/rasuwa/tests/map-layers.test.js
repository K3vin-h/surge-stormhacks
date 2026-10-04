import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

test('map uses regional camera and preserves boundaries without internal coverage dividers', async () => {
  const layers = [];
  let instance;
  class Map {
    constructor(options) { this.options = options; instance = this; }
    addControl() {}
    on() {}
    once(event, callback) { this.load = callback; }
    addSource() {}
    addLayer(layer) { layers.push(layer.id); }
    setFilter() {}
    getSource() { return { setData() {} }; }
    resize() {}
    jumpTo(view) { this.view = view; }
    fitBounds(bounds) { this.bounds = bounds; }
  }
  const source = await readFile(new URL('../map-view.js', import.meta.url), 'utf8');
  const context = vm.createContext({
    maplibre: { Map, setWorkerUrl() {}, NavigationControl: class {}, AttributionControl: class {} },
    ResizeObserver: class { observe() {} }, URL, statusFeatures: () => [],
  });
  vm.runInContext(source.replace(/^import .*;$/gm, '').replace('export function ', 'function ').replaceAll('import.meta.url', "'http://localhost/rasuwa/map-view.js'"), context);
  const data = Object.fromEntries(['district', 'wards', 'settlements', 'facilities', 'open_ground', 'risk_zones', 'roads'].map(k => [k, { type: 'FeatureCollection', features: [] }]));
  data.hazards = { type: 'Polygon', coordinates: [] };
  const api = context.createMap({ dataset: {} }, data, {
    config: { center: [87.2, 26.7], zoom: 10 }, onNotice() {},
  });
  assert.equal(instance.options.center.join(), '87.2,26.7');
  instance.load();
  assert.ok(layers.includes('wards-line'));
  assert.ok(layers.includes('district-line'));
  assert.ok(!layers.includes('risk-outline-halo'));
  assert.ok(!layers.includes('risk-outline'));
  api.overview();
  assert.equal(instance.view.center.join(), '87.2,26.7');
  data.district.features = [{ geometry: { type: 'Polygon', coordinates: [[[87, 26], [87.5, 26], [87.5, 27], [87, 27], [87, 26]]] } }];
  const regional = context.createMap({ dataset: {} }, data, {
    config: { center: [87.2, 26.7], zoom: 10, fitDistrict: true }, onNotice() {},
  });
  assert.equal(JSON.stringify(instance.options.bounds), '[[87,26],[87.5,27]]');
  regional.overview();
  assert.equal(JSON.stringify(instance.bounds), '[[87,26],[87.5,27]]');
});
