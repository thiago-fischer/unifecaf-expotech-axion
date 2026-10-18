import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  use: { baseURL: 'http://127.0.0.1:5174', browserName: 'chromium', trace: 'retain-on-failure' },
  webServer: [
    {
      command: 'uv run --locked --no-sync python ../frontend/scripts/serve_test_api.py',
      cwd: '../backend',
      url: 'http://127.0.0.1:8765/openapi.json',
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: 'npm run dev -- --port 5174',
      env: { AXION_API_TARGET: 'http://127.0.0.1:8765' },
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
    },
  ],
});
