import * as maplibre from './vendor/maplibre-gl.mjs';

const collection = features => ({ type: 'FeatureCollection', features });
const empty = collection([]);

export function createMap(element, data, { config, onVillage, onNotice, onCell }) {
  maplibre.setWorkerUrl(new URL('./vendor/maplibre-gl-worker.mjs', import.meta.url).href);
  const hasImagery = !!(config.satelliteTiles && config.satelliteAttribution);
  const map = new maplibre.Map({
    container: element,
    center: [85.35, 28.2], zoom: 11, maxZoom: 18,
    attributionControl: false,
    style: {
      version: 8, glyphs: config.glyphs,
      sources: hasImagery ? { satellite: { type: 'raster', tiles: [config.satelliteTiles], tileSize: 256, maxzoom: 14, attribution: config.satelliteAttribution } } : {},
      layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#233c46' } }, ...(hasImagery ? [{ id: 'satellite', type: 'raster', source: 'satellite' }] : [])]
    }
  });
  let ready = false;
  let pending = { candidates: [], selected: null };
  map.addControl(new maplibre.NavigationControl({ visualizePitch: true }), 'top-right');
  map.addControl(new maplibre.AttributionControl({ compact: true, customAttribution: '© OpenStreetMap contributors' }), 'bottom-right');
  if (!hasImagery) onNotice('Satellite imagery is disabled. Local geographic overlays and routing remain available.');
  map.on('error', () => onNotice('An imagery tile or map label could not load. Local geographic overlays and routing remain available.'));
  const observer = new ResizeObserver(() => map.resize());
  observer.observe(element);

  function update(candidates, selected) {
    pending = { candidates, selected };
    if (!ready) return;
    const put = (id, features) => map.getSource(id).setData(collection(features));
    put('routes', selected ? [{ type: 'Feature', properties: { mode: selected.route.mode }, geometry: selected.route.geometry }] : []);
    put('destinations', (selected ? [selected] : candidates).map(candidate => ({ type: 'Feature', properties: { name: candidate.destination.name }, geometry: candidate.destination.location })));
    if (selected) {
      element.dataset.selectedMode = selected.route.mode;
      const bounds = new maplibre.LngLatBounds();
      for (const c of selected.route.geometry.coordinates) bounds.extend(c);
      map.fitBounds(bounds, { padding: 70, maxZoom: 15, duration: 0 });
    } else {
      delete element.dataset.selectedMode;
    }
  }

  // Style readiness does not depend on remote satellite tiles succeeding.
  map.once('style.load', () => {
    for (const [id, value] of Object.entries({
      district: data.district, wards: data.wards, settlements: data.settlements, facilities: data.facilities,
      'open-ground': data.open_ground, 'risk-zones': data.risk_zones,
      hazards: collection([{ type: 'Feature', properties: {}, geometry: data.hazards }]), routes: empty, destinations: empty
    })) map.addSource(id, { type: 'geojson', data: value });
    const layer = (id, type, source, paint, layout) => map.addLayer({ id, type, source, paint, ...(layout ? { layout } : {}) });
    layer('wards-fill', 'fill', 'wards', { 'fill-color': '#76add5', 'fill-opacity': 0.12 });
    layer('risk-fill', 'fill', 'risk-zones', { 'fill-color': ['match', ['get', 'risk_level'], 'Extreme', '#ef4444', 'High', '#fb923c', 'Moderate', '#facc15', 'Low', '#22c55e', '#94a3b8'], 'fill-opacity': 0.42 });
    layer('hazards-fill', 'fill', 'hazards', { 'fill-color': '#ef4444', 'fill-opacity': 0.85 });
    layer('wards-halo', 'line', 'wards', { 'line-color': '#142b38', 'line-width': 6 });
    layer('wards-line', 'line', 'wards', { 'line-color': '#fff', 'line-width': 3 });
    layer('district-line', 'line', 'district', { 'line-color': '#fff', 'line-width': 4, 'line-dasharray': [3, 2] });
    layer('open-ground-fill', 'fill', 'open-ground', { 'fill-color': '#a78bfa', 'fill-opacity': 0.45 });
    layer('open-ground-line', 'line', 'open-ground', { 'line-color': '#ddd6fe', 'line-width': 2 });
    layer('route-halo', 'line', 'routes', { 'line-color': '#142b38', 'line-width': 9 });
    layer('routes-line', 'line', 'routes', { 'line-color': ['match', ['get', 'mode'], 'walking', '#67e8f9', '#fff'], 'line-width': 5 });
    layer('facilities-points', 'circle', 'facilities', { 'circle-color': '#b3cbd0', 'circle-radius': 4 });
    layer('destinations-points', 'circle', 'destinations', { 'circle-color': '#fff', 'circle-radius': 8, 'circle-stroke-color': '#178267', 'circle-stroke-width': 3 });
    layer('village-points', 'circle', 'settlements', { 'circle-color': '#fff', 'circle-radius': 5, 'circle-stroke-color': '#253d51', 'circle-stroke-width': 2 });
    layer('village-labels', 'symbol', 'settlements', { 'text-color': '#fff', 'text-halo-color': '#203545', 'text-halo-width': 2 }, { 'text-field': ['get', 'name'], 'text-size': 12, 'text-offset': [0, 1.2], 'text-anchor': 'top' });
    map.on('click', 'village-points', event => {
      const id = event.features?.[0]?.properties?.id;
      if (typeof id === 'string') onVillage(id);
    });
    map.on('click', 'risk-fill', event => {
      const p = event.features?.[0]?.properties;
      if (p) onCell(`${p.ward_name}: ${p.risk_level} risk (simulated)`);
    });
    map.on('mouseenter', 'village-points', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'village-points', () => { map.getCanvas().style.cursor = ''; });
    ready = true;
    map.resize();
    update(pending.candidates, pending.selected);
    element.dataset.mapReady = 'true';
  });
  return {
    update,
    overview: () => map.jumpTo({ center: [85.35, 28.2], zoom: 11, pitch: 0, bearing: 0 }),
    destroy: () => { observer.disconnect(); map.remove(); }
  };
}
