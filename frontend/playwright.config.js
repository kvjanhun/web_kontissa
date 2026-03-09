import { defineConfig } from '@playwright/test'
import { resolve } from 'path'

const dbPath = resolve(import.meta.dirname, '..', 'app', 'data', 'test-e2e.db')

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
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
      command: `DATABASE_URI="sqlite:///${dbPath}" TESTING=1 python3 ../run.py`,
      port: 5001,
      reuseExistingServer: !process.env.CI,
      cwd: import.meta.dirname,
    },
    {
      command: 'TESTING=1 npx nuxt build && npx nuxt preview --port 3000',
      port: 3000,
      reuseExistingServer: !process.env.CI,
      cwd: import.meta.dirname,
    },
  ],
})
