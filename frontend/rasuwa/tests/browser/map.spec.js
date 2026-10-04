import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  page.on('pageerror', error => console.error('Map page error:', error.message));
  // External imagery is not required for the actual geography or routing tests.
  await page.route('https://tiles.maps.eox.at/**', route => route.abort());
  await page.route('https://demotiles.maplibre.org/**', route => route.abort());
});

test('home entry opens an independent map and distance changes clear route selection', async ({ page }) => {
  const apiCalls = [];
  const failures = [];
  page.on('request', request => { if (new URL(request.url()).pathname.startsWith('/api/')) apiCalls.push(request.url()); });
  page.on('pageerror', error => failures.push(error.message));
  await page.goto('/');
  await page.getByRole('link', { name: /Rasuwa Route Planner/ }).click();
  await expect(page.getByLabel('Origin village')).toBeEnabled();
  await page.getByLabel('Walking limit (metres)').fill('500');
  await page.getByLabel('Vehicle limit (metres)').fill('2000');
  await page.getByLabel('Origin village').selectOption({ label: 'National Rainbow Trout Research Station, Dhunche' });
  await page.getByRole('button', { name: /Pasture demonstration plots/ }).click();
  await expect(page.getByRole('heading', { name: 'Selected route' })).toBeVisible();
  await expect(page.getByText('Open-ground patch; suitability unverified', { exact: true })).toBeVisible();
  await expect(page.locator('#map')).toHaveAttribute('data-map-ready', 'true');
  await expect(page.locator('#map')).toHaveAttribute('data-selected-mode', 'walking');
  await expect(page.getByLabel('Flood risk legend')).toContainText('Extreme');
  await expect(page.getByLabel('Flood risk legend')).toContainText('High');
  await expect(page.getByLabel('Flood risk legend')).toContainText('Moderate');
  await expect(page.getByLabel('Flood risk legend')).toContainText('Low');
  await page.screenshot({ path: test.info().outputPath('desktop.png'), fullPage: true });
  await page.getByLabel('Walking limit (metres)').fill('100');
  await expect(page.getByRole('button', { name: /Pasture demonstration plots/ })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Selected route' })).toHaveCount(0);
  await expect(page.locator('#map')).not.toHaveAttribute('data-selected-mode', 'walking');
  expect(apiCalls).toEqual([]);
  expect(failures).toEqual([]);
});

test('walking and vehicle limits are independent and missing values never choose a default', async ({ page }) => {
  await page.goto('/rasuwa/');
  await expect(page.getByLabel('Origin village')).toBeEnabled();
  await page.getByLabel('Origin village').selectOption({ label: 'National Rainbow Trout Research Station, Dhunche' });
  await expect(page.getByRole('status').filter({ hasText: /distance limit/ })).toBeVisible();
  await page.getByLabel('Walking limit (metres)').fill('500');
  await expect(page.getByRole('button', { name: /Pasture demonstration plots/ })).toBeVisible();
  await page.getByRole('radio', { name: 'Vehicle', exact: true }).check();
  await expect(page.getByRole('button', { name: /Pasture demonstration plots/ })).toHaveCount(0);
  await page.getByLabel('Vehicle limit (metres)').fill('500');
  await page.getByRole('button', { name: /Pasture demonstration plots/ }).click();
  await expect(page.locator('#map')).toHaveAttribute('data-selected-mode', 'vehicle');
  await page.getByLabel('Vehicle limit (metres)').fill('100');
  await expect(page.getByRole('button', { name: /Pasture demonstration plots/ })).toHaveCount(0);
  await page.getByRole('radio', { name: 'Walking', exact: true }).check();
  await expect(page.getByRole('button', { name: /Pasture demonstration plots/ })).toBeVisible();
});

test('failed geographic data shows an error and keeps planning disabled', async ({ page }) => {
  await page.route('**/data/prepared.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.goto('/rasuwa/');
  await expect(page.getByRole('alert')).toContainText('Map data could not load');
  await expect(page.getByLabel('Origin village')).toBeDisabled();
});

test('mobile layout has usable map controls without horizontal page overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/rasuwa/');
  await expect(page.getByLabel('Origin village')).toBeEnabled();
  await expect(page.locator('#map')).toHaveAttribute('data-map-ready', 'true');
  const width = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }));
  expect(width.content).toBeLessThanOrEqual(width.viewport);
  await expect(page.getByRole('button', { name: 'Map overview' })).toBeVisible();
});
