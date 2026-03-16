// Restore locale from localStorage after SSR hydration.
// Nuxt serializes Pinia state from the server (always 'en') into the page
// payload, which overwrites the client-side detectLocale() result on hydration.
export default defineNuxtPlugin(() => {
  const i18nStore = useI18nStore()
  const stored = localStorage.getItem('locale')
  if (stored && stored !== i18nStore.locale) {
    i18nStore.setLocale(stored)
  }
})
