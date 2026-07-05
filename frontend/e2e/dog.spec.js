import { test, expect } from './fixtures/base.js'

// The show list auto-collapses every month section except the current month
// (and the relative "Tänään"/"Tällä viikolla" sections), so fixtures pinned to
// a hard-coded month roll out of view once the calendar passes them and every
// spec that expects an expanded show card starts failing. Anchor the fixtures
// of current/live shows to the real clock instead; specs that exercise the
// collapsed-month behavior keep deliberately non-current months.
const FINNISH_MONTHS = [
  'tammikuu', 'helmikuu', 'maaliskuu', 'huhtikuu', 'toukokuu', 'kesäkuu',
  'heinäkuu', 'elokuu', 'syyskuu', 'lokakuu', 'marraskuu', 'joulukuu',
]
const pad2 = value => String(value).padStart(2, '0')
const TODAY = new Date()
const CURRENT_MONTH_LABEL = `${FINNISH_MONTHS[TODAY.getMonth()]} ${TODAY.getFullYear()}`
const TODAY_DATE = `${pad2(TODAY.getDate())}.${pad2(TODAY.getMonth() + 1)}.`
const TODAY_FULL_DATE = `${TODAY_DATE}${TODAY.getFullYear()}`

// A finished show for specs that exercise the whole-show results flow: on the
// show day itself the affordance label changes ("Tarkista koirat ja tulokset")
// and goes quiet overnight, so those specs need a show in the past. Yesterday
// with an explicit year parses unambiguously even across New Year, and the
// relative "Tällä viikolla" section label is never collapsed or rewritten.
const YESTERDAY = new Date(TODAY.getFullYear(), TODAY.getMonth(), TODAY.getDate() - 1)
const YESTERDAY_FULL_DATE = `${pad2(YESTERDAY.getDate())}.${pad2(YESTERDAY.getMonth() + 1)}.${YESTERDAY.getFullYear()}`

// Two consecutive days in the current month for the multi-day date badge. The
// range must stay inside BOTH the current month (the calendar box only renders a
// same-month range) AND the current "this week left" window, which ends Sunday —
// otherwise the show drops out of the featured "Tällä viikolla" section. Since
// parseShowDate resolves a range to its LATER day, that later day must be ≤ the
// upcoming Sunday. So use today–tomorrow normally, but fall back to yesterday–today
// on the last day of the month or on a Sunday (when tomorrow spills into next week).
const NEXT_DAY = new Date(TODAY.getFullYear(), TODAY.getMonth(), TODAY.getDate() + 1)
const FORWARD_RANGE_OK = NEXT_DAY.getMonth() === TODAY.getMonth() && TODAY.getDay() !== 0
const RANGE_START = FORWARD_RANGE_OK
  ? TODAY
  : new Date(TODAY.getFullYear(), TODAY.getMonth(), TODAY.getDate() - 1)
const RANGE_END = FORWARD_RANGE_OK ? NEXT_DAY : TODAY
const MULTI_DAY_DATE = `${pad2(RANGE_START.getDate())}.-${pad2(RANGE_END.getDate())}.${pad2(TODAY.getMonth() + 1)}.`
const MULTI_DAY_BADGE = `${RANGE_START.getDate()}–${RANGE_END.getDate()}`

