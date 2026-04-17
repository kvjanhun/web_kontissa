import { test, expect } from './fixtures/base.js'

test.describe('Homepage', () => {
  test('shows ASCII banner and interactive terminal', async ({ page }) => {
    await page.goto('/')
    // ASCII banner has aria-label "erez.ac"
    await expect(page.getByLabel('erez.ac')).toBeVisible()
    // Interactive terminal prompt should appear
    await expect(page.locator('text=konsta@erez.ac')).toBeVisible({ timeout: 10000 })
  })

  test('shows the info cards', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('// whoami', { exact: true })).toBeVisible()
    await expect(page.getByText('// stack', { exact: true })).toBeVisible()
    await expect(page.getByText('// projects', { exact: true })).toBeVisible()
    await expect(page.getByText('// ping', { exact: true })).toBeVisible()
  })

  test('has correct page title', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/erez\.ac/)
  })

  test('redirects /about to /', async ({ page }) => {
    await page.goto('/about')
    await expect(page).toHaveURL('/')
  })

  test('redirects /contact to /', async ({ page }) => {
    await page.goto('/contact')
    await expect(page).toHaveURL('/')
  })
})
