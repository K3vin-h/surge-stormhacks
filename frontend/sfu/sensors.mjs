/** Fixed demo heuristic; the flooded extent is a separate fictional scenario input. */
export function assessRegions(data) {
  if (data.provenance !== 'simulated' || !Array.isArray(data.regions) || !data.regions.length || !Array.isArray(data.readings)) {
    throw new Error('Unsupported sensor simulation.');
  }
  const ids = new Set();
  for (const region of data.regions) {
    const bounds = region.bounds;
    if (typeof region.id !== 'string' || !region.id || ids.has(region.id) || typeof region.name !== 'string'
      || !Array.isArray(bounds) || bounds.length !== 4 || !bounds.every(Number.isFinite)
      || bounds[0] >= bounds[2] || bounds[1] >= bounds[3]
      || bounds[0] < -180 || bounds[2] > 180 || bounds[1] < -90 || bounds[3] > 90
      || typeof region.simulated_flood !== 'boolean') throw new Error('Invalid campus region.');
    ids.add(region.id);
  }
  const readings = new Map();
  for (const reading of data.readings) {
    if (!ids.has(reading.region_id)) throw new Error('Unknown sensor region.');
    if (readings.has(reading.region_id)) throw new Error('Duplicate sensor reading.');
    for (const [field, maximum] of [['rainfall_mm_24h', Infinity], ['water_level_ratio', Infinity], ['soil_moisture_pct', 100]]) {
      const value = reading[field];
      if (!Number.isFinite(value) || value < 0 || value > maximum) throw new Error(`Invalid ${field}.`);
    }
    if (typeof reading.observed_at !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(reading.observed_at)
      || !Number.isFinite(Date.parse(reading.observed_at))) throw new Error('Sensor timestamps must include a timezone.');
    readings.set(reading.region_id, reading);
  }
  return data.regions.map(region => {
    const reading = readings.get(region.id);
    const score = reading
      ? .45 * Math.min(reading.rainfall_mm_24h / 150, 1)
        + .40 * Math.min(reading.water_level_ratio / 1.2, 1)
        + .15 * reading.soil_moisture_pct / 100
      : null;
    const risk_level = score === null ? 'Unknown' : score >= .8 ? 'Extreme' : score >= .55 ? 'High' : score >= .3 ? 'Moderate' : 'Low';
    return {
      ...region, reading: reading ?? null, risk_level, sensor_score: score === null ? null : Math.round(score * 1000) / 1000,
      status: region.simulated_flood ? 'Simulated flooding' : `${risk_level} risk`,
      color: region.simulated_flood ? '#c66151' : risk_level === 'Low' ? '#6b9367' : risk_level === 'Unknown' ? '#929b92' : '#caa04c'
    };
  });
}

function intersectsBounds(a, b, bounds) {
  let entry = 0, exit = 1;
  for (let axis = 0; axis < 2; axis++) {
    const delta = b[axis] - a[axis];
    if (delta === 0) {
      if (a[axis] < bounds[axis] || a[axis] > bounds[axis + 2]) return false;
    } else {
      const near = (bounds[axis] - a[axis]) / delta;
      const far = (bounds[axis + 2] - a[axis]) / delta;
      entry = Math.max(entry, Math.min(near, far));
      exit = Math.min(exit, Math.max(near, far));
      if (entry > exit) return false;
    }
  }
  return true;
}

/** Conservatively close an entire mapped way when any segment crosses a flooded sector. */
export function floodedRoadIds(campus, regions) {
  const flooded = regions.filter(region => region.simulated_flood);
  return [...new Set(campus.paths.filter(path => path.nodes.slice(1).some((node, i) => flooded.some(region =>
    intersectsBounds(campus.points[path.nodes[i]], campus.points[node], region.bounds)
  ))).map(path => path.id))];
}
