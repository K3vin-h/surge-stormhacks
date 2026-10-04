import { recommend } from './routing.js';
import { createMap } from './map-view.js';
import { mapConfig } from './config.js';

const element = id => document.getElementById(id);
const village = element('village');
const inputs = { walking: element('walking-limit'), vehicle: element('vehicle-limit') };
let data, map;
let candidates = [];

function select(candidate) {
  element('selection').hidden = !candidate;
  for (const button of element('candidates').children) button.setAttribute('aria-pressed', String(button.dataset.destination === candidate?.destination.shelter_id));
  if (candidate) {
    element('selected-name').textContent = candidate.route.name;
    element('selected-distance').textContent = `${candidate.route.distance_m} m along the mapped graph. Official search limit: ${candidate.route.search_limit_m} m.`;
    element('unknowns').replaceChildren(...candidate.unknowns.map(text => {
      const item = document.createElement('li');
      item.textContent = text;
      return item;
    }));
    const link = element('evidence');
    link.hidden = true;
    link.removeAttribute('href');
    try {
      const url = new URL(candidate.evidence[0]);
      if (url.protocol === 'https:' && ['openstreetmap.org', 'www.openstreetmap.org'].includes(url.hostname)) {
        link.href = url.href;
        link.hidden = false;
      }
    } catch { /* An absent/invalid provenance URL is not rendered as a link. */ }
  }
  map?.update(candidates, candidate);
}

function search() {
  candidates = [];
  element('candidates').replaceChildren();
  element('excluded').hidden = true;
  select(null);
  if (!data) return;
  const mode = document.querySelector('input[name=mode]:checked').value;
  const limit = Number(inputs[mode].value);
  if (!inputs[mode].value || !Number.isFinite(limit) || limit <= 0 || limit > 50000) {
    element('route-status').textContent = `Set a ${mode} distance limit between 1 and 50,000 metres.`;
    return;
  }
  if (!village.value) {
    element('route-status').textContent = 'Select a mapped village to find nearby candidates.';
    return;
  }
  try {
    const result = recommend(data, { origin: village.value, mode, maxDistance: limit });
    candidates = result.candidates;
    element('route-status').textContent = result.message;
    for (const candidate of candidates) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'candidate';
      button.dataset.destination = candidate.destination.shelter_id;
      button.setAttribute('aria-pressed', 'false');
      const title = document.createElement('strong');
      title.textContent = candidate.destination.name;
      const distance = document.createElement('span');
      distance.textContent = `${candidate.route.distance_m} m on mapped graph`;
      const kind = document.createElement('small');
      kind.textContent = candidate.destination.destination_kind === 'open_ground' ? 'Open-ground patch; suitability unverified' : 'Mapped facility; suitability unverified';
      button.append(title, distance, kind);
      button.addEventListener('click', () => select(candidate));
      element('candidates').append(button);
    }
    const names = new Map([...data.map.facilities.features, ...data.map.open_ground.features].map(f => [f.properties.id, f.properties.name]));
    element('exclusions').replaceChildren(...Object.entries(result.exclusions).map(([id, reason]) => {
      const item = document.createElement('li');
      item.textContent = `${names.get(id) || id}: ${reason}`;
      return item;
    }));
    element('excluded').hidden = !Object.keys(result.exclusions).length;
    map?.update(candidates, null);
  } catch (error) {
    element('route-status').textContent = error.message;
  }
}

async function start() {
  try {
    const response = await fetch(new URL('./data/prepared.json', import.meta.url), { signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    data = await response.json();
    if (data.format_version !== 1 || !data.map?.settlements?.features || !data.graphs?.walking || !data.graphs?.vehicle) throw new Error('Unsupported geographic dataset');
    for (const feature of data.map.settlements.features) {
      const option = document.createElement('option');
      option.value = feature.properties.id;
      option.textContent = feature.properties.name;
      village.append(option);
    }
    element('scenario').textContent = data.scenario;
    for (const reading of data.sensors?.readings || []) {
      const ward = data.map.wards.features.find(feature => feature.properties.id === reading.ward_id);
      const properties = data.map.risk_zones.features.find(feature => feature.properties.ward_id === reading.ward_id && feature.properties.sensor_risk_level)?.properties;
      const card = document.createElement('article');
      card.className = `sensor-card risk-${properties?.sensor_risk_level || 'Unknown'}`;
      const title = document.createElement('strong');
      title.textContent = `${ward?.properties.name || reading.ward_id} · ${properties?.sensor_risk_level || 'Unknown'}`;
      const body = document.createElement('p');
      body.textContent = `Rain ${reading.rainfall_mm_24h} mm/24h · river/warning ${reading.river_level_ratio} · soil ${reading.soil_moisture_pct}%`;
      const time = document.createElement('small');
      time.textContent = `Observed ${reading.observed_at} · ${data.sensors.provenance}`;
      card.append(title, body, time);
      element('sensor-readings').append(card);
    }
    element('dataset-label').textContent = `${data.map.settlements.features.length} origins · ${data.map.wards.features.length} wards · dataset ${data.dataset_version}`;
    village.disabled = false;
    element('mode-controls').disabled = false;
    for (const input of Object.values(inputs)) input.disabled = false;
    try {
      map = createMap(element('map'), data.map, {
        config: mapConfig,
        onVillage: id => { village.value = id; search(); },
        onNotice: text => { element('map-notice').hidden = false; element('map-notice').textContent = text; },
        onCell: text => { element('map-caption').textContent = text; }
      });
      element('overview').disabled = false;
      element('overview').addEventListener('click', () => map.overview());
      window.addEventListener('pagehide', () => map.destroy(), { once: true });
    } catch {
      element('map-notice').hidden = false;
      element('map-notice').textContent = 'The map renderer could not start. Enable WebGL or use a supported browser. The village list and route search remain available.';
    }
    village.addEventListener('change', search);
    for (const input of Object.values(inputs)) input.addEventListener('input', search);
    for (const radio of document.querySelectorAll('input[name=mode]')) radio.addEventListener('change', search);
    search();
  } catch (error) {
    data = null;
    element('load-error').hidden = false;
    element('load-error').textContent = `Map data could not load: ${error.message}. Serve the frontend over HTTP and reload.`;
    element('route-status').textContent = 'Route planning is unavailable until the geographic data loads.';
  }
}

await start();
