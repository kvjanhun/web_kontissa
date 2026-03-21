import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '~/stores/auth.js'
import { useNavLinks } from '~/composables/useNavLinks.js'

describe('useNavLinks', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function setup(userRole = null, handleLogout = () => {}) {
    const auth = useAuthStore()
    auth.user = userRole ? { id: 1, username: 'test', role: userRole } : null
    const { navLinks } = useNavLinks(handleLogout)
    return navLinks.value
  }

  // ---------------------------------------------------------------------------
  // Anonymous visitor
  // ---------------------------------------------------------------------------

  describe('anonymous (not logged in)', () => {
    it('includes the three public links', () => {
      const links = setup(null)
      const routes = links.map((l) => l.to)
      expect(routes).toContain('/about')
      expect(routes).toContain('/contact')
      expect(routes).toContain('/sanakenno')
    })

    it('includes a login link', () => {
      const links = setup(null)
      const login = links.find((l) => l.labelKey === 'nav.login')
      expect(login).toBeDefined()
      expect(login.to).toBe('/login')
    })

    it('does not include recipes or admin links', () => {
      const links = setup(null)
      const keys = links.map((l) => l.labelKey)
      expect(keys).not.toContain('nav.recipes')
      expect(keys).not.toContain('nav.admin')
    })

    it('does not include a logout link', () => {
      const links = setup(null)
      const keys = links.map((l) => l.labelKey)
      expect(keys).not.toContain('nav.logout')
    })

    it('login link has no action property', () => {
      const links = setup(null)
      const login = links.find((l) => l.labelKey === 'nav.login')
      expect(login.action).toBeUndefined()
    })
  })

  // ---------------------------------------------------------------------------
  // Authenticated non-admin user
  // ---------------------------------------------------------------------------

  describe('authenticated user (role: user)', () => {
    it('includes recipes link', () => {
      const links = setup('user')
      expect(links.find((l) => l.labelKey === 'nav.recipes')).toBeDefined()
    })

    it('includes a logout link instead of login', () => {
      const links = setup('user')
      const keys = links.map((l) => l.labelKey)
      expect(keys).toContain('nav.logout')
      expect(keys).not.toContain('nav.login')
    })

    it('does not include the admin link', () => {
      const links = setup('user')
      const keys = links.map((l) => l.labelKey)
      expect(keys).not.toContain('nav.admin')
    })

    it('logout link carries the handleLogout action', () => {
      const handleLogout = () => 'logout called'
      const auth = useAuthStore()
      auth.user = { id: 1, username: 'u', role: 'user' }
      const { navLinks } = useNavLinks(handleLogout)
      const logout = navLinks.value.find((l) => l.labelKey === 'nav.logout')
      expect(logout.action).toBe(handleLogout)
    })

    it('still includes all three public links', () => {
      const links = setup('user')
      const routes = links.map((l) => l.to)
      expect(routes).toContain('/about')
      expect(routes).toContain('/contact')
      expect(routes).toContain('/sanakenno')
    })
  })

  // ---------------------------------------------------------------------------
  // Admin user
  // ---------------------------------------------------------------------------

  describe('admin user (role: admin)', () => {
    it('includes the admin link', () => {
      const links = setup('admin')
      const admin = links.find((l) => l.labelKey === 'nav.admin')
      expect(admin).toBeDefined()
      expect(admin.to).toBe('/admin')
    })

    it('includes recipes link', () => {
      const links = setup('admin')
      expect(links.find((l) => l.labelKey === 'nav.recipes')).toBeDefined()
    })

    it('includes logout link', () => {
      const links = setup('admin')
      expect(links.find((l) => l.labelKey === 'nav.logout')).toBeDefined()
    })

    it('does not include login link', () => {
      const links = setup('admin')
      expect(links.find((l) => l.labelKey === 'nav.login')).toBeUndefined()
    })
  })

  // ---------------------------------------------------------------------------
  // Reactivity — links update when auth state changes
  // ---------------------------------------------------------------------------

  describe('reactivity', () => {
    it('updates links when user logs in', () => {
      const auth = useAuthStore()
      auth.user = null
      const { navLinks } = useNavLinks(() => {})

      expect(navLinks.value.find((l) => l.labelKey === 'nav.recipes')).toBeUndefined()

      auth.user = { id: 1, role: 'user' }
      expect(navLinks.value.find((l) => l.labelKey === 'nav.recipes')).toBeDefined()
    })

    it('updates links when user logs out', () => {
      const auth = useAuthStore()
      auth.user = { id: 1, role: 'user' }
      const { navLinks } = useNavLinks(() => {})

      expect(navLinks.value.find((l) => l.labelKey === 'nav.logout')).toBeDefined()

      auth.user = null
      expect(navLinks.value.find((l) => l.labelKey === 'nav.login')).toBeDefined()
      expect(navLinks.value.find((l) => l.labelKey === 'nav.logout')).toBeUndefined()
    })

    it('adds admin link when user gains admin role', () => {
      const auth = useAuthStore()
      auth.user = { id: 1, role: 'user' }
      const { navLinks } = useNavLinks(() => {})

      expect(navLinks.value.find((l) => l.labelKey === 'nav.admin')).toBeUndefined()

      auth.user = { id: 1, role: 'admin' }
      expect(navLinks.value.find((l) => l.labelKey === 'nav.admin')).toBeDefined()
    })
  })
})
