import { test, expect } from './fixtures/base.js'

test.describe('Homepage', () => {
  test('loads and shows heading and terminal', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('Konsta Janhunen')
    // Terminal window should be present
    await expect(page.locator('text=konsta@erez.ac')).toBeVisible({ timeout: 10000 })
  })

  test('has navigation links', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('a[href="/about"]').first()).toBeVisible()
    await expect(page.locator('a[href="/contact"]').first()).toBeVisible()
  })

  test('has correct page title', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/erez\.ac/)
  })
})
