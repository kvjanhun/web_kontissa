import { test, expect } from './fixtures/base.js'

test.describe('404 Page', () => {
  test('shows 404 for nonexistent route', async ({ page }) => {
    await page.goto('/nonexistent-page-xyz')
    await expect(page.locator('h1')).toContainText('404')
  })

  test('has link back to home', async ({ page }) => {
    await page.goto('/nonexistent-page-xyz')
    // Use the specific "Back to home" / "Takaisin" link, not the nav logo
    const homeLink = page.locator('a[href="/"].bg-accent')
    await expect(homeLink).toBeVisible()
  })

  test('is marked noindex', async ({ page }) => {
    // The HTTP 404 status is served by Flask, which these specs bypass (they run
    // against `nuxt preview`), so it's asserted in tests/test_core_routes.py instead.
    // What this can check is that the page itself asks not to be indexed.
    await page.goto('/nonexistent-page-xyz')
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex')
  })
})
