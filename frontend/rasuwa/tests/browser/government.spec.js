import { test, expect } from '@playwright/test';

test('government publication uses selected catalog area and renders reports as text', async ({ page }) => {
  let published;
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let body;
    if (path.endsWith('/dashboard')) body = { areas: [
      { area_id: 'sunsari', name: 'Sunsari', risk: { risk_level: 'High' }, priority: { score: .8, priority_level: 'High' } },
      { area_id: 'bardiya', name: 'Bardiya', risk: { risk_level: 'Low' }, priority: { score: .2, priority_level: 'Low' } }
    ], events: [{ summary: 'Model refreshed', kind: 'model_refresh', created_at: '2026-10-03T12:00:00Z' }], updated_at: '2026-10-03T12:00:00Z' };
    else if (path.startsWith('/api/areas/')) {
      const id = path.split('/').at(-1);
      body = { shelters: [{ id: `${id}-shelter`, name: `${id} shelter` }], routes: [{ id: `${id}-route`, name: `${id} route` }], roads: [{ id: `${id}-road`, name: `${id} road`, status: 'open' }] };
    } else if (path.endsWith('/reports')) body = { reports: [{ kind: 'rescue_needed', message: '<img src=x onerror=alert(1)>', verification_state: 'unverified', received_at: '2026-10-03T12:00:00Z' }] };
    else if (path.endsWith('/instructions')) { published = route.request().postDataJSON(); body = { instruction: { instruction_type: published.instruction_type, severity: 'High' } }; }
    else body = { instruction: null };
    await route.fulfill({ json: body });
  });
  await page.goto('/rasuwa/');
  await page.getByRole('button', { name: 'Connect government API' }).click();
  await expect(page.getByLabel('Government area')).toBeEnabled();
  await page.getByLabel('Government area').selectOption('bardiya');
  await expect(page.getByLabel('Shelter', { exact: true })).toHaveValue('bardiya-shelter');
  await expect(page.locator('#gov-reports')).toContainText('<img src=x onerror=alert(1)>');
  await expect(page.locator('#gov-reports img')).toHaveCount(0);
  await page.getByLabel('Emergency message').fill('Use the approved route.');
  await page.getByRole('button', { name: 'Publish directive' }).click();
  await expect(page.locator('#gov-publish-status')).toContainText('Published');
  expect(published.area_id).toBe('bardiya');
  expect(published.shelter_id).toBe('bardiya-shelter');
  expect(published.approved_route_id).toBe('bardiya-route');
});

test('unavailable government API leaves local routing usable and publishing disabled', async ({ page }) => {
  await page.route('**/api/**', route => route.fulfill({ status: 503, json: { detail: 'Unavailable' } }));
  await page.goto('/rasuwa/');
  await page.getByRole('button', { name: 'Connect government API' }).click();
  await expect(page.locator('#gov-status')).toContainText('unavailable');
  await expect(page.getByRole('button', { name: 'Publish directive' })).toBeDisabled();
  await expect(page.getByLabel('Origin village')).toBeEnabled();
});
