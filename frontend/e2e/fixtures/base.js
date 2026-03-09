import { test as base } from '@playwright/test'

// For SSR pages, Vue hydration completes after the load event fires.
// Waiting for networkidle ensures event handlers (e.g. @submit.prevent) are
// attached before Playwright interacts with the page.
export const test = base.extend({
  page: async ({ page }, use) => {
    const origGoto = page.goto.bind(page)
    page.goto = async (url, options) => {
      const resp = await origGoto(url, options)
      await page.waitForLoadState('networkidle')
      return resp
    }
    await use(page)
  },
})

export { expect } from '@playwright/test'
