import { ref } from 'vue'
import en from '../locales/en.json'
import fi from '../locales/fi.json'

const messages = { en, fi }
const supportedLocales = ['en', 'fi']

function detectLocale() {
  if (typeof window === 'undefined') return 'en'
  const stored = localStorage.getItem('locale')
  if (stored && supportedLocales.includes(stored)) return stored
  const browserLang = navigator.language?.slice(0, 2)
  if (supportedLocales.includes(browserLang)) return browserLang
  return 'en'
}

const locale = ref(detectLocale())

if (typeof window !== 'undefined') {
  document.documentElement.lang = locale.value
}

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

export function useI18n() {
  return { locale, t, setLocale }
}
