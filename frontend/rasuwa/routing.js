/** Searches a prepared, hazard/access-filtered transport graph locally.
 * No route is an evacuation order or a claim of safety.
 */
class MinHeap {
  items = [];
  push(item) {
    const a = this.items;
    a.push(item);
    let i = a.length - 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (a[parent][0] <= item[0]) break;
      a[i] = a[parent];
      i = parent;
    }
    a[i] = item;
  }
  pop() {
    const a = this.items;
    const result = a[0];
    const last = a.pop();
    if (a.length) {
      let i = 0;
      while (i * 2 + 1 < a.length) {
        let child = i * 2 + 1;
        if (child + 1 < a.length && a[child + 1][0] < a[child][0]) child++;
        if (a[child][0] >= last[0]) break;
        a[i] = a[child];
        i = child;
      }
      a[i] = last;
    }
    return result;
  }
}

function shortestPaths(graph, source) {
  const distances = new Map([[source, 0]]);
  const previous = new Map();
  const heap = new MinHeap();
  heap.push([0, source]);
  while (heap.items.length) {
    const [distance, node] = heap.pop();
    if (distance !== distances.get(node)) continue;
    for (const [next, length, road] of graph.edges[node] || []) {
      const total = distance + length;
      if (!distances.has(next) || total < distances.get(next)) {
        distances.set(next, total);
        previous.set(next, { node, road });
        heap.push([total, next]);
      }
    }
  }
  return { distances, previous };
}

export function recommend(data, { origin, mode, maxDistance, version = data.dataset_version }) {
  if (typeof maxDistance !== 'number' || !Number.isFinite(maxDistance) || maxDistance <= 0 || maxDistance > 50000) {
    throw new Error('Set a distance limit between 1 and 50,000 metres.');
  }
  if (!['walking', 'vehicle'].includes(mode)) throw new Error('Unknown travel mode.');
  if (version !== data.dataset_version) throw new Error('Map data changed; reload before selecting a route.');
  if (!data.map.settlements.features.some(f => f.properties.id === origin)) throw new Error('Unknown village.');
  const graph = data.graphs[mode];
  const source = graph.origins[origin];
  const exclusions = { ...graph.exclusions };
  const candidates = [];
  const { distances, previous } = source == null
    ? { distances: new Map(), previous: new Map() }
    : shortestPaths(graph, source);
  for (const destination of graph.destinations) {
    const reachable = destination.targets.filter(n => distances.has(n));
    reachable.sort((a, b) => distances.get(a) - distances.get(b) || String(a).localeCompare(String(b), 'en'));
    const target = reachable.length ? reachable[0] : destination.fallback;
    if (target == null || !distances.has(target)) {
      exclusions[destination.id] = 'No admissible mapped connection under the current scenario.';
      continue;
    }
    const distance = distances.get(target);
    if (distance > maxDistance) {
      exclusions[destination.id] = 'Exceeds the official’s mapped-route distance limit.';
      continue;
    }
    const nodes = [target];
    const roads = new Set();
    let node = target;
    while (previous.has(node)) {
      const edge = previous.get(node);
      roads.add(edge.road);
      node = edge.node;
      nodes.push(node);
    }
    if (nodes.length < 2) {
      exclusions[destination.id] = 'No distinct mapped route between access points.';
      continue;
    }
    nodes.reverse();
    candidates.push({
      destination: {
        shelter_id: destination.id,
        name: destination.name,
        destination_kind: destination.kind,
        location: { type: 'Point', coordinates: reachable.length ? graph.nodes[target] : destination.location }
      },
      route: {
        route_id: `${data.dataset_version}:${mode}:${origin}:${destination.id}`,
        name: `${mode === 'walking' ? 'Walking' : 'Vehicle'} to ${destination.name}`,
        mode,
        distance_m: Math.round(distance * 10) / 10,
        search_limit_m: maxDistance,
        dataset_version: data.dataset_version,
        geometry: { type: 'LineString', coordinates: nodes.map(n => graph.nodes[n]) },
        road_ids: [...roads].sort()
      },
      evidence: [destination.source],
      assessment_status: 'unverified_simulation',
      unknowns: [
        'Capacity', 'Permission/opening status',
        destination.kind === 'open_ground' ? 'Ground surface and usability' : 'Structural condition',
        'Terrain/landslide safety', 'Current field access',
        'Access between markers and mapped route endpoints needs field verification; it is not included in the distance.'
      ]
    });
  }
  candidates.sort((a, b) => a.route.distance_m - b.route.distance_m || a.destination.shelter_id.localeCompare(b.destination.shelter_id, 'en'));
  return { candidates: candidates.slice(0, 6), exclusions, message: candidates.length ? 'Candidates require government review' : 'No route found under the current constraints' };
}
