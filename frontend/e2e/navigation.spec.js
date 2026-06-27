import { test, expect } from './fixtures/base.js'

test.describe('Navigation', () => {
  test('redirects unauthenticated user from recipes to login', async ({ page }) => {
    await page.goto('/recipes')
    // Bounced to login, carrying the intended path for a post-login return.
    await expect(page).toHaveURL(/\/login\?redirect=/)
  })

  test('redirects unauthenticated user from admin to login', async ({ page }) => {
    await page.goto('/admin')
    await expect(page).toHaveURL(/\/login\?redirect=/)
  })
})
