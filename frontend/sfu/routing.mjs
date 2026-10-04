import { recommend } from '../rasuwa/routing.js';
import { metresBetween } from '../rasuwa/resident-route.js';

const graphs = new WeakMap();

function walkingGraph(data) {
  if (graphs.has(data)) return graphs.get(data);
  const nodes = Object.fromEntries(data.points.map((point, index) => [String(index), point]));
  const edges = {};
  for (const path of data.paths) {
    for (let i = 1; i < path.nodes.length; i++) {
      const a = String(path.nodes[i - 1]);
      const b = String(path.nodes[i]);
      const length = metresBetween(nodes[a], nodes[b]);
      (edges[a] ??= []).push([b, length, path.id]);
      (edges[b] ??= []).push([a, length, path.id]);
    }
  }
  const graph = {
    nodes, edges, exclusions: {},
    origins: Object.fromEntries(data.landmarks.map(place => [place.id, String(place.node)])),
    destinations: data.landmarks.map(place => ({
      id: place.id, name: place.name, kind: 'campus', source: place.source,
      targets: [String(place.node)], fallback: null, location: place.coordinates
    }))
  };
  graphs.set(data, graph);
  return graph;
}

/** Route between selected landmark access points using the shared distance search. */
export function campusRoute(data, { from, to, blocked = [] }) {
  const origin = data.landmarks.find(place => place.id === from);
  const destination = data.landmarks.find(place => place.id === to);
  if (!origin || !destination) throw new Error('Unknown campus location.');
  if (from === to) return { status: 'same_place', route: null };
  if (origin.node === destination.node) return { status: 'nearby', route: null };
  const graph = walkingGraph(data);
  const prepared = {
    dataset_version: data.dataset_version,
    map: { settlements: { features: data.landmarks.map(place => ({ properties: { id: place.id } })) } },
    graphs: { walking: { ...graph, destinations: graph.destinations.filter(place => place.id === to) } }
  };
  const result = recommend(prepared, { origin: from, mode: 'walking', maxDistance: 5000, blocked });
  const candidate = result.candidates[0];
  return candidate ? { status: 'ok', route: candidate.route } : { status: 'no_route', route: null };
}
