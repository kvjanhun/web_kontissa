import { test, expect } from './fixtures/auth.js'

test.describe('Admin Dashboard', () => {
  test('non-admin redirected from admin page', async ({ authenticatedPage }) => {
    // Regular user is already logged in and on /about
    // Navigate to /admin via the address bar — full page load triggers guard
    // Since auth state is already populated, the guard should redirect
    await authenticatedPage.goto('/admin')
    await expect(authenticatedPage).toHaveURL('/login', { timeout: 10000 })
  })

  test('admin can access admin page', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await expect(adminPage).toHaveURL('/admin', { timeout: 10000 })
  })

  test('admin sees all tabs', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await expect(adminPage).toHaveURL('/admin', { timeout: 10000 })

    await expect(adminPage.locator('button').filter({ hasText: /Sections|Osiot/ })).toBeVisible()
    await expect(adminPage.locator('button').filter({ hasText: /Analytics|Analytiikka/ })).toBeVisible()
    await expect(adminPage.locator('button').filter({ hasText: /Recipes|Reseptit/ })).toBeVisible()
    await expect(adminPage.locator('button').filter({ hasText: /Health|Terveys/ })).toBeVisible()
    await expect(adminPage.locator('button').filter({ hasText: 'Sanakenno' })).toBeVisible()
  })

  test('sections tab shows seeded sections', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await expect(adminPage).toHaveURL('/admin', { timeout: 10000 })
    await expect(adminPage.locator('text=Welcome').first()).toBeVisible({ timeout: 10000 })
  })

  test('can switch between tabs', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await expect(adminPage).toHaveURL('/admin', { timeout: 10000 })

    await adminPage.locator('button').filter({ hasText: /Health|Terveys/ }).click()
    // Health tab shows Python version string like "3.13.x (default, ...)"
    await expect(adminPage.locator('text=/\\d\\.\\d+\\.\\d+.*default/')).toBeVisible({ timeout: 10000 })
  })
})
