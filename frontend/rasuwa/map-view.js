import * as maplibre from './vendor/maplibre-gl.mjs';
import { statusFeatures } from './road-status.js';

const collection = features => ({ type: 'FeatureCollection', features });
const empty = collection([]);

export function createMap(element, data, { config, onVillage, onNotice, onCell, onRoad }) {
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
  let picking = false, pendingRoads = [], pendingSelected = null;
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

  function setRoadStatus(roads) {
    pendingRoads = roads;
    if (ready) map.getSource('road-status').setData(collection(statusFeatures(data.roads, roads)));
  }
  function selectRoad(id) {
    pendingSelected = id;
    if (ready) map.getSource('road-selected').setData(collection(id ? data.roads.features.filter(feature => feature.properties.id === id) : []));
  }

  // Style readiness does not depend on remote satellite tiles succeeding.
  map.once('style.load', () => {
    for (const [id, value] of Object.entries({
      district: data.district, wards: data.wards, settlements: data.settlements, facilities: data.facilities,
      'open-ground': data.open_ground, 'risk-zones': data.risk_zones, roads: data.roads,
      hazards: collection([{ type: 'Feature', properties: {}, geometry: data.hazards }]), routes: empty, destinations: empty, 'road-status': empty, 'road-selected': empty
    })) map.addSource(id, { type: 'geojson', data: value });
    const layer = (id, type, source, paint, layout) => map.addLayer({ id, type, source, paint, ...(layout ? { layout } : {}) });
    layer('district-fill', 'fill', 'district', { 'fill-color': '#64748b', 'fill-opacity': 0.45 });
    layer('wards-fill', 'fill', 'wards', { 'fill-color': '#94a3b8', 'fill-opacity': 0.5 });
    const levelColor = level => ['match', level, 'Extreme', '#dc2626', 'High', '#f97316', 'Moderate', '#facc15', 'Low', '#22c55e', '#94a3b8'];
    // Outside the hazard-proximity analysis a ward is colored by its own sensor reading (lighter fill);
    // it stays gray only when the ward has no reading.
    const sensorOnly = ['==', ['get', 'risk_level'], 'Unknown'];
    const riskColor = ['case', sensorOnly, levelColor(['get', 'sensor_risk_level']), levelColor(['get', 'risk_level'])];
    layer('risk-fill', 'fill', 'risk-zones', { 'fill-color': riskColor, 'fill-opacity': ['case', sensorOnly, 0.4, 0.68] });
    layer('risk-outline-halo', 'line', 'risk-zones', { 'line-color': '#0f172a', 'line-width': 3 });
    layer('risk-outline', 'line', 'risk-zones', { 'line-color': riskColor, 'line-width': 1.5, 'line-opacity': ['case', sensorOnly, 0.5, 1] });
    layer('hazards-fill', 'fill', 'hazards', { 'fill-color': '#ef4444', 'fill-opacity': 0.85 });
    layer('wards-halo', 'line', 'wards', { 'line-color': '#142b38', 'line-width': 6 });
    layer('wards-line', 'line', 'wards', { 'line-color': '#fff', 'line-width': 3 });
    layer('district-line', 'line', 'district', { 'line-color': '#fff', 'line-width': 4, 'line-dasharray': [3, 2] });
    layer('open-ground-fill', 'fill', 'open-ground', { 'fill-color': '#a78bfa', 'fill-opacity': 0.45 });
    layer('open-ground-line', 'line', 'open-ground', { 'line-color': '#ddd6fe', 'line-width': 2 });
    layer('roads-halo', 'line', 'roads', { 'line-color': '#0f172a', 'line-width': ['interpolate', ['linear'], ['zoom'], 9, 2, 15, 7] });
    layer('roads-line', 'line', 'roads', { 'line-color': '#f8fafc', 'line-width': ['interpolate', ['linear'], ['zoom'], 9, 0.7, 15, 3] });
    layer('paths-line', 'line', 'roads', { 'line-color': '#fbbf24', 'line-width': 2, 'line-dasharray': [2, 2] });
    map.setFilter('paths-line', ['in', ['get', 'highway'], ['literal', ['path', 'footway', 'steps', 'track']]]);
    layer('closed-roads', 'line', 'roads', { 'line-color': '#f43f5e', 'line-width': 4, 'line-dasharray': [2, 1] });
    map.setFilter('closed-roads', ['==', ['get', 'closed'], true]);
    // Government road status: red long dashes = closed, blue short dashes = flooded (shape differs, not only colour).
    layer('road-status-halo', 'line', 'road-status', { 'line-color': '#0f172a', 'line-width': 8 });
    layer('road-status-closed', 'line', 'road-status', { 'line-color': '#dc2626', 'line-width': 5, 'line-dasharray': [4, 1.5] });
    layer('road-status-flooded', 'line', 'road-status', { 'line-color': '#2563eb', 'line-width': 5, 'line-dasharray': [1, 1] });
    map.setFilter('road-status-closed', ['==', ['get', 'status'], 'closed']);
    map.setFilter('road-status-flooded', ['==', ['get', 'status'], 'flooded']);
    layer('road-selected', 'line', 'road-selected', { 'line-color': '#fde047', 'line-width': 11, 'line-opacity': 0.75 });
    // Wide transparent hit area so thin roads are clickable.
    layer('roads-hit', 'line', 'roads', { 'line-color': '#000', 'line-opacity': 0, 'line-width': 18 });
    layer('route-halo', 'line', 'routes', { 'line-color': '#142b38', 'line-width': 9 });
    layer('routes-line', 'line', 'routes', { 'line-color': ['match', ['get', 'mode'], 'walking', '#67e8f9', '#c4b5fd'], 'line-width': 5 });
    layer('facilities-points', 'circle', 'facilities', { 'circle-color': '#b3cbd0', 'circle-radius': 4 });
    layer('destinations-points', 'circle', 'destinations', { 'circle-color': '#fff', 'circle-radius': 8, 'circle-stroke-color': '#178267', 'circle-stroke-width': 3 });
    layer('village-points', 'circle', 'settlements', { 'circle-color': '#fff', 'circle-radius': 5, 'circle-stroke-color': '#253d51', 'circle-stroke-width': 2 });
    layer('village-labels', 'symbol', 'settlements', { 'text-color': '#fff', 'text-halo-color': '#203545', 'text-halo-width': 2 }, { 'text-field': ['get', 'name'], 'text-size': 12, 'text-offset': [0, 1.2], 'text-anchor': 'top' });
    layer('ward-labels', 'symbol', 'wards', { 'text-color': '#fff', 'text-halo-color': '#0f172a', 'text-halo-width': 2 }, { 'text-field': ['get', 'name'], 'text-size': 14 });
    map.on('click', 'village-points', event => {
      const id = event.features?.[0]?.properties?.id;
      if (typeof id === 'string') onVillage(id);
    });
    map.on('click', 'risk-fill', event => {
      const p = event.features?.[0]?.properties;
      if (p) onCell(`${p.ward_name}: ${p.risk_level === 'Unknown' && p.sensor_risk_level ? `${p.sensor_risk_level} risk (ward sensor reading only, outside the hazard analysis)` : `${p.risk_level} risk`} · ${p.provenance}. ${p.observed_at ? `Rain ${p.rainfall_mm_24h} mm/24h · river/warning ${p.river_level_ratio} · soil ${p.soil_moisture_pct}% · observed ${p.observed_at}` : 'No sensor assessment available.'}`);
    });
    map.on('click', 'roads-hit', event => {
      if (map.queryRenderedFeatures(event.point, { layers: ['village-points'] }).length) return; // village click wins
      const properties = event.features?.[0]?.properties;
      if (picking && typeof properties?.id === 'string') onRoad(properties);
    });
    map.on('mouseenter', 'roads-hit', () => { if (picking) map.getCanvas().style.cursor = 'crosshair'; });
    map.on('mouseleave', 'roads-hit', () => { map.getCanvas().style.cursor = ''; });
    map.on('mouseenter', 'village-points', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'village-points', () => { map.getCanvas().style.cursor = ''; });
    ready = true;
    setRoadStatus(pendingRoads);
    selectRoad(pendingSelected);
    map.resize();
    update(pending.candidates, pending.selected);
    element.dataset.mapReady = 'true';
  });
  return {
    update, setRoadStatus, selectRoad,
    setPicking: value => { picking = value; },
    overview: () => map.jumpTo({ center: [85.35, 28.2], zoom: 11, pitch: 0, bearing: 0 }),
    destroy: () => { observer.disconnect(); map.remove(); }
  };
}
