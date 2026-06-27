import { test, expect } from './fixtures/auth.js'

test.describe('Admin', () => {
  test('non-admin redirected from admin page', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/admin')
    await expect(authenticatedPage).toHaveURL('/login', { timeout: 10000 })
  })

  test('admin can access admin page', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await expect(adminPage).toHaveURL('/admin', { timeout: 10000 })
  })

  test('sidebar shows all sections', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    const nav = adminPage.locator('.as-nav')
    for (const label of ['Dashboard', 'Home content', 'Projects', 'Recipes', 'Analytics', 'Server health']) {
      await expect(nav.getByRole('button', { name: label })).toBeVisible({ timeout: 10000 })
    }
  })

  test('dashboard links to Grafana', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await expect(adminPage.getByRole('link', { name: /Grafana/ })).toHaveAttribute('href', '/logs/')
  })

  test('projects section lists the seeded project', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await adminPage.locator('.as-nav').getByRole('button', { name: 'Projects' }).click()
    await expect(adminPage.getByText('Sanakenno', { exact: true }).first()).toBeVisible({ timeout: 10000 })
  })

  test('home content section shows the Hero group', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await adminPage.locator('.as-nav').getByRole('button', { name: 'Home content' }).click()
    await expect(adminPage.getByRole('heading', { name: 'Hero' })).toBeVisible({ timeout: 10000 })
  })

  test('server health section loads', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await adminPage.locator('.as-nav').getByRole('button', { name: 'Server health' }).click()
    await expect(adminPage.getByText('Python', { exact: true })).toBeVisible({ timeout: 10000 })
  })

  test('editing the intro text is reflected on the home page', async ({ adminPage }) => {
    await adminPage.goto('/admin')
    await adminPage.locator('.as-nav').getByRole('button', { name: 'Home content' }).click()

    // Groups start collapsed — open Hero to reach its fields.
    await adminPage.getByRole('button', { name: 'Hero', exact: true }).click()

    const heroCard = adminPage.locator('.group', { hasText: 'Hero' })
    const intro = heroCard.locator('.field', { hasText: 'Intro paragraph' }).locator('textarea')
    await expect(intro).toBeVisible({ timeout: 10000 })
    // The editor loads its fields async on mount — wait for that to land, otherwise
    // a fill() can be clobbered when the fetch resolves.
    await expect(intro).not.toHaveValue('', { timeout: 10000 })
    const original = await intro.inputValue()
    const marker = `E2E intro marker ${Date.now()}`

    await intro.fill(marker)
    await expect(adminPage.getByText(/unsaved change/)).toBeVisible({ timeout: 5000 })
    await adminPage.getByRole('button', { name: /Save changes/ }).click()
    await expect(adminPage.getByRole('status')).toContainText('Saved', { timeout: 10000 })

    // The home page (which fetches /api/home-content) now shows the edited copy.
    await adminPage.goto('/')
    await expect(adminPage.getByText(marker)).toBeVisible({ timeout: 10000 })

    // Restore via the API so the change does not leak into other specs.
    const restore = await adminPage.request.put('/api/admin/home-content', {
      data: { key: 'home.hero.body', locale: 'en', value: original },
    })
    expect(restore.ok()).toBeTruthy()
  })
})
