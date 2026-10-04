import { mkdir, copyFile } from 'node:fs/promises';

const destination = new URL('../vendor/', import.meta.url);
await mkdir(destination, { recursive: true });
for (const name of ['maplibre-gl.mjs', 'maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs', 'maplibre-gl.css']) {
  await copyFile(new URL(`../node_modules/maplibre-gl/dist/${name}`, import.meta.url), new URL(name, destination));
}
await copyFile(new URL('../node_modules/maplibre-gl/LICENSE.txt', import.meta.url), new URL('MAPLIBRE-LICENSE.txt', destination));
console.log('Local MapLibre assets ready.');
