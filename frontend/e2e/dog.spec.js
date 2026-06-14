import { test, expect } from './fixtures/base.js'

test.describe('Dog Show Browser', () => {
  test.use({
    viewport: { width: 390, height: 844 },
  })

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

  test('browser back restores the previous dog page view', async ({ page }) => {
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
            indexed_show_count: 1,
            total_show_count: 1,
            last_updated: 1781431200,
            last_updated_iso: '2026-06-14T10:00:00Z',
          },
        }),
      })
    })

    await page.route('**/api/dog/shows/14042', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          id: 14042,
          title: 'Basenji Show 2026',
          breeds: [
            {
              name: 'Basenji',
              count: 3,
              group: '6',
              breed_id: '123',
              has_results: true,
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042&R=6&RO=123',
            },
          ],
          source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042',
          fetched_at: 1781431200,
          fetched_at_iso: '2026-06-14T10:00:00Z',
        }),
      })
    })

    await page.route('**/api/dog/shows/14042/results**', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          show_id: 14042,
          title: 'Basenji Show 2026',
          breed: 'Basenji',
          judge: 'Testituomari',
          awards: [],
          results: [
            {
              number: 1,
              name: 'Aamun Tähti',
              reg_url: '',
              grade: 'ERI',
              placement: 1,
              awards: '',
              critique: '',
              gender: 'uros',
              class_name: 'JUN',
            },
          ],
          source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042&R=6&RO=123',
          fetched_at: 1781431200,
          fetched_at_iso: '2026-06-14T10:00:00Z',
        }),
      })
    })

    await page.goto('/dog')

    await page.getByRole('button', { name: /Basenji/ }).click()
    await expect(page).toHaveURL(/\/dog\?show=14042$/)
    await expect(page.getByRole('checkbox', { name: 'Vain tuloksia' })).toBeVisible()

    await page.getByRole('button', { name: /Basenji 3 koiraa/ }).click()
    await expect(page).toHaveURL(/\/dog\?show=14042&group=6&breed=123$/)
    await expect(page.getByText('Testituomari')).toBeVisible()

    await page.goBack()
    await expect(page).toHaveURL(/\/dog\?show=14042$/)
    await expect(page.getByRole('checkbox', { name: 'Vain tuloksia' })).toBeVisible()
    await expect(page.getByText('Testituomari')).toHaveCount(0)

    await page.goBack()
    await expect(page).toHaveURL(/\/dog$/)
    await expect(page.getByRole('button', { name: 'Näyttelyt', exact: true })).toBeVisible()
  })
})
