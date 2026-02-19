import { ViteSSG } from 'vite-ssg'
import App from './App.vue'
import { routes } from './router.js'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import './style.css'

export const createApp = ViteSSG(
  App,
  { routes, scrollBehavior() { return { top: 0 } } },
  ({ router, isClient }) => {
    router.beforeEach((to) => {
      if (to.meta.requiresAdmin) {
        const { isAdmin } = useAuth()
        if (!isAdmin.value) return '/login'
      }
      if (to.meta.requiresAuth) {
        const { isAuthenticated } = useAuth()
        if (!isAuthenticated.value) return '/login'
      }
    })
    router.afterEach((to) => {
      if (isClient) {
        const { t } = useI18n()
        document.title = to.meta.titleKey ? t(to.meta.titleKey) : 'erez.ac'
      }
    })
  }
)
