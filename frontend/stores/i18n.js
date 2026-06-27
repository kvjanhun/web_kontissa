import { ref } from 'vue'
import { defineStore } from 'pinia'
import en from '~/locales/en.json'
import fi from '~/locales/fi.json'
import homeSnapshot from '~/locales/home-content.snapshot.json'

const messages = { en, fi }
const supportedLocales = ['en', 'fi']

export const useI18nStore = defineStore('i18n', () => {
  // Always initialize with 'en' for SSR compatibility.
  // The locale.client.js plugin restores the user's preference after hydration.
  const locale = ref('en')

  // Database-backed home content (Stage 2). Seeded from the build snapshot so the
  // statically-generated page paints correct content immediately; loadHomeContent()
  // re-fetches the live values from /api/home-content and swaps them in reactively.
  // home.* keys resolve from this overlay first, then fall back to the bundled
  // messages (which still hold home.* chrome strings like nav/section labels).
  const homeContent = ref({ en: { ...homeSnapshot.en }, fi: { ...homeSnapshot.fi } })

  function resolveRaw(key) {
    if (key.startsWith('home.')) {
      const loc = homeContent.value[locale.value]
      if (loc && loc[key] !== undefined) return loc[key]
      const enLoc = homeContent.value.en
      if (enLoc && enLoc[key] !== undefined) return enLoc[key]
    }
    const val = messages[locale.value]?.[key]
    return val !== undefined ? val : messages.en[key]
  }

  function t(key, params) {
    let str = resolveRaw(key)
    if (str === undefined || str === null) str = key
    if (params && typeof str === 'string') {
      for (const [k, v] of Object.entries(params)) {
        str = str.replace(`{${k}}`, v)
      }
    }
    return str
  }

  // Raw message accessor: returns the value as-is (string, array, or object)
  // for structured content (e.g. project/stack-layer/footer-link arrays),
  // with the same overlay→English fallback as t(). No parameter interpolation.
  function tm(key) {
    return resolveRaw(key)
  }

  async function loadHomeContent(loc = locale.value) {
    if (typeof window === 'undefined') return
    try {
      const res = await fetch(`/api/home-content?locale=${loc}`)
      if (!res.ok) return
      const data = await res.json()
      homeContent.value = { ...homeContent.value, [loc]: data }
    } catch {
      // Keep the baked snapshot on any network/parse failure.
    }
  }

  function setLocale(lang) {
    if (!supportedLocales.includes(lang)) return
    locale.value = lang
    if (typeof window !== 'undefined') {
      localStorage.setItem('locale', lang)
      document.documentElement.lang = lang
    }
  }

  return { locale, t, tm, setLocale, loadHomeContent }
})
