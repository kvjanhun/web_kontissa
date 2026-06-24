import { ref } from 'vue'
import { defineStore } from 'pinia'
import en from '~/locales/en.json'
import fi from '~/locales/fi.json'

const messages = { en, fi }
const supportedLocales = ['en', 'fi']

export const useI18nStore = defineStore('i18n', () => {
  // Always initialize with 'en' for SSR compatibility.
  // The locale.client.js plugin restores the user's preference after hydration.
  const locale = ref('en')

  function t(key, params) {
    let str = messages[locale.value]?.[key] || messages.en[key] || key
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        str = str.replace(`{${k}}`, v)
      }
    }
    return str
  }

  // Raw message accessor: returns the value as-is (string, array, or object)
  // for structured content (e.g. project/stack-layer/footer-link arrays),
  // with the same English fallback as t(). No parameter interpolation.
  function tm(key) {
    const val = messages[locale.value]?.[key]
    return val !== undefined ? val : messages.en[key]
  }

  function setLocale(lang) {
    if (!supportedLocales.includes(lang)) return
    locale.value = lang
    if (typeof window !== 'undefined') {
      localStorage.setItem('locale', lang)
      document.documentElement.lang = lang
    }
  }

  return { locale, t, tm, setLocale }
})
