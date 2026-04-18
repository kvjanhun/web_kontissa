import { test, expect } from './fixtures/base.js'

test.describe('Homepage', () => {
  test('shows ASCII banner and interactive terminal', async ({ page }) => {
    await page.goto('/')
    // ASCII banner has aria-label "erez.ac"
    await expect(page.getByLabel('erez.ac', { exact: true })).toBeVisible()
    // Interactive terminal prompt should appear
    await expect(page.locator('text=konsta@erez.ac')).toBeVisible({ timeout: 10000 })
  })

  test('shows the info cards and project gallery', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('// whoami', { exact: true })).toBeVisible()
    await expect(page.getByText('// projects', { exact: true })).toBeVisible()
    await expect(page.getByText('// ping', { exact: true })).toBeVisible()
    await expect(page.getByText('// gallery', { exact: true })).toBeVisible()
  })

  test('gallery switches highlighted project when a thumbnail is clicked', async ({ page }) => {
    await page.goto('/')
    const gallery = page.getByRole('region', { name: 'Project gallery' })
    await expect(gallery.getByRole('heading', { name: 'Sanakenno' })).toBeVisible()
    await gallery.getByRole('tab', { name: 'erez.ac admin' }).click()
    await expect(gallery.getByRole('heading', { name: 'erez.ac admin' })).toBeVisible()
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
