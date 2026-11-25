const { defineConfig, devices } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests',
  timeout: 30000,
  expect: { timeout: 8000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [ ['list'], ['html', { outputFolder: './reports/e2e-html', open: 'never' }], ['junit', { outputFile: './reports/e2e-results.xml' }] ],
  use: {
    baseURL: 'http://127.0.0.1:13000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } }
  ]
});
