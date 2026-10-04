import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  timeout: 30000,
  outputDir: './test-results',
  use: { baseURL: 'http://127.0.0.1:3011', headless: true, launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] } },
  webServer: {
    command: 'npx --yes http-server .. -p 3011 -a 127.0.0.1 -c-1',
    url: 'http://127.0.0.1:3011/rasuwa/',
    reuseExistingServer: false,
    timeout: 15000
  }
});
