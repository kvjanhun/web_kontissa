import { test, expect } from './fixtures/base.js'

// /alchemy ships its whole dataset in the bundle, so unlike /dog there is no API
// to stub and nothing to wait on beyond hydration.

test.describe('alchemy recipe list', () => {
  test('renders the recipe list', async ({ page }) => {
    await page.goto('/alchemy')
    await expect(page.getByRole('heading', { name: 'Alchemy', level: 1 })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Saviour Schnapps' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Artemisia' })).toBeVisible()
  })

  test('search narrows the list', async ({ page }) => {
    await page.goto('/alchemy')
    await page.getByPlaceholder('Search recipes or ingredients').fill('schnapps')
    await expect(page.getByRole('heading', { name: 'Saviour Schnapps' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Artemisia' })).toBeHidden()
  })

  test('clicking a base chip drops that base out of the list, not down to it', async ({ page }) => {
    await page.goto('/alchemy')
    // Lullaby is Oil-based; clicking "Oil" toggles it OFF (drops out), so
    // Lullaby disappears while every other base stays visible.
    await page.getByRole('button', { name: 'Oil', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Lullaby' })).toBeHidden()
    await expect(page.getByRole('heading', { name: 'Saviour Schnapps' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Artemisia' })).toBeVisible()
  })

  test('clicking a dropped-out base chip again brings it back', async ({ page }) => {
    await page.goto('/alchemy')
    await page.getByRole('button', { name: 'Oil', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Lullaby' })).toBeHidden()
    await page.getByRole('button', { name: 'Oil', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Lullaby' })).toBeVisible()
  })

  test('"All" restores every base after some have been dropped out', async ({ page }) => {
    await page.goto('/alchemy')
    await page.getByRole('button', { name: 'Oil', exact: true }).click()
    await page.getByRole('button', { name: 'Wine', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Lullaby' })).toBeHidden()
    await expect(page.getByRole('heading', { name: 'Saviour Schnapps' })).toBeHidden()

    await page.getByRole('button', { name: 'All', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Lullaby' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Saviour Schnapps' })).toBeVisible()
  })

  test('opening a recipe shows its ingredients and brewing steps', async ({ page }) => {
    await page.goto('/alchemy')
    await page.getByRole('heading', { name: 'Saviour Schnapps' }).click()
    await expect(page).toHaveURL(/recipe=saviour-schnapps/)
    await expect(page.getByRole('heading', { name: 'Ingredients' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Brewing' })).toBeVisible()
    await expect(page.getByText('Add nettle and boil for 2 turns.')).toBeVisible()
    await page.getByRole('button', { name: 'All recipes' }).click()
    await expect(page.getByRole('heading', { name: 'Artemisia' })).toBeVisible()
  })

  test('a recipe deep link survives a cold load', async ({ page }) => {
    await page.goto('/alchemy?recipe=artemisia')
    await expect(page.getByRole('heading', { name: 'Brewing' })).toBeVisible()
    await expect(page.getByText('Distil into a phial.')).toBeVisible()
  })
})

test.describe('alchemy ingredient matcher', () => {
  test('ticking ingredients reports what they brew', async ({ page }) => {
    await page.goto('/alchemy')
    await page.getByRole('button', { name: 'What can I brew?' }).click()

    await expect(page.getByText('Tick the ingredients in your pack')).toBeVisible()

    await page.getByRole('checkbox', { name: 'Nettle' }).check()
    await page.getByRole('checkbox', { name: 'Marigold' }).check()

    const canBrew = page.locator('.al-card-good')
    await expect(canBrew.getByRole('heading', { name: 'Marigold Decoction' })).toBeVisible()

    // Saviour Schnapps needs nettle + belladonna, so it is exactly one short.
    const oneShort = page.locator('.al-card-short')
    await expect(oneShort.getByRole('heading', { name: 'Saviour Schnapps' })).toBeVisible()
    await expect(oneShort.getByText('Still need: Belladonna')).toBeVisible()
  })

  test('the ingredient search filters the checklist', async ({ page }) => {
    await page.goto('/alchemy?tab=brew')
    await page.getByPlaceholder('Search ingredients').fill('marig')
    await expect(page.getByRole('checkbox', { name: 'Marigold' })).toBeVisible()
    await expect(page.getByRole('checkbox', { name: 'Nettle' })).toBeHidden()
  })

  test('a selection deep link survives a cold load and clears', async ({ page }) => {
    await page.goto('/alchemy?have=marigold,nettle')
    await expect(page.getByRole('checkbox', { name: 'Nettle' })).toBeChecked()
    await expect(page.locator('.al-card-good').getByRole('heading', { name: 'Marigold Decoction' })).toBeVisible()

    await page.getByRole('button', { name: 'Clear' }).click()
    await expect(page.getByText('Tick the ingredients in your pack')).toBeVisible()
  })
})

test('the page is marked noindex while it is unlisted', async ({ page }) => {
  await page.goto('/alchemy')
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex')
})