// Whole-show results now auto-load the moment a show detail opens. Specs that only
// exercise the breed list (not whole-show filtering) stub /all-results as a slow
// "warming" response: the cache never finishes loading, so the breed-list UI is
// asserted in its unloaded state and the auto-load fetch never reaches the real
// server. retry_after is large so the background poll effectively doesn't re-fire
// during the test.
async function stubWarmingAllResults(page, showId) {
  await page.route(`**/api/dog/shows/${showId}/all-results`, async route => {
    await route.fulfill({
      status: 202,
      contentType: 'application/json',
      body: JSON.stringify({
        show_id: showId,
        status: 'warming',
        retry_after: 120,
        progress: { state: 'queued', total_breeds: 1, fetched_breeds: 0, failed_breeds: 0, total_dogs: 0, percent: 0 },
      }),
    })
  })
}

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
              date: TODAY_DATE,
              name: 'Basenji',
              month: CURRENT_MONTH_LABEL,
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
                date: TODAY_DATE,
                name: 'Basenji',
                month: CURRENT_MONTH_LABEL,
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

    const searchInput = page.getByPlaceholder('Hae näyttelyä, rotua, tuomaria tai koiraa...')
    await expect(searchInput).toBeVisible()
    await expect(page.getByRole('button', { name: 'Hae rotua', exact: true })).toHaveCount(0)
    // A show dated today renders both in "Tällä viikolla" and its month
    // section, so scope the list assertions to the featured section.
    const thisWeek = page.locator('.dog-this-week-section')
    await expect(thisWeek.getByRole('button', { name: /Basenji/ })).toBeVisible()
    await expect(thisWeek.getByText('2 rotua')).toBeVisible()
    await expect(thisWeek.getByText('Käynnissä')).toBeVisible()
    await expect(thisWeek.getByText('12/90 tulosta')).toBeVisible()
    await expect(page.getByText('90 koiraa')).toHaveCount(0)
    await expect(page.getByText('1 tulosrotu')).toHaveCount(0)

    await searchInput.fill('paula')
    await expect(page.getByText('Haetaan...')).toBeVisible()
    await expect(page.getByRole('button', { name: /Paula Steele/ })).toHaveCount(1)
    await expect(page.getByText('Paula Steele')).toBeVisible()
    await expect(page.getByText(TODAY_FULL_DATE)).toBeVisible()

    await page.getByRole('button', { name: 'Tyhjennä haku' }).click()
    await expect(searchInput).toHaveValue('')
    await expect(page.getByRole('button', { name: /Paula Steele/ })).toHaveCount(0)
  })

  test('search surfaces dog-name and owner matches with their own tags', async ({ page }) => {
    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows: [],
          index: { indexed_show_count: 1, total_show_count: 1, last_updated: null, last_updated_iso: null },
        }),
      })
    })
    await page.route('**/api/dog/search**', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          query: 'tähti',
          results: [
            {
              show: { id: 14042, date: YESTERDAY_FULL_DATE, name: 'Näyttely A', month: 'Tällä viikolla' },
              breed: null, match: 'dog', dog: 'Aamun Tähti', dog_match_count: 3,
            },
            {
              show: { id: 15050, date: YESTERDAY_FULL_DATE, name: 'Näyttely B', month: 'Tällä viikolla' },
              breed: null, match: 'owner', owner: 'Tähti Pia', owner_match_count: 4,
            },
          ],
          index: { indexed_show_count: 1, total_show_count: 1, last_updated: null, last_updated_iso: null },
        }),
      })
    })
    await page.route('**/api/dog/shows/14042', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          id: 14042, title: 'Näyttely A', breeds: [], source_url: '',
          fetched_at: 1781431200, fetched_at_iso: '2026-06-14T10:00:00Z',
        }),
      })
    })
    // After navigating into the dog's show, results auto-load — keep it off the real server.
    await stubWarmingAllResults(page, 14042)

    await page.goto('/dog')
    await page.getByPlaceholder('Hae näyttelyä, rotua, tuomaria tai koiraa...').fill('tähti')

    await expect(page.locator('.dog-search-breed-tag', { hasText: 'Koira' })).toBeVisible()
    await expect(page.getByText('Aamun Tähti +2 muuta')).toBeVisible()
    await expect(page.locator('.dog-search-breed-tag', { hasText: 'Omistaja' })).toBeVisible()
    await expect(page.getByText('Tähti Pia · 4 tulosta')).toBeVisible()

    // A dog hit opens its show and pre-fills the whole-show search with the dog name.
    // (The cache stays "warming" here, so the input keeps its unloaded placeholder;
    // assert the value by the input's class rather than the widened placeholder.)
    await page.getByRole('button', { name: /Aamun Tähti/ }).click()
    await expect(page).toHaveURL(/\/dog\?show=14042$/)
    await expect(page.locator('.dog-breed-search .dog-search-input')).toHaveValue('Aamun Tähti')
  })

  test('paused multi-day show shows Jatkuu, today’s results, and a date range', async ({ page }) => {
    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows: [
            {
              id: 13762,
              date: MULTI_DAY_DATE,
              name: 'Turku KV',
              month: CURRENT_MONTH_LABEL,
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=13762',
              stats: {
                indexed: true,
                breed_count: 2,
                entry_count: 90,
                result_count: 12,
                is_live: false,
                is_paused: true,
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

    await page.goto('/dog')

    const thisWeek = page.locator('.dog-this-week-section')
    await expect(thisWeek.getByRole('button', { name: /Turku KV/ })).toBeVisible({ timeout: 10000 })
    await expect(thisWeek.getByText('Jatkuu')).toBeVisible()
    await expect(page.getByText('Käynnissä')).toHaveCount(0)
    await expect(thisWeek.getByText('12/90 tulosta')).toBeVisible()
    // Calendar box renders the multi-day range, not just the first day.
    await expect(thisWeek.getByText(MULTI_DAY_BADGE)).toBeVisible()
  })

  test('browser back restores the previous dog page view', async ({ page }) => {
    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows: [
            {
              id: 14042,
              date: YESTERDAY_FULL_DATE,
              name: 'Basenji',
              month: 'Tällä viikolla',
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042',
              // is_live keeps the "Tuloksia saaneet" breed filter visible while
              // the past show date keeps the whole-show affordance in its
              // settled "Suodata koko näyttelyä" form at any hour.
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

    // Whole-show results now auto-load when the show opens, so this show needs a
    // complete cache to serve instantly.
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
              critique: '',
              gender: 'uros',
              class_name: 'JUN',
              breedName: 'Basenji',
              breedGroup: '6',
              breedId: '123',
              breedObj: { name: 'Basenji', count: 3, group: '6', breed_id: '123', has_results: true },
            },
          ],
          cache: { status: 'complete', stale: false, total_breeds: 1, fetched_breeds: 1, failed_breeds: 0, total_dogs: 1, percent: 100 },
          fetched_at: 1781431200,
          fetched_at_iso: '2026-06-14T10:00:00Z',
        }),
      })
    })

    await page.goto('/dog')

    await page.getByRole('button', { name: /Basenji/ }).click()
    await expect(page).toHaveURL(/\/dog\?show=14042$/)
    // Back-to-list affordance: at this mobile width the label collapses to just
    // the chevron, so assert the button (named via aria-label) and that its
    // text label is hidden rather than expecting the label to be visible.
    await expect(page.getByRole('button', { name: 'Näyttelyt', exact: true })).toBeVisible()
    await expect(page.locator('.dog-back-link span')).toBeHidden()
    // The persistent /dog brand stays visible on the show page.
    await expect(page.getByRole('link', { name: '/dog' })).toBeVisible()
    await expect(page.locator('.dog-top-title')).toHaveCSS('text-overflow', 'ellipsis')
    // Auto-loaded whole-show cache widens the placeholder (no button to click).
    await expect(page.getByPlaceholder('Hae rotua, tuomaria tai koiraa...')).toBeVisible()
    const resultBreedsOnly = page.getByRole('checkbox', { name: 'Tuloksia saaneet' })
    await expect(resultBreedsOnly).toBeVisible()
    await expect(resultBreedsOnly).toBeChecked()
    await expect(page.getByText('Akita')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Basenji 3 koiraa/ })).toBeVisible()
    await resultBreedsOnly.uncheck()
    await expect(page.getByText('Akita')).toBeVisible()
    await resultBreedsOnly.check()
    await expect(page.getByText('Akita')).toHaveCount(0)

    // With the cache loaded, a breed group expands in place; its "Rotutulokset"
    // link is what now opens the single-breed page.
    await page.getByRole('button', { name: /Basenji 3 koiraa/ }).click()
    await page.getByRole('button', { name: 'Rotutulokset' }).click()
    await expect(page).toHaveURL(/\/dog\?show=14042&group=6&breed=123$/)
    await expect(page.getByText('Testituomari')).toBeVisible()

    await page.goBack()
    await expect(page).toHaveURL(/\/dog\?show=14042$/)
    await expect(page.getByPlaceholder('Hae rotua, tuomaria tai koiraa...')).toBeVisible()
    await expect(page.getByText('Testituomari')).toHaveCount(0)

    await page.goBack()
    await expect(page).toHaveURL(/\/dog$/)
    await expect(page.getByPlaceholder('Hae näyttelyä, rotua, tuomaria tai koiraa...')).toBeVisible()
  })

  test('show links open the breed list from the top of the page', async ({ page }) => {
    const shows = Array.from({ length: 35 }, (_, index) => ({
      id: index === 34 ? 14042 : 13000 + index,
      date: TODAY_DATE,
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

    await stubWarmingAllResults(page, 14042)

    await page.goto('/dog')
    // Today-dated shows are duplicated into "Tällä viikolla"; target the month
    // section further down the page to keep the scroll distance meaningful.
    const targetShow = page.locator('.dog-month-group').getByRole('button', { name: /Target Basenji Show/ })
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
              date: YESTERDAY_FULL_DATE,
              name: 'Basenji Show',
              month: 'Tällä viikolla',
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

    // Whole-show results auto-load on open — there is no button to click. Once the
    // cache is loaded the widened search placeholder appears and breed groups
    // expand on demand.
    await expect(page.getByRole('button', { name: 'Suodata koko näyttelyä' })).toHaveCount(0)
    await expect(page.getByPlaceholder('Hae rotua, tuomaria tai koiraa...')).toBeVisible()
    await expect(page.getByText('Aamun Tähti')).toHaveCount(0)
    // With every breed group collapsed there is nothing on screen to expand.
    await expect(page.getByRole('button', { name: 'Näytä kaikki arvostelut' })).toHaveCount(0)
    await page.getByRole('button', { name: /Basenji/ }).click()
    await expect(page.getByText('Aamun Tähti')).toBeVisible()
    await expect(page.getByText('Iltatähti')).toBeVisible()

    // Expand/collapse-all critiques appears once an open group has a critique.
    await expect(page.getByText('Hieno basenji')).toHaveCount(0)
    await page.getByRole('button', { name: 'Näytä kaikki arvostelut' }).click()
    await expect(page.getByText('Hieno basenji')).toBeVisible()
    await page.getByRole('button', { name: 'Piilota arvostelut' }).click()
    await expect(page.getByText('Hieno basenji')).toHaveCount(0)

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

  test('show winners summary and PU/PN chips render from the whole-show cache', async ({ page }) => {
    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows: [
            {
              id: 14042,
              date: YESTERDAY_FULL_DATE,
              name: 'Voittaja Show',
              month: 'Tällä viikolla',
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042',
            },
          ],
          index: { indexed_show_count: 1, total_show_count: 1, last_updated: null, last_updated_iso: null },
        }),
      })
    })

    await page.route('**/api/dog/shows/14042', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          id: 14042,
          title: 'Voittaja Show 2026',
          breeds: [
            { name: 'Basenji', count: 3, group: '6', breed_id: '123', has_results: true },
            { name: 'Akita', count: 2, group: '5', breed_id: '124', has_results: true },
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
              number: 1, name: 'Best In Show Dog', reg_url: '', grade: 'ERI', placement: 1,
              competitive_placement: 'PU1', awards: 'ROP, BIS-1', critique: '',
              gender: 'uros', class_name: 'VAL', breedName: 'Basenji', breedGroup: '6', breedId: '123',
              breedObj: { name: 'Basenji', count: 3, group: '6', breed_id: '123', has_results: true },
            },
            {
              number: 2, name: 'Group Five Winner', reg_url: '', grade: 'ERI', placement: 1,
              competitive_placement: 'PN1', awards: 'ROP, RYP-1', critique: '',
              gender: 'narttu', class_name: 'VAL', breedName: 'Akita', breedGroup: '5', breedId: '124',
              breedObj: { name: 'Akita', count: 2, group: '5', breed_id: '124', has_results: true },
            },
          ],
          cache: { status: 'complete', stale: false, total_breeds: 2, fetched_breeds: 2, failed_breeds: 0, total_dogs: 2, percent: 100 },
          fetched_at: 1781431200,
          fetched_at_iso: '2026-06-14T10:00:00Z',
        }),
      })
    })

    await page.goto('/dog')
    await page.getByRole('button', { name: /Voittaja Show/ }).click()

    // Winners summary renders on the default (unfiltered) view once the cache loads.
    await expect(page.getByRole('heading', { name: 'Näyttelyn voittajat' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'BIS', exact: true })).toBeVisible()
    await expect(page.getByText('Ryhmävoittajat (RYP-1)')).toBeVisible()
    await expect(page.getByText('Best In Show Dog')).toBeVisible()
    await expect(page.getByText('Group Five Winner')).toBeVisible()

    // Best-of-sex rank chips (PU1/PN1) render on the winner cards.
    await expect(page.getByText('PU1')).toBeVisible()
    await expect(page.getByText('PN1')).toBeVisible()

    // Applying a filter hides the summary and shows the filtered breed list instead.
    await page.getByPlaceholder('Hae rotua, tuomaria tai koiraa...').fill('Group')
    await expect(page.getByRole('heading', { name: 'Näyttelyn voittajat' })).toHaveCount(0)
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
    await page.getByRole('button', { name: /kesäkuu 2999/i }).click()
    await page.getByRole('button', { name: /Future Basenji Show/ }).click()

    await expect(page.getByText('Tuloksia ei haeta vielä')).toBeVisible()
    await expect(page.getByText(/aikaisintaan näyttelypäivänä klo 6/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Suodata koko näyttelyä' })).toHaveCount(0)
    expect(allResultsCalled).toBe(false)
  })

  test('breed list can be grouped by FCI group, judge, or alphabetically', async ({ page }) => {
    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows: [
            {
              id: 14050,
              date: '14.03.',
              name: 'Ryhmänäyttely',
              month: 'maaliskuu 2026',
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14050',
              stats: { indexed: true, breed_count: 2, show_state: 'past' },
            },
          ],
          index: { indexed_show_count: 1, total_show_count: 1, last_updated: null, last_updated_iso: null },
        }),
      })
    })

    await page.route('**/api/dog/shows/14050', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          id: 14050,
          title: 'Ryhmänäyttely 2026',
          breeds: [
            { name: 'Beagle', count: 4, group: '6', breed_id: '201', has_results: true, judge: 'Antti Aalto' },
            { name: 'Akita', count: 2, group: '5', breed_id: '202', has_results: true, judge: 'Kaarina Koski' },
          ],
          source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14050',
          fetched_at: 1781431200,
          fetched_at_iso: '2026-06-14T10:00:00Z',
        }),
      })
    })

    await stubWarmingAllResults(page, 14050)

    await page.goto('/dog')
    await page.getByRole('button', { name: /maaliskuu 2026/i }).click()
    await page.getByRole('button', { name: /Ryhmänäyttely/ }).click()
    await expect(page).toHaveURL(/\/dog\?show=14050$/)

    // Default = FCI grouping: numeric group headings, group 5 before group 6.
    await expect(page.getByRole('tab', { name: 'Ryhmä' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByRole('heading', { name: /Ryhmä 5/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Ryhmä 6/ })).toBeVisible()

    // Sections are collapsible: collapsing group 6 hides its breed.
    await expect(page.getByRole('button', { name: /Beagle/ })).toBeVisible()
    await page.getByRole('button', { name: /Ryhmä 6/ }).click()
    await expect(page.getByRole('button', { name: /Beagle/ })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /Akita/ })).toBeVisible()

    // Collapse all / expand all toggle.
    await page.getByRole('button', { name: 'Sulje kaikki' }).click()
    await expect(page.getByRole('button', { name: /Akita/ })).not.toBeVisible()
    await page.getByRole('button', { name: 'Avaa kaikki' }).click()
    await expect(page.getByRole('button', { name: /Beagle/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /Akita/ })).toBeVisible()

    // Switch to judge grouping.
    await page.getByRole('tab', { name: 'Tuomari' }).click()
    await expect(page.getByRole('heading', { name: /Antti Aalto/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Kaarina Koski/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Ryhmä 6/ })).toHaveCount(0)

    // Alphabetical = flat, no section headings, breeds still listed.
    await page.getByRole('tab', { name: 'Aakkoset' }).click()
    await expect(page.getByRole('heading', { name: /Ryhmä 5/ })).toHaveCount(0)
    await expect(page.getByRole('heading', { name: /Antti Aalto/ })).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Beagle/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /Akita/ })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sulje kaikki' })).toHaveCount(0)
  })

  test('persistent /dog brand returns to the show list in-app', async ({ page }) => {
    await page.route('**/api/dog/shows', async route => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          shows: [
            {
              id: 14042,
              date: TODAY_DATE,
              name: 'Basenji',
              month: CURRENT_MONTH_LABEL,
              source_url: 'https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=14042',
              stats: { indexed: true, breed_count: 1, show_state: 'past' },
            },
          ],
          index: { indexed_show_count: 1, total_show_count: 1, last_updated: null, last_updated_iso: null },
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

    await stubWarmingAllResults(page, 14042)

    await page.goto('/dog')

    const brand = page.getByRole('link', { name: '/dog' })
    await expect(brand).toBeVisible()

    // Open a show, then jump back to the list via the brand.
    await page.locator('.dog-this-week-section').getByRole('button', { name: /Basenji/ }).click()
    await expect(page).toHaveURL(/\/dog\?show=14042$/)
    await expect(brand).toBeVisible()

    // Marker proves the brand navigates in-app: a full page reload would wipe it.
    await page.evaluate(() => { window.__dogSpaMarker = true })
    await brand.click()
    await expect(page).toHaveURL(/\/dog$/)
    await expect(page.getByPlaceholder('Hae näyttelyä, rotua, tuomaria tai koiraa...')).toBeVisible()
    expect(await page.evaluate(() => window.__dogSpaMarker)).toBe(true)
  })
})
