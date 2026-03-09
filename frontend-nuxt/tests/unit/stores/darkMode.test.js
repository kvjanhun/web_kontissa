import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Must mock matchMedia before importing the store
function mockMatchMedia(prefersDark) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockReturnValue({ matches: prefersDark }),
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.resetModules()
  vi.restoreAllMocks()
})

describe('useDarkModeStore — init', () => {
  it('reads dark from localStorage', async () => {
    localStorage.setItem('theme', 'dark')
    mockMatchMedia(false)
    const { useDarkModeStore } = await import('~/stores/darkMode.js')
    const store = useDarkModeStore()
    store.init()
    expect(store.isDark).toBe(true)
  })

  it('reads light from localStorage', async () => {
    localStorage.setItem('theme', 'light')
    mockMatchMedia(true)
    const { useDarkModeStore } = await import('~/stores/darkMode.js')
    const store = useDarkModeStore()
    store.init()
    expect(store.isDark).toBe(false)
  })

  it('falls back to system dark preference when no localStorage', async () => {
    mockMatchMedia(true)
    const { useDarkModeStore } = await import('~/stores/darkMode.js')
    const store = useDarkModeStore()
    store.init()
    expect(store.isDark).toBe(true)
  })

  it('falls back to system light preference when no localStorage', async () => {
    mockMatchMedia(false)
    const { useDarkModeStore } = await import('~/stores/darkMode.js')
    const store = useDarkModeStore()
    store.init()
    expect(store.isDark).toBe(false)
  })
})

describe('useDarkModeStore — toggleDark', () => {
  it('flips isDark', async () => {
    mockMatchMedia(false)
    const { useDarkModeStore } = await import('~/stores/darkMode.js')
    const store = useDarkModeStore()
    store.init()
    expect(store.isDark).toBe(false)
    store.toggleDark()
    expect(store.isDark).toBe(true)
    store.toggleDark()
    expect(store.isDark).toBe(false)
  })

  it('persists to localStorage', async () => {
    mockMatchMedia(false)
    const { useDarkModeStore } = await import('~/stores/darkMode.js')
    const store = useDarkModeStore()
    store.init()
    store.toggleDark()
    expect(localStorage.getItem('theme')).toBe('dark')
    store.toggleDark()
    expect(localStorage.getItem('theme')).toBe('light')
  })
})
