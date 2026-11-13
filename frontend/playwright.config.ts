import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  use: {
    baseURL: 'http://127.0.0.1:5174',
    browserName: 'chromium',
    channel: process.env.PLAYWRIGHT_CHANNEL,
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command:
        'uv run --project ../backend --locked --no-sync uvicorn axion_controller.main:create_app --factory --host 127.0.0.1 --port 8766',
      cwd: '../controller',
      env: { AXION_CONTROLLER_INITIAL_PIECES: '1' },
      url: 'http://127.0.0.1:8766/openapi.json',
      reuseExistingServer: false,
    },
    {
      command: 'uv run --locked --no-sync python ../frontend/scripts/serve_test_api.py',
      cwd: '../backend',
      env: { AXION_CONTROLLER_URL: 'http://127.0.0.1:8766' },
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
