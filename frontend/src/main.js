import { ViteSSG } from 'vite-ssg'
import { createPinia, storeToRefs } from 'pinia'
import App from './App.vue'
import { routes } from './router.js'
import { useAuthStore } from './stores/auth.js'
import { useI18nStore } from './stores/i18n.js'
import { trackPageView } from './composables/usePageView'
import './style.css'

export const createApp = ViteSSG(
  App,
  { routes, scrollBehavior() { return { top: 0 } } },
  ({ app, router, isClient }) => {
    app.use(createPinia())
    router.beforeEach(async (to) => {
      if (to.meta.requiresAdmin || to.meta.requiresAuth) {
        const authStore = useAuthStore()
        const { isAdmin, isAuthenticated } = storeToRefs(authStore)
        // Ensure auth state is populated before checking guards
        // (handles direct URL navigation and page refresh)
        if (!isAuthenticated.value) await authStore.checkAuth()
        if (to.meta.requiresAdmin && !isAdmin.value) return '/login'
        if (to.meta.requiresAuth && !isAuthenticated.value) return '/login'
      }
    })
    router.afterEach((to) => {
      if (isClient) {
        const { t } = useI18nStore()
        document.title = to.meta.titleKey ? t(to.meta.titleKey) : 'erez.ac'
        if (to.matched.length > 0 && to.path !== '/admin') {
          trackPageView(to.path)
        }
      }
    })
  }
)
