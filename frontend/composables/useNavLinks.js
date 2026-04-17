import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '~/stores/auth.js'

export function useNavLinks(handleLogout) {
  const { isAuthenticated, isAdmin } = storeToRefs(useAuthStore())

  const navLinks = computed(() => {
    const links = [
      { to: 'https://sanakenno.fi', labelKey: 'nav.sanakenno', external: true },
    ]
    if (isAuthenticated.value) {
      links.push({ to: '/recipes', labelKey: 'nav.recipes' })
    }
    if (isAdmin.value) {
      links.push({ to: '/admin', labelKey: 'nav.admin' })
    }
    if (isAuthenticated.value) {
      links.push({ to: '/login', labelKey: 'nav.logout', action: handleLogout })
    } else {
      links.push({ to: '/login', labelKey: 'nav.login' })
    }
    return links
  })

  return { navLinks }
}
