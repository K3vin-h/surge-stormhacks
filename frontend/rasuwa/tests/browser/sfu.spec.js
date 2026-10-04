import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('https://tile.openstreetmap.org/**', route => route.abort());
});

test('SFU campus selection draws a walking route and swap reverses the locations', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/sfu/');
  await expect(page.getByLabel('Start', { exact: true })).toBeEnabled();
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
