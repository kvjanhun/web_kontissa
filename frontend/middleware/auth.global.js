export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) return  // cookies not available server-side
  if (!to.meta.requiresAdmin && !to.meta.requiresAuth) return

  const authStore = useAuthStore()
  const { isAdmin, isAuthenticated } = storeToRefs(authStore)

  // Ensure auth state is populated before checking guards
  // (handles direct URL navigation and page refresh)
  if (!isAuthenticated.value) await authStore.checkAuth()

  // Bounce to login, remembering where they were headed so we can return them
  // there after a successful sign-in (see pages/login.vue).
  if (to.meta.requiresAdmin && !isAdmin.value) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }
})
