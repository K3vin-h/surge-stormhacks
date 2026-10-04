// Pure helpers shared by app.js, map-view.js and government.js. `roads` is the
// /api/public/roads/status list: [{road_id, status: 'closed'|'flooded', note, updated_at}].
export const blockedIds = roads => [...new Set(roads.map(road => road.road_id))].sort();

export function statusFeatures(roadsCollection, roads) {
  const status = new Map(roads.map(road => [road.road_id, road.status]));
  return roadsCollection.features
    .filter(feature => status.has(feature.properties.id))
    .map(feature => ({ ...feature, properties: { ...feature.properties, status: status.get(feature.properties.id) } }));
}

export const roadLabel = properties => properties.name ? `${properties.name} (${properties.id})` : properties.id;
