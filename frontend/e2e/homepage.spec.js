import { test, expect } from './fixtures/base.js'

test.describe('Homepage', () => {
  test('shows the hero, work, stack and terminal sections', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Selected projects/i })).toBeVisible()
    await expect(page.getByRole('heading', { name: /The stack/i })).toBeVisible()
    // Stack layers rendered from the database-backed home content
    await expect(page.getByText('Bare metal', { exact: true })).toBeVisible()
    // Interactive terminal frame
    await expect(page.getByText('konsta@erez.ac', { exact: false }).first()).toBeVisible({ timeout: 10000 })
  })

  test('the terminal section carries no footnote', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: /Terminal/i })).toBeVisible()
    // The "// Originally this site's main attraction" caption is gone for good.
    await expect(page.getByText(/Originally this site/i)).toHaveCount(0)
  })

  test('an expanded project shows the stack layers it touches', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /Sanakenno Admin tools/ }).click()
    const panel = page.locator('#proj-panel-1')
    await expect(panel.getByRole('link', { name: 'L6', exact: true })).toBeVisible()
    await expect(panel.getByRole('link', { name: 'L7', exact: true })).toBeVisible()
    // The chips are the legend link into the stack table.
    await expect(panel.getByRole('link', { name: 'L6', exact: true })).toHaveAttribute('href', '#stack')
  })

  test('the footer reports live host uptime beside the status line', async ({ page }) => {
    await page.goto('/')
    // Rendered only after the client-side /api/server-info call resolves, so the
    // prerendered HTML never carries a stale figure.
    await expect(page.getByText(/up \d+ (hour|day)s?/)).toBeVisible({ timeout: 10000 })
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

  // Panels keep their content in the DOM when collapsed (grid-template-rows 0fr),
  // so these assert on attributes without needing to expand anything.
  test('external project links open in a new tab with rel protection', async ({ page }) => {
    await page.goto('/')
    const external = page.locator('.proj__link[href="https://sanakenno.fi"]').first()
    await expect(external).toHaveAttribute('target', '_blank')
    await expect(external).toHaveAttribute('rel', 'noopener noreferrer')
  })

  test('internal project links stay in the same tab', async ({ page }) => {
    await page.goto('/')
    const internal = page.locator('.proj__link[href="#stack"]').first()
    await expect(internal).not.toHaveAttribute('target', '_blank')
    await expect(internal).not.toHaveAttribute('rel', 'noopener noreferrer')
  })
})

test.describe('Homepage — mobile nav drawer', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('collapsed drawer links are not reachable by keyboard', async ({ page }) => {
    await page.goto('/')
    const drawer = page.locator('.nav-drawer')
    // inert (not aria-hidden) while collapsed: the links stay in the DOM, so without
    // it they'd remain tabbable while hidden from assistive tech.
    await expect(drawer).toHaveAttribute('inert', '')

    // Assert the guarantee that actually matters: an inert subtree can't take focus.
    // (Playwright's role selectors don't model inert, so getByRole still finds it.)
    const canFocus = await drawer.locator('a').first().evaluate((el) => {
      el.focus()
      return document.activeElement === el
    })
    expect(canFocus).toBe(false)
  })

  test('opening the drawer exposes its links', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /Toggle menu|Käytä valikkoa/ }).click()

    const drawer = page.locator('.nav-drawer')
    await expect(drawer).not.toHaveAttribute('inert', '')
    await expect(drawer.getByRole('link', { name: 'stack' })).toBeVisible()
  })
})
