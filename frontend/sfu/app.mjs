import * as maplibre from '../rasuwa/vendor/maplibre-gl.mjs';
import { campusRoute } from './routing.mjs';

const element = id => document.getElementById(id);
const collection = features => ({ type: 'FeatureCollection', features });
const empty = collection([]);
const start = element('start');
const destination = element('destination');
let data, map, mapReady = false, route = null;
const markers = [];

if (new URLSearchParams(location.search).get('embed') === '1') document.body.classList.add('embedded');

function notice(message) {
  element('map-notice').textContent = message;
  element('map-notice').hidden = false;
}

function overview() {
  map?.fitBounds(data.bounds, { padding: 45, duration: 0 });
}

function drawRoute() {
  if (!mapReady) return;
  map.getSource('route').setData(collection(route ? [{ type: 'Feature', properties: {}, geometry: route.geometry }] : []));
  element('map').dataset.routeReady = String(!!route);
  if (route) {
    const bounds = new maplibre.LngLatBounds();
    for (const point of route.geometry.coordinates) bounds.extend(point);
    for (const place of data.landmarks) {
      if (place.id === start.value || place.id === destination.value) bounds.extend(place.coordinates);
    }
    map.fitBounds(bounds, { padding: { top: 55, bottom: 85, left: 65, right: 65 }, maxZoom: 17.5, duration: 0 });
  }
}

function update() {
  const result = campusRoute(data, { from: start.value, to: destination.value });
  const from = data.landmarks.find(place => place.id === start.value);
  const to = data.landmarks.find(place => place.id === destination.value);
  route = result.route;
  element('route-distance').textContent = route ? `${Math.round(route.distance_m)} m` : '';
  element('route-summary').textContent = result.status === 'same_place'
    ? `You're already at ${to.name}.`
    : result.status === 'nearby' ? 'These places share a nearby mapped access point.'
    : route ? `${from.name} → ${to.name}` : 'No mapped walking route connects these locations.';
  for (const { place, button } of markers) {
    button.classList.toggle('is-start', place.id === start.value);
    button.classList.toggle('is-destination', place.id === destination.value);
  }
  drawRoute();
}

function createMap() {
  maplibre.setWorkerUrl(new URL('../rasuwa/vendor/maplibre-gl-worker.mjs', import.meta.url).href);
  map = new maplibre.Map({
    container: 'map', bounds: data.bounds, fitBoundsOptions: { padding: 40 }, maxZoom: 19,
    style: {
      version: 8,
      sources: { basemap: {
        type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
      } },
      layers: [
        { id: 'background', type: 'background', paint: { 'background-color': '#e8ede3' } },
        { id: 'basemap', type: 'raster', source: 'basemap', paint: { 'raster-opacity': .7 } }
      ]
    }
  });
  map.addControl(new maplibre.NavigationControl({ showCompass: false }), 'top-right');
  map.on('error', () => notice('Background map tiles could not load. Campus paths and route search are still available.'));
  const observer = new ResizeObserver(() => map.resize());
  observer.observe(element('map'));
  map.on('style.load', () => {
    map.addSource('paths', { type: 'geojson', data: collection(data.paths.map(path => ({
      type: 'Feature', properties: {},
      geometry: { type: 'LineString', coordinates: path.nodes.map(node => data.points[node]) }
    }))) });
    map.addSource('buildings', { type: 'geojson', data: collection(data.buildings.map(building => ({
      type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [building.coordinates] }
    }))) });
    map.addSource('route', { type: 'geojson', data: empty });
    map.addLayer({ id: 'buildings', type: 'fill', source: 'buildings', paint: { 'fill-color': '#b4bca8', 'fill-opacity': .65 } });
    map.addLayer({ id: 'paths-halo', type: 'line', source: 'paths', paint: { 'line-color': '#fff', 'line-width': 4 } });
    map.addLayer({ id: 'paths', type: 'line', source: 'paths', paint: { 'line-color': '#a7b49c', 'line-width': 2 } });
    map.addLayer({ id: 'route-halo', type: 'line', source: 'route', paint: { 'line-color': '#fff', 'line-width': 8 } });
    map.addLayer({ id: 'route', type: 'line', source: 'route', paint: { 'line-color': '#327663', 'line-width': 5 } });
    for (const place of data.landmarks) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'landmark';
      button.setAttribute('aria-label', `Route to ${place.name}`);
      const label = document.createElement('span');
      label.className = 'landmark-label';
      label.textContent = place.name;
      button.append(label);
      button.onclick = () => { destination.value = place.id; update(); };
      new maplibre.Marker({ element: button }).setLngLat(place.coordinates).addTo(map);
      markers.push({ place, button });
    }
    mapReady = true;
    element('map').dataset.mapReady = 'true';
    update();
  });
}

async function init() {
  try {
    const response = await fetch(new URL('./data/campus.json', import.meta.url), { signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    data = await response.json();
    if (data.version !== 1 || !data.paths?.length || !data.landmarks?.length || !data.points?.length) throw new Error('Unsupported campus data');
    for (const select of [start, destination]) {
      select.replaceChildren(...data.landmarks.map(place => new Option(place.name, place.id)));
      select.disabled = false;
    }
    start.value = 'library';
    destination.value = 'aq';
    start.onchange = destination.onchange = update;
    element('swap').disabled = false;
    element('swap').onclick = () => { [start.value, destination.value] = [destination.value, start.value]; update(); };
    update();
  } catch (error) {
    element('load-error').textContent = `Campus data could not load. Reload to try again. (${error.message})`;
    element('load-error').hidden = false;
    element('route-summary').textContent = 'Campus routing is unavailable.';
    start.disabled = destination.disabled = element('swap').disabled = true;
    return;
  }
  try {
    createMap();
    element('overview').disabled = false;
    element('overview').onclick = overview;
  } catch {
    notice('The map could not start. Use the location selectors to compare route distances.');
  }
}

init();
