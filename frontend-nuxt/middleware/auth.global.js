import { useAuthStore } from '~/stores/auth.js'

export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) return  // cookies not available server-side
  if (!to.meta.requiresAdmin && !to.meta.requiresAuth) return

  const authStore = useAuthStore()
  const { isAdmin, isAuthenticated } = storeToRefs(authStore)

  // Ensure auth state is populated before checking guards
  // (handles direct URL navigation and page refresh)
  if (!isAuthenticated.value) await authStore.checkAuth()

  if (to.meta.requiresAdmin && !isAdmin.value) {
    return navigateTo('/login')
  }
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return navigateTo('/login')
  }
})
