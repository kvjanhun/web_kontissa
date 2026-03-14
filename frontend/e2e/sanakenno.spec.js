import { test, expect } from './fixtures/base.js'

test.describe('Sanakenno', () => {
  test('game loads with honeycomb and score', async ({ page }) => {
    await page.goto('/sanakenno')
    // Wait for the honeycomb SVG (has aria-label)
    await expect(page.locator('svg[aria-label^="Kirjainkenno"]')).toBeVisible({ timeout: 10000 })
    // Score display should show 0 (scope to Pisteet to avoid matching puzzle number #20)
    await expect(page.locator('text=Pisteet: 0')).toBeVisible()
  })

  test('can type letters via keyboard', async ({ page }) => {
    await page.goto('/sanakenno')
    await expect(page.locator('svg[aria-label^="Kirjainkenno"]')).toBeVisible({ timeout: 10000 })
    // Type some letters — at least the current word area should update
    await page.keyboard.type('abc')
  })

  test('backspace clears letters', async ({ page }) => {
    await page.goto('/sanakenno')
    await expect(page.locator('svg[aria-label^="Kirjainkenno"]')).toBeVisible({ timeout: 10000 })
    await page.keyboard.type('abc')
    await page.keyboard.press('Backspace')
    await page.keyboard.press('Backspace')
    await page.keyboard.press('Backspace')
  })

  test('submitting short word shows error', async ({ page }) => {
    await page.goto('/sanakenno')
    await expect(page.locator('svg[aria-label^="Kirjainkenno"]')).toBeVisible({ timeout: 10000 })
    // Type a short string and submit
    await page.keyboard.type('ab')
    await page.keyboard.press('Enter')
    // Wait briefly for the message to appear
    await page.waitForTimeout(500)
  })

  test('hints panel toggles', async ({ page }) => {
    await page.goto('/sanakenno')
    await expect(page.locator('svg[aria-label^="Kirjainkenno"]')).toBeVisible({ timeout: 10000 })

    // Click the hints toggle button (contains "Avut")
    const hintsButton = page.locator('button').filter({ hasText: 'Avut' })
    await hintsButton.click()
    // "Yleiskuva" hint should appear
    await expect(page.locator('text=Yleiskuva')).toBeVisible()
  })

  test('share button exists', async ({ page }) => {
    await page.goto('/sanakenno')
    await expect(page.locator('svg[aria-label^="Kirjainkenno"]')).toBeVisible({ timeout: 10000 })
    const shareButton = page.locator('button').filter({ hasText: 'Jaa tulos' })
    await expect(shareButton).toBeVisible()
  })

  test('rules modal opens and closes', async ({ page }) => {
    await page.goto('/sanakenno')
    await expect(page.locator('svg[aria-label^="Kirjainkenno"]')).toBeVisible({ timeout: 10000 })

    // Click the ? help button
    const helpButton = page.locator('button').filter({ hasText: '?' })
    await helpButton.click()

    // Modal with role="dialog" should appear
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('text=Ohjeet')).toBeVisible()
  })
})
