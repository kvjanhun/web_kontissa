// Restore user's locale preference after hydration.
//
// SSR always renders with 'en' (the i18n store default). On the client,
// we detect the preferred locale from localStorage or browser language
// and apply it AFTER hydration to avoid mismatches between server HTML
// and client rendering.
const supportedLocales = ['en', 'fi']

function detectLocale() {
  const stored = localStorage.getItem('locale')
  if (stored && supportedLocales.includes(stored)) return stored
  const browserLang = navigator.language?.slice(0, 2)
  if (supportedLocales.includes(browserLang)) return browserLang
  return 'en'
}

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.hook('app:mounted', () => {
    const i18nStore = useI18nStore()
    const preferred = detectLocale()
    if (preferred !== i18nStore.locale) {
      i18nStore.setLocale(preferred)
    }
  })
})
