import { defineConfig } from '@playwright/test'
import { existsSync } from 'fs'
import { resolve } from 'path'

const dbPath = resolve(import.meta.dirname, '..', 'app', 'data', 'test-e2e.db')
const apiPort = Number(process.env.PLAYWRIGHT_API_PORT || 5001)
const webPort = Number(process.env.PLAYWRIGHT_WEB_PORT || 3000)
const apiBaseUrl = `http://localhost:${apiPort}`
const localPython = resolve(import.meta.dirname, '..', '.venv', 'bin', 'python')
const pythonBin = process.env.PYTHON || (existsSync(localPython) ? localPython : 'python3')

function shellQuote(value) {
  return `'${String(value).replace(/'/g, "'\\''")}'`
}

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
      command: `DATABASE_URI=${shellQuote(`sqlite:///${dbPath}`)} TESTING=1 DOG_NO_CRAWLER=true SECRET_KEY=e2e-secret PYTHONDONTWRITEBYTECODE=1 FLASK_RUN_HOST=127.0.0.1 FLASK_RUN_PORT=${apiPort} ${shellQuote(pythonBin)} ../run.py`,
      port: apiPort,
      reuseExistingServer: !process.env.CI,
      cwd: import.meta.dirname,
    },
    {
      command: `TESTING=1 API_BASE_URL=${apiBaseUrl} npx nuxt build && API_BASE_URL=${apiBaseUrl} npx nuxt preview --port ${webPort}`,
      port: webPort,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      cwd: import.meta.dirname,
    },
  ],
})
