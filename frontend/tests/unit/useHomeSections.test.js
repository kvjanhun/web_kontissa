import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useI18nStore } from '~/stores/i18n.js'
import { useHomeSections, HIDEABLE_SECTIONS } from '~/composables/useHomeSections.js'

// The composable reads `home.hiddenSections` out of the i18n store's home-content
// overlay, so each case seeds the overlay the way the live page does: through
// loadHomeContent() against a stubbed /api/home-content.
async function withOverlay(overlay) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => overlay }))
  await useI18nStore().loadHomeContent('en')
  return useHomeSections()
}

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useHomeSections', () => {
  it('shows every band when nothing is hidden', async () => {
    const { isVisible } = await withOverlay({ 'home.hiddenSections': [] })
    for (const key of HIDEABLE_SECTIONS) {
      expect(isVisible(key)).toBe(true)
    }
  })

  it('hides exactly the listed bands', async () => {
    const { isVisible } = await withOverlay({ 'home.hiddenSections': ['stack'] })
    expect(isVisible('stack')).toBe(false)
    expect(isVisible('work')).toBe(true)
    expect(isVisible('terminal')).toBe(true)
  })

  it('hides several at once', async () => {
    const { isVisible } = await withOverlay({ 'home.hiddenSections': ['stack', 'terminal'] })
    expect(isVisible('stack')).toBe(false)
    expect(isVisible('terminal')).toBe(false)
    expect(isVisible('work')).toBe(true)
  })

  it('shows everything when the key is missing entirely', async () => {
    // A build snapshot baked before this feature has no home.hiddenSections. That
    // must read as "nothing hidden", not as a blank page.
    const { isVisible } = await withOverlay({ 'home.hero.body': 'x' })
    for (const key of HIDEABLE_SECTIONS) {
      expect(isVisible(key)).toBe(true)
    }
  })

  it('ignores a non-array value rather than throwing', async () => {
    const { isVisible } = await withOverlay({ 'home.hiddenSections': 'stack' })
    expect(isVisible('stack')).toBe(true)
  })

  it('tracks a later overlay refresh', async () => {
    // The page paints from the snapshot and then swaps in live DB content; a band
    // hidden since the build must disappear on that second pass.
    const { isVisible } = await withOverlay({ 'home.hiddenSections': [] })
    expect(isVisible('terminal')).toBe(true)

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ 'home.hiddenSections': ['terminal'] }),
    }))
    await useI18nStore().loadHomeContent('en')
    expect(isVisible('terminal')).toBe(false)
  })

  it('lists the same bands the API allows, in page order', () => {
    // Mirrors HOME_SECTIONS in app/home_content.py. Hero and footer are chrome and
    // must not be hideable.
    expect(HIDEABLE_SECTIONS).toEqual(['work', 'stack', 'terminal'])
  })
})
