import { test as base } from './base.js'

// Must match scripts/seed_e2e.py credentials
const ADMIN_EMAIL = 'admin@test.com'
const ADMIN_PASSWORD = 'adminpass123'
const USER_EMAIL = 'user@test.com'
const USER_PASSWORD = 'userpass123'

async function loginViaAPI(page, email, password) {
  const resp = await page.request.post('/api/login', {
    data: { email, password },
  })
  if (!resp.ok()) {
    throw new Error(`Login failed for ${email}: ${resp.status()}`)
  }
}

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    await loginViaAPI(page, USER_EMAIL, USER_PASSWORD)
    await use(page)
  },
  adminPage: async ({ page }, use) => {
    await loginViaAPI(page, ADMIN_EMAIL, ADMIN_PASSWORD)
    await use(page)
  },
})

export { expect } from '@playwright/test'
