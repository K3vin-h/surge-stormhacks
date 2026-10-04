import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('https://tile.openstreetmap.org/**', route => route.abort());
  await page.route('https://tiles.maps.eox.at/**', route => route.abort());
});

test('SFU campus selection draws a walking route and swap reverses the locations', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/sfu/');
  await expect(page.getByLabel('Start', { exact: true })).toBeEnabled();
  await page.getByLabel('Avoid simulated flooded areas').uncheck();
  await page.getByLabel('Start', { exact: true }).selectOption('library');
  await page.getByLabel('Destination', { exact: true }).selectOption('asb');
  await expect(page.locator('#route-summary')).toContainText('Applied Sciences Building');
  await expect(page.locator('#route-distance')).toHaveText(/\d+ m/);
  await expect(page.locator('#map')).toHaveAttribute('data-route-ready', 'true');
  await page.getByRole('button', { name: 'Swap start and destination' }).click();
  await expect(page.getByLabel('Start', { exact: true })).toHaveValue('asb');
  await expect(page.getByLabel('Destination', { exact: true })).toHaveValue('library');
  await expect(page.locator('#route-summary')).toContainText('WAC Bennett Library');
  await page.screenshot({ path: test.info().outputPath('sfu-desktop.png'), fullPage: true });
  await page.getByLabel('Destination', { exact: true }).selectOption('asb');
  await expect(page.locator('#route-summary')).toContainText('already at');
  await expect(page.locator('#map')).toHaveAttribute('data-route-ready', 'false');
  expect(errors).toEqual([]);
});

test('SFU map works on mobile and fails visibly when campus data is unavailable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/sfu/');
  await expect(page.locator('#map')).toHaveAttribute('data-map-ready', 'true');
  const width = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }));
  expect(width.content).toBeLessThanOrEqual(width.viewport);
  await page.screenshot({ path: test.info().outputPath('sfu-mobile.png'), fullPage: true });
  await page.route('**/sfu/data/campus.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('Campus data could not load');
  await expect(page.getByLabel('Start', { exact: true })).toBeDisabled();
});

test('government route planner can open the SFU campus map', async ({ page }) => {
  await page.goto('/gov.html#planner');
  await page.getByRole('button', { name: 'SFU Burnaby', exact: true }).click();
  const campus = page.frameLocator('#planner iframe');
  await expect(campus.getByLabel('Start', { exact: true })).toBeEnabled();
  await expect(page.locator('#plannerRegion')).toContainText('campus walking routes');
  await campus.getByLabel('Destination', { exact: true }).selectOption('asb');
  await page.getByRole('button', { name: 'Close route planner' }).click();
  await page.locator('[data-planner]').first().click();
  await expect(campus.getByLabel('Destination', { exact: true })).toHaveValue('asb');
});

test('SFU flood regions show their readings and the avoidance toggle changes route eligibility', async ({ page }) => {
  await page.goto('/sfu/');
  await expect(page.getByLabel('Avoid simulated flooded areas')).toBeChecked();
  await expect(page.locator('#map')).toHaveAttribute('data-flood-regions', '3');
  await expect(page.locator('#sensor-readings')).toContainText('West campus');
  await expect(page.locator('#sensor-readings')).toContainText('Central campus');
  await expect(page.locator('#sensor-readings')).toContainText('East campus');
  await expect(page.locator('#sensor-readings')).toContainText('170 mm');
  await page.getByLabel('Destination', { exact: true }).selectOption('asb');
  await expect(page.locator('#route-summary')).toContainText('simulated flooded');
  await expect(page.locator('#map')).toHaveAttribute('data-route-ready', 'false');
  await page.getByLabel('Avoid simulated flooded areas').uncheck();
  await expect(page.locator('#map')).toHaveAttribute('data-route-ready', 'true');
  await page.getByLabel('Avoid simulated flooded areas').check();
  await expect(page.locator('#map')).toHaveAttribute('data-route-ready', 'false');
  await page.getByRole('button', { name: /East campus/ }).click();
  await expect(page.locator('.maplibregl-popup')).toContainText('Simulated flooding');
  await page.getByRole('button', { name: 'Campus overview' }).click();
  await page.screenshot({ path: test.info().outputPath('sfu-flood-regions.png'), fullPage: true });
});

test('missing sensor simulation fails visibly and keeps route planning disabled', async ({ page }) => {
  await page.route('**/sfu/data/sensors.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.goto('/sfu/');
  await expect(page.getByRole('alert')).toContainText('Campus data could not load');
  await expect(page.getByLabel('Start', { exact: true })).toBeDisabled();
});

test('selecting an offscreen sensor region brings its readings into the visible map', async ({ page }) => {
  await page.goto('/sfu/');
  await expect(page.locator('#map')).toHaveAttribute('data-route-ready', 'true');
  await page.getByRole('button', { name: /East campus/ }).click();
  const popup = page.locator('.maplibregl-popup-content');
  await expect(popup).toContainText('Simulated flooding');
  await expect.poll(async () => {
    const box = await popup.boundingBox();
    const map = await page.locator('#map').boundingBox();
    return box && map && box.x >= map.x && box.y >= map.y
      && box.x + box.width <= map.x + map.width && box.y + box.height <= map.y + map.height;
  }).toBe(true);
});
