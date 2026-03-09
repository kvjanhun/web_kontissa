import { trackPageView } from '~/composables/usePageView.js'
import { useI18nStore } from '~/stores/i18n.js'

export default defineNuxtRouteMiddleware((to, from) => {
  // Only run on client side, and only after initial navigation
  if (import.meta.server) return
  if (!from.name) return

  // Set page title
  const { t } = useI18nStore()
  if (to.meta.titleKey) {
    useHead({ title: t(to.meta.titleKey) })
  }

  // Track page views (skip admin)
  if (to.matched.length > 0 && to.path !== '/admin') {
    trackPageView(to.path)
  }
})
