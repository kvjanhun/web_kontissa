import { test, expect } from './fixtures/base.js'

test.describe('Dog Show Browser', () => {
  test('dog page loads with heading and tabs', async ({ page }) => {
    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows: [
            {
              id: 14042,
              date: '14.06.',
              name: 'Basenji',
              month: 'kesäkuu 2026',
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042',
            },
          ],
          index: {
            indexed_show_count: 0,
            total_show_count: 1,
            last_updated: null,
            last_updated_iso: null,
          },
        }),
      })
    })

    await page.goto('/dog')

    await expect(page.locator('h1:has-text("Näyttelytulokset")')).toBeVisible({ timeout: 10000 })

    const showsTab = page.getByRole('button', { name: 'Näyttelyt', exact: true })
    const searchTab = page.getByRole('button', { name: 'Hae rotua', exact: true })
    await expect(showsTab).toBeVisible()
    await expect(searchTab).toBeVisible()
    await expect(page.getByRole('button', { name: /Basenji/ })).toBeVisible()
  })
})
