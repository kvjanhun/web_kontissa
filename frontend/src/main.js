import { ViteSSG } from 'vite-ssg'
import App from './App.vue'
import { routes } from './router.js'
import { useAuth } from './composables/useAuth'
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
    })
    router.afterEach((to) => {
      if (isClient) document.title = to.meta.title || 'erez.ac'
    })
  }
)
