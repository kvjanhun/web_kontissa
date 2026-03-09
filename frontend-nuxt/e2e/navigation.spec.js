import { test, expect } from './fixtures/base.js'

test.describe('Navigation', () => {
  test('navigates between public pages', async ({ page }) => {
    await page.goto('/')
    await page.click('a[href="/about"]')
    await expect(page).toHaveURL('/about')

    await page.click('a[href="/contact"]')
    await expect(page).toHaveURL('/contact')
  })

  test('redirects unauthenticated user from recipes to login', async ({ page }) => {
    await page.goto('/recipes')
    await expect(page).toHaveURL('/login')
  })

  test('redirects unauthenticated user from admin to login', async ({ page }) => {
    await page.goto('/admin')
    await expect(page).toHaveURL('/login')
  })
})
