import { test, expect } from './fixtures/base.js'

test.describe('Dog Show Browser', () => {
  test.use({
    viewport: { width: 390, height: 844 },
  })

  test('dog page loads with heading and merged search', async ({ page }) => {
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
              stats: {
                indexed: true,
                breed_count: 2,
                entry_count: 90,
                result_count: 12,
                is_live: true,
                show_state: 'live',
              },
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
    await page.route('**/api/dog/search**', async route => {
      await new Promise(resolve => setTimeout(resolve, 500))
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          query: 'paula',
          results: [
            {
              show: {
                id: 14042,
                date: '14.06.',
                name: 'Basenji',
                month: 'kesäkuu 2026',
                source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042',
                stats: {
                  indexed: true,
                  breed_count: 2,
                  entry_count: 90,
                  result_count: 12,
                  is_live: true,
                  show_state: 'live',
                },
              },
              breed: null,
              match: 'judge',
              judge: 'Paula Steele',
              judge_match_count: 2,
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

    await page.goto('/dog')

    await expect(page.locator('h1:has-text("Näyttelytulokset")')).toBeVisible({ timeout: 10000 })

    const searchInput = page.getByPlaceholder('Hae näyttelyä, rotua tai tuomaria...')
    await expect(searchInput).toBeVisible()
    await expect(page.getByRole('button', { name: 'Hae rotua', exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Basenji/ })).toBeVisible()
    await expect(page.getByText('2 rotua')).toBeVisible()
    await expect(page.getByText('Käynnissä')).toBeVisible()
    await expect(page.getByText('12/90 tulosta')).toBeVisible()
    await expect(page.getByText('90 koiraa')).toHaveCount(0)
    await expect(page.getByText('1 tulosrotu')).toHaveCount(0)

    await searchInput.fill('paula')
    await expect(page.getByText('Haetaan...')).toBeVisible()
    await expect(page.getByRole('button', { name: /Paula Steele/ })).toHaveCount(1)
    await expect(page.getByText('Paula Steele')).toBeVisible()
    await expect(page.getByText('14.06.2026')).toBeVisible()

    await page.getByRole('button', { name: 'Tyhjennä haku' }).click()
    await expect(searchInput).toHaveValue('')
    await expect(page.getByRole('button', { name: /Paula Steele/ })).toHaveCount(0)
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
              stats: {
                indexed: true,
                breed_count: 2,
                entry_count: 4,
                result_breed_count: 1,
                is_live: true,
                show_state: 'live',
              },
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
          title: 'Basenji Show 2026 erittäin pitkä näyttelyn nimi joka tarvitsee katkaisun mobiilissa',
          breeds: [
            {
              name: 'Basenji',
              count: 3,
              group: '6',
              breed_id: '123',
              has_results: true,
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042&R=6&RO=123',
            },
            {
              name: 'Akita',
              count: 1,
              group: '5',
              breed_id: '10',
              has_results: false,
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042&R=5&RO=10',
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
    await expect(page.locator('.dog-back-link span').filter({ hasText: 'Näyttelyt' })).toBeVisible()
    await expect(page.locator('.dog-top-title')).toHaveCSS('text-overflow', 'ellipsis')
    await expect(page.getByPlaceholder('Hae rotua tai tuomaria...')).toBeVisible()
    await expect(page.getByText('Akita')).toBeVisible()
    const resultBreedsOnly = page.getByRole('checkbox', { name: 'Tuloksia saaneet' })
    await expect(resultBreedsOnly).toBeVisible()
    await resultBreedsOnly.check()
    await expect(page.getByText('Akita')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Basenji 3 koiraa/ })).toBeVisible()
    await resultBreedsOnly.uncheck()
    await expect(page.getByText('Akita')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Suodata koko näyttelyä' })).toBeVisible()

    await page.getByRole('button', { name: /Basenji 3 koiraa/ }).click()
    await expect(page).toHaveURL(/\/dog\?show=14042&group=6&breed=123$/)
    await expect(page.getByText('Testituomari')).toBeVisible()

    await page.goBack()
    await expect(page).toHaveURL(/\/dog\?show=14042$/)
    await expect(page.getByPlaceholder('Hae rotua tai tuomaria...')).toBeVisible()
    await expect(page.getByText('Testituomari')).toHaveCount(0)

    await page.goBack()
    await expect(page).toHaveURL(/\/dog$/)
    await expect(page.getByPlaceholder('Hae näyttelyä, rotua tai tuomaria...')).toBeVisible()
  })

  test('show links open the breed list from the top of the page', async ({ page }) => {
    const shows = Array.from({ length: 35 }, (_, index) => ({
      id: index === 34 ? 14042 : 13000 + index,
      date: `${String(index + 1).padStart(2, '0')}.06.`,
      name: index === 34 ? 'Target Basenji Show' : `Scroll Test Show ${index + 1}`,
      month: 'Tänään',
      source_url: `https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=${index === 34 ? 14042 : 13000 + index}`,
    }))

    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows,
          index: {
            indexed_show_count: 1,
            total_show_count: shows.length,
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
          title: 'Target Basenji Show',
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

    await page.goto('/dog')
    const targetShow = page.getByRole('button', { name: /Target Basenji Show/ })
    await targetShow.scrollIntoViewIfNeeded()
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(100)

    await targetShow.click()

    await expect(page).toHaveURL(/\/dog\?show=14042$/)
    await expect(page.getByPlaceholder('Hae rotua tai tuomaria...')).toBeVisible()
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeLessThan(5)
  })

  test('show-wide results can be searched and filtered by rank without selecting a breed', async ({ page }) => {
    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows: [
            {
              id: 14042,
              date: '14.06.',
              name: 'Basenji Show',
              month: 'kesäkuu 2026',
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042',
            },
          ],
          index: {
            indexed_show_count: 1,
            total_show_count: 1,
            last_updated: null,
            last_updated_iso: null,
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

    await page.route('**/api/dog/shows/14042/all-results', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          show_id: 14042,
          results: [
            {
              number: 1,
              name: 'Aamun Tähti',
              reg_url: '',
              grade: 'ERI',
              placement: 1,
              awards: '',
              critique: 'Hieno basenji',
              gender: 'uros',
              class_name: 'JUN',
              breedName: 'Basenji',
              breedGroup: '6',
              breedId: '123',
              breedObj: {
                name: 'Basenji',
                count: 3,
                group: '6',
                breed_id: '123',
                has_results: true,
              },
            },
            {
              number: 2,
              name: 'Iltatähti',
              reg_url: '',
              grade: 'EH',
              placement: 2,
              awards: '',
              critique: '',
              gender: 'narttu',
              class_name: 'NUO',
              breedName: 'Basenji',
              breedGroup: '6',
              breedId: '123',
              breedObj: {
                name: 'Basenji',
                count: 3,
                group: '6',
                breed_id: '123',
                has_results: true,
              },
            },
          ],
          fetched_at: 1781431200,
          fetched_at_iso: '2026-06-14T10:00:00Z',
        }),
      })
    })

    await page.goto('/dog')
    await page.getByRole('button', { name: /Basenji Show/ }).click()
    await expect(page.getByPlaceholder('Hae rotua tai tuomaria...')).toBeVisible()

    // Open whole-show filter panel
    await page.getByRole('button', { name: 'Suodata koko näyttelyä' }).click()

    // Check that one combined search/filter panel remains and breed groups expand on demand
    await expect(page.getByRole('button', { name: 'Suodata koko näyttelyä' })).toHaveCount(0)
    await expect(page.getByPlaceholder('Hae rotua, tuomaria tai koiraa...')).toBeVisible()
    await expect(page.getByText('Aamun Tähti')).toHaveCount(0)
    await page.getByRole('button', { name: /Basenji/ }).click()
    await expect(page.getByText('Aamun Tähti')).toBeVisible()
    await expect(page.getByText('Iltatähti')).toBeVisible()

    // Filter by grade 'ERI'
    await page.locator('select').first().selectOption('eri')

    // Aamun Tähti (ERI) should be visible, Iltatähti (EH) should be hidden
    await expect(page.getByText('Aamun Tähti')).toBeVisible()
    await expect(page.getByText('Iltatähti')).not.toBeVisible()

    // Search text for 'Aamun'
    await page.getByPlaceholder('Hae rotua, tuomaria tai koiraa...').fill('Aamun')
    await expect(page.getByText('Aamun Tähti')).toBeVisible()

    // Non-matching search
    const showSearchInput = page.getByPlaceholder('Hae rotua, tuomaria tai koiraa...')
    await showSearchInput.fill('Mustikki')
    await expect(page.getByText('Aamun Tähti')).not.toBeVisible()

    await page.getByRole('button', { name: 'Tyhjennä haku' }).click()
    await expect(showSearchInput).toHaveValue('')
    await expect(page.getByText('Aamun Tähti')).toBeVisible()
  })

  test('future shows explain that whole-show results are not checked yet', async ({ page }) => {
    let allResultsCalled = false

    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows: [
            {
              id: 15001,
              date: '20.06.',
              name: 'Future Basenji Show',
              month: 'kesäkuu 2999',
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=15001',
              stats: {
                indexed: true,
                breed_count: 1,
                entry_count: 4,
                result_breed_count: 0,
                show_state: 'upcoming',
                is_live: false,
              },
            },
          ],
          index: {
            indexed_show_count: 1,
            total_show_count: 1,
            last_updated: null,
            last_updated_iso: null,
          },
        }),
      })
    })

    await page.route('**/api/dog/shows/15001', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          id: 15001,
          title: 'Future Basenji Show 2999',
          date: '20.06.',
          month: 'kesäkuu 2999',
          breeds: [
            {
              name: 'Basenji',
              count: 4,
              group: '6',
              breed_id: '123',
              has_results: false,
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=15001&R=6&RO=123',
            },
          ],
          source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=15001',
          fetched_at: 1781431200,
          fetched_at_iso: '2026-06-14T10:00:00Z',
        }),
      })
    })

    await page.route('**/api/dog/shows/15001/all-results', async route => {
      allResultsCalled = true
      await route.fulfill({
        status: 425,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'not_ready' }),
      })
    })

    await page.goto('/dog')
    await page.getByRole('button', { name: /kesäkuu 2999/ }).click()
    await page.getByRole('button', { name: /Future Basenji Show/ }).click()

    await expect(page.getByText('Tuloksia ei haeta vielä')).toBeVisible()
    await expect(page.getByText(/aikaisintaan näyttelypäivänä klo 6/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Suodata koko näyttelyä' })).toHaveCount(0)
    expect(allResultsCalled).toBe(false)
  })
})
