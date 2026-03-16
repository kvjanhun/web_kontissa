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

  function setLocale(lang) {
    if (!supportedLocales.includes(lang)) return
    locale.value = lang
    if (typeof window !== 'undefined') {
      localStorage.setItem('locale', lang)
      document.documentElement.lang = lang
    }
  }

  return { locale, t, setLocale }
})
