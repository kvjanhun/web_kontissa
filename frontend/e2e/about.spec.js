import { test, expect } from './fixtures/base.js'

test.describe('About page', () => {
  test('loads sections without flashing error', async ({ page }) => {
    await page.goto('/about')

    // Error message should never be visible
    await expect(page.locator('text=loadError')).not.toBeVisible()
    await expect(page.locator('.text-red-500')).not.toBeVisible()

    // Hero banner should render
    await expect(page.locator('h1', { hasText: 'Konsta Janhunen' })).toBeVisible()
  })

  test('renders hero banner with tagline', async ({ page }) => {
    await page.goto('/about')
    await expect(page.locator('.hero')).toBeVisible()
    await expect(page.locator('text=Full-Stack Developer')).toBeVisible()
  })

  test('renders currently section with label:value items', async ({ page }) => {
    await page.goto('/about')
    await expect(page.locator('text=Status')).toBeVisible()
    await expect(page.locator('text=Testing')).toBeVisible()
    await expect(page.locator('text=Mood')).toBeVisible()
    await expect(page.locator('text=Focused')).toBeVisible()
  })

  test('renders tech pills', async ({ page }) => {
    await page.goto('/about')
    await expect(page.locator('.tech-pill', { hasText: 'Python' })).toBeVisible()
    await expect(page.locator('.tech-pill', { hasText: 'Vue.js' })).toBeVisible()
  })

  test('renders project items', async ({ page }) => {
    await page.goto('/about')
    await expect(page.locator('text=TestProject')).toBeVisible()
  })
})
