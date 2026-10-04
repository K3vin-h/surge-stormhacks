// Public imagery settings only. No backend URL or private provider keys.
// Set satelliteTiles to an empty string to use just the local geographic layers.
export const mapConfig = {
  satelliteTiles: 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2025_3857/default/g/{z}/{y}/{x}.jpg',
  satelliteAttribution: 'EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2025)',
  glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf'
};
