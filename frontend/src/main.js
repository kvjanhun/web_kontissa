import { ViteSSG } from 'vite-ssg'
import App from './App.vue'
import { routes } from './router.js'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import { trackPageView } from './composables/usePageView'
import './style.css'

export const createApp = ViteSSG(
  App,
  { routes, scrollBehavior() { return { top: 0 } } },
  ({ router, isClient }) => {
    router.beforeEach(async (to) => {
      if (to.meta.requiresAdmin || to.meta.requiresAuth) {
        const { isAdmin, isAuthenticated, checkAuth } = useAuth()
        // Ensure auth state is populated before checking guards
        // (handles direct URL navigation and page refresh)
        if (!isAuthenticated.value) await checkAuth()
        if (to.meta.requiresAdmin && !isAdmin.value) return '/login'
        if (to.meta.requiresAuth && !isAuthenticated.value) return '/login'
      }
    })
    router.afterEach((to) => {
      if (isClient) {
        const { t } = useI18n()
        document.title = to.meta.titleKey ? t(to.meta.titleKey) : 'erez.ac'
        if (to.matched.length > 0 && to.path !== '/admin') {
          trackPageView(to.path)
        }
      }
    })
  }
)
