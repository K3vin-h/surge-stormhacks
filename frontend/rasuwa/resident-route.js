// Pure resident-routing logic for the Rasuwa area (no DOM). Wraps routing.js recommend().
import { recommend } from './routing.js';

export const MAX_DISTANCE_M = 50000;
export const MOVE_THRESHOLD_M = 50;

// Metres between two [lng, lat] points (haversine).
export function metresBetween(a, b) {
  const rad = (d) => (d * Math.PI) / 180;
  const h = Math.sin(rad(b[1] - a[1]) / 2) ** 2 +
    Math.cos(rad(a[1])) * Math.cos(rad(b[1])) * Math.sin(rad(b[0] - a[0]) / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.sqrt(h));
}

// Recompute only on the first fix or after moving more than the threshold.
export function shouldRecompute(prevPoint, nextPoint, thresholdM = MOVE_THRESHOLD_M) {
  if (!nextPoint) return false;
  if (!prevPoint) return true;
  return metresBetween(prevPoint, nextPoint) > thresholdM;
}

/**
 * Nearest reachable shelter by route distance.
 * previous: result of an earlier planRoute (or null). changedBecause lists the roads of the
 * previous route that are now blocked, i.e. why the route had to change.
 */
export function planRoute(data, { point, mode = 'walking', blocked = [], previous = null }) {
  const out = { route: null, destination: null, changedBecause: [], status: 'ok' };
  if (!point) return { ...out, status: 'no_location' };
  const blockedSet = new Set(blocked);
  const prevRoads = (previous && previous.route && previous.route.road_ids) || [];
  out.changedBecause = prevRoads.filter((id) => blockedSet.has(id));
  let result;
  try {
    result = recommend(data, { point, mode, maxDistance: MAX_DISTANCE_M, blocked });
  } catch (e) {
    if (!/No mapped road within/.test(e.message)) throw e;
    // Off the network entirely -> too_far; on it but every nearby road is closed -> no_route.
    let nearRoad = false;
    if (blocked.length) try { recommend(data, { point, mode, maxDistance: MAX_DISTANCE_M }); nearRoad = true; } catch { /* still off-network */ }
    return { ...out, status: nearRoad ? 'no_route' : 'too_far' };
  }
  const best = result.candidates
    .slice()
    .sort((a, b) => a.route.distance_m - b.route.distance_m)[0];
  if (!best) return { ...out, status: 'no_route' };
  return { ...out, route: best.route, destination: best.destination };
}
