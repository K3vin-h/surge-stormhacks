const element = id => document.getElementById(`gov-${id}`);
let areas = [], current = '', catalog = null, generation = 0, timer, publishing = false;

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options, headers: { 'Content-Type': 'application/json' },
    signal: AbortSignal.timeout(15000)
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}

function options(id, entries) {
  element(id).replaceChildren(...entries.map(entry => {
    const option = document.createElement('option');
    option.value = entry.id;
    option.textContent = `${entry.name}${entry.status ? ` (${entry.status})` : ''}`;
    return option;
  }));
}

function items(id, entries, title, description, empty) {
  const container = element(id);
  container.replaceChildren();
  if (!entries.length) { container.textContent = empty; return; }
  for (const entry of entries) {
    const article = document.createElement('article');
    article.className = 'operation-item';
    const heading = document.createElement('strong');
    heading.textContent = title(entry);
    const body = document.createElement('p');
    body.textContent = description(entry);
    article.append(heading, body);
    container.append(article);
  }
}

function renderAreas() {
  element('areas').replaceChildren(...areas.map(area => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'area-button';
    button.disabled = publishing;
    button.setAttribute('aria-pressed', String(area.area_id === current));
    button.textContent = `${area.name} · risk ${area.risk.risk_level} · priority ${area.priority.priority_level} (${area.priority.score.toFixed(2)})`;
    button.addEventListener('click', () => {
      element('area').value = area.area_id;
      void chooseArea(area.area_id);
    });
    return button;
  }));
}

function typeChanged() {
  const evacuation = element('type').value === 'evacuate';
  element('evac').hidden = !evacuation;
  element('shelter').required = evacuation;
  element('route').required = evacuation;
}

function unavailable(error) {
  clearTimeout(timer);
  element('fields').disabled = true;
  element('refresh-model').disabled = true;
  element('status').textContent = `Government API unavailable: ${error.message}. Reconnect to retry. Local Rasuwa routing remains available.`;
  element('connect').textContent = 'Reconnect government API';
}

async function refresh() {
  const requestGeneration = generation;
  const area = current;
  try {
    const [dashboard, reports, instruction] = await Promise.all([
      api('/api/government/dashboard'),
      api(`/api/government/reports?area_id=${encodeURIComponent(area)}`),
      api(`/api/government/instructions/${encodeURIComponent(area)}`)
    ]);
    if (requestGeneration !== generation) return;
    areas = dashboard.areas;
    renderAreas();
    items('events', dashboard.events, event => event.kind, event => `${event.summary} · ${event.created_at}`, 'No operational events yet.');
    items('reports', reports.reports, report => `${report.kind} · ${report.verification_state}`, report => `${report.message} · ${report.received_at}`, 'No community reports for this area.');
    const name = areas.find(item => item.area_id === area)?.name || area;
    element('status').textContent = `${name} · updated ${dashboard.updated_at} · current directive: ${instruction.instruction?.instruction_type || 'none'} · ${dashboard.freshness?.publication_state || 'no publication freshness supplied'}`;
    element('fields').disabled = publishing || !catalog;
    element('refresh-model').disabled = publishing || !catalog;
    clearTimeout(timer);
    timer = setTimeout(() => void refresh(), 15000);
  } catch (error) {
    if (requestGeneration === generation) unavailable(error);
  }
}

async function chooseArea(area) {
  if (publishing) return;
  clearTimeout(timer);
  const requestGeneration = ++generation;
  current = area;
  catalog = null;
  element('fields').disabled = true;
  element('refresh-model').disabled = true;
  element('publish-status').textContent = '';
  element('message').value = '';
  element('reports').textContent = 'Loading reports for the selected area…';
  for (const id of ['shelter', 'route', 'roads']) options(id, []);
  renderAreas();
  element('status').textContent = 'Loading selected government area…';
  try {
    const detail = await api(`/api/areas/${encodeURIComponent(area)}`);
    if (requestGeneration !== generation) return;
    catalog = detail;
    options('shelter', detail.shelters);
    options('route', detail.routes);
    options('roads', detail.roads);
    typeChanged();
    await refresh();
  } catch (error) {
    if (requestGeneration === generation) unavailable(error);
  }
}

element('connect').addEventListener('click', async () => {
  clearTimeout(timer);
  const requestGeneration = ++generation;
  element('connect').disabled = true;
  element('area').disabled = true;
  element('fields').disabled = true;
  element('refresh-model').disabled = true;
  element('status').textContent = 'Connecting to government API…';
  try {
    const dashboard = await api('/api/government/dashboard');
    if (requestGeneration !== generation) return;
    if (!dashboard.areas?.length) throw new Error('No government areas returned');
    areas = dashboard.areas;
    options('area', areas.map(area => ({ id: area.area_id, name: area.name })));
    const area = areas.some(area => area.area_id === current) ? current : areas[0].area_id;
    element('area').value = area;
    element('area').disabled = false;
    await chooseArea(area);
  } catch (error) {
    if (requestGeneration === generation) unavailable(error);
  } finally {
    element('connect').disabled = false;
  }
});

element('area').addEventListener('change', () => void chooseArea(element('area').value));
element('type').addEventListener('change', typeChanged);
element('refresh-model').addEventListener('click', async () => {
  const requestGeneration = generation;
  element('refresh-model').disabled = true;
  try {
    await api(`/api/government/areas/${encodeURIComponent(current)}/refresh`, { method: 'POST' });
    if (requestGeneration === generation) await refresh();
  } catch (error) {
    if (requestGeneration === generation) unavailable(error);
  }
});

element('form').addEventListener('submit', async event => {
  event.preventDefault();
  if (publishing || !catalog || element('fields').disabled) return;
  const message = element('message').value.trim();
  if (!message) { element('publish-status').textContent = 'Enter an emergency message.'; return; }
  const body = {
    publication_id: `pub-${crypto.randomUUID()}`, area_id: current,
    instruction_type: element('type').value, emergency_message: message,
    roads_to_avoid_ids: [...element('roads').selectedOptions].map(option => option.value),
    update_frequency_minutes: Number(element('frequency').value)
  };
  if (body.instruction_type === 'evacuate') {
    body.shelter_id = element('shelter').value;
    body.approved_route_id = element('route').value;
  }
  publishing = true;
  clearTimeout(timer);
  element('fields').disabled = true;
  element('area').disabled = true;
  element('connect').disabled = true;
  element('refresh-model').disabled = true;
  renderAreas();
  element('publish-status').textContent = 'Publishing directive…';
  try {
    if (body.instruction_type === 'all_clear') {
      const latest = await api(`/api/government/instructions/${encodeURIComponent(current)}`);
      body.cancels_instruction_id = latest.instruction?.publication_id || null;
    }
    const result = await api('/api/government/instructions', { method: 'POST', body: JSON.stringify(body) });
    element('publish-status').textContent = `Published ${result.instruction.instruction_type} for ${areas.find(area => area.area_id === current)?.name || current} (severity ${result.instruction.severity}).`;
  } catch (error) {
    element('publish-status').textContent = `Publication could not be confirmed: ${error.message}. Check the current directive before retrying.`;
  } finally {
    publishing = false;
    element('area').disabled = false;
    element('connect').disabled = false;
    await refresh();
  }
});

window.addEventListener('pagehide', () => { generation++; clearTimeout(timer); }, { once: true });
typeChanged();
