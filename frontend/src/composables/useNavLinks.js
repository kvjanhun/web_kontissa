import { computed } from 'vue'
import { useAuth } from './useAuth'

export function useNavLinks(handleLogout) {
  const { isAuthenticated, isAdmin } = useAuth()

  const navLinks = computed(() => {
    const links = [
      { to: '/about',   labelKey: 'nav.about' },
      { to: '/contact', labelKey: 'nav.contact' },
      { to: '/sanakenno', labelKey: 'nav.sanakenno' },
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
