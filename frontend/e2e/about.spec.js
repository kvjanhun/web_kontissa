import { test, expect } from './fixtures/base.js'

test.describe('About page', () => {
  test('loads sections without flashing error', async ({ page }) => {
    await page.goto('/about')

    // Error message should never be visible
    await expect(page.locator('text=loadError')).not.toBeVisible()
    await expect(page.locator('.text-red-500')).not.toBeVisible()

    // Seeded sections should render
    await expect(page.locator('blockquote', { hasText: 'Hello world' })).toBeVisible()
    await expect(page.locator('h2', { hasText: 'Currently' })).toBeVisible()
    await expect(page.locator('h2', { hasText: 'Skills' })).toBeVisible()
  })

  test('renders quote section content', async ({ page }) => {
    await page.goto('/about')
    const quote = page.locator('#welcome blockquote')
    await expect(quote).toHaveText('Hello world')
  })

  test('renders currently section with label:value items', async ({ page }) => {
    await page.goto('/about')
    const section = page.locator('#currently')
    await expect(section.locator('text=Status')).toBeVisible()
    await expect(section.locator('text=Testing')).toBeVisible()
    await expect(section.locator('text=Mood')).toBeVisible()
    await expect(section.locator('text=Focused')).toBeVisible()
  })

  test('renders pills section with skill items', async ({ page }) => {
    await page.goto('/about')
    const section = page.locator('#skills')
    await expect(section.locator('.pill', { hasText: 'Python' })).toBeVisible()
    await expect(section.locator('.pill', { hasText: 'JavaScript' })).toBeVisible()
    await expect(section.locator('.pill', { hasText: 'Vue' })).toBeVisible()
  })
})
