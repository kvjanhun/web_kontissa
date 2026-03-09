import { test, expect } from '@playwright/test'

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
})
