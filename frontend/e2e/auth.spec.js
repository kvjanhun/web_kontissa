import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('shows login form when not authenticated', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('input#email')).toBeVisible()
    await expect(page.locator('input#password')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('shows error on invalid credentials', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input#email', 'wrong@test.com')
    await page.fill('input#password', 'wrongpass')
    await page.click('button[type="submit"]')
    await expect(page.locator('[role="alert"]')).toBeVisible()
  })

  test('login succeeds and redirects to about', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input#email', 'user@test.com')
    await page.fill('input#password', 'userpass123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/about', { timeout: 10000 })
  })

  test('logout returns to home', async ({ page }) => {
    // Login via API to skip the form
    await page.request.post('/api/login', {
      data: { email: 'user@test.com', password: 'userpass123' },
    })

    // Visit login page — should show logged-in state
    await page.goto('/login')
    await expect(page.locator('text=testuser')).toBeVisible({ timeout: 10000 })

    // Click logout button
    const logoutButton = page.locator('button').filter({ hasText: /log|kirjaudu/i })
    await logoutButton.click()
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })
})
