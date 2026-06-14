import { defineConfig } from '@playwright/test'
import { resolve } from 'path'

const dbPath = resolve(import.meta.dirname, '..', 'app', 'data', 'test-e2e.db')
const apiPort = Number(process.env.PLAYWRIGHT_API_PORT || 5001)
const webPort = Number(process.env.PLAYWRIGHT_WEB_PORT || 3000)
const apiBaseUrl = `http://localhost:${apiPort}`

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: 0,
  reporter: 'html',
  use: {
    baseURL: `http://localhost:${webPort}`,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command: `DATABASE_URI="sqlite:///${dbPath}" TESTING=1 DOG_NO_CRAWLER=true SECRET_KEY=e2e-secret PYTHONDONTWRITEBYTECODE=1 FLASK_RUN_HOST=127.0.0.1 FLASK_RUN_PORT=${apiPort} python3 ../run.py`,
      port: apiPort,
      reuseExistingServer: !process.env.CI,
      cwd: import.meta.dirname,
    },
    {
      command: `TESTING=1 API_BASE_URL=${apiBaseUrl} npx nuxt build && API_BASE_URL=${apiBaseUrl} npx nuxt preview --port ${webPort}`,
      port: webPort,
      reuseExistingServer: !process.env.CI,
      cwd: import.meta.dirname,
    },
  ],
})
