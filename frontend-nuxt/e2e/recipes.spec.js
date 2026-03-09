import { test, expect } from './fixtures/auth.js'

test.describe('Recipes', () => {
  test('redirects to login when not authenticated', async ({ page }) => {
    await page.goto('/recipes')
    await expect(page).toHaveURL('/login')
  })

  test('shows recipe list when authenticated', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/recipes')
    await expect(authenticatedPage).toHaveURL('/recipes')
    // Should see the seeded recipe
    await expect(authenticatedPage.locator('text=Test Pancakes')).toBeVisible({ timeout: 10000 })
  })

  test('can view recipe detail', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/recipes')
    await expect(authenticatedPage.locator('text=Test Pancakes')).toBeVisible({ timeout: 10000 })
    await authenticatedPage.click('text=Test Pancakes')
    await expect(authenticatedPage).toHaveURL('/recipes/test-pancakes')
    await expect(authenticatedPage.locator('text=Flour')).toBeVisible({ timeout: 10000 })
    await expect(authenticatedPage.locator('text=Mix ingredients')).toBeVisible()
  })

  test('can navigate to new recipe form', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/recipes/new')
    await expect(authenticatedPage).toHaveURL('/recipes/new')
  })
})
