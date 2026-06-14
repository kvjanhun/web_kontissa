import { test, expect } from './fixtures/base.js'

test.describe('Dog Show Browser', () => {
  test('dog page loads with heading and tabs', async ({ page }) => {
    // Navigate to /dog
    await page.goto('/dog')

    // The heading "Näyttelytulokset" should be visible
    await expect(page.locator('h1:has-text("Näyttelytulokset")')).toBeVisible({ timeout: 10000 })

    // Check that we have tabs: "Näyttelyt" and "Hae rotua"
    const showsTab = page.getByRole('button', { name: 'Näyttelyt', exact: true })
    const searchTab = page.getByRole('button', { name: 'Hae rotua', exact: true })
    await expect(showsTab).toBeVisible()
    await expect(searchTab).toBeVisible()
  })
})
