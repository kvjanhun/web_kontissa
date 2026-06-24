import { test, expect } from './fixtures/base.js'

test.describe('Homepage', () => {
  test('shows the hero, work, stack and terminal sections', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Selected projects/i })).toBeVisible()
    await expect(page.getByRole('heading', { name: /The stack/i })).toBeVisible()
    // Stack layers rendered from the locale array
    await expect(page.getByText('Bare metal', { exact: true })).toBeVisible()
    // Interactive terminal frame
    await expect(page.getByText('konsta@erez.ac', { exact: false }).first()).toBeVisible({ timeout: 10000 })
  })

  test('expands a collapsed project on click', async ({ page }) => {
    await page.goto('/')
    const tool = page.getByRole('button', { name: /Sanakenno Admin tools/ })
    await expect(tool).toHaveAttribute('aria-expanded', 'false')
    await tool.click()
    await expect(tool).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByText('A custom-made admin suite', { exact: false })).toBeVisible()
  })

  test('language toggle switches copy EN <-> FI', async ({ page }) => {
    await page.goto('/')
    const h1 = page.getByRole('heading', { level: 1 })
    await expect(h1).toContainText('From the silicon up')
    await page.getByRole('button', { name: 'Switch language' }).click()
    await expect(h1).toContainText('Raudasta ulkoasuun')
  })

  test('theme toggle flips the dark class on <html>', async ({ page }) => {
    await page.goto('/')
    const html = page.locator('html')
    const wasDark = ((await html.getAttribute('class')) || '').includes('dark')
    await page.getByRole('button', { name: /Switch to (light|dark) mode/ }).click()
    if (wasDark) {
      await expect(html).not.toHaveClass(/dark/)
    } else {
      await expect(html).toHaveClass(/dark/)
    }
  })

  test('footer links to GitHub and sanakenno.fi', async ({ page }) => {
    await page.goto('/')
    const footer = page.locator('footer')
    await expect(footer.getByRole('link', { name: /GitHub/ })).toHaveAttribute('href', 'https://github.com/kvjanhun')
    await expect(footer.getByRole('link', { name: /sanakenno\.fi/ })).toHaveAttribute('href', 'https://sanakenno.fi')
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
