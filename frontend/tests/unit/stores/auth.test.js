import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '~/stores/auth.js'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.restoreAllMocks()
})

describe('useAuthStore — initial state', () => {
  it('starts unauthenticated', () => {
    const auth = useAuthStore()
    expect(auth.user).toBeNull()
    expect(auth.isAuthenticated).toBe(false)
    expect(auth.isAdmin).toBe(false)
  })
})

describe('useAuthStore — checkAuth', () => {
  it('sets user when /api/me returns 200', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 1, email: 'user@test.com', role: 'user' }),
    }))
    const auth = useAuthStore()
    await auth.checkAuth()
    expect(auth.user).toEqual({ id: 1, email: 'user@test.com', role: 'user' })
    expect(auth.isAuthenticated).toBe(true)
  })

  it('clears user when /api/me returns null (not authenticated)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(null),
    }))
    const auth = useAuthStore()
    auth.user = { id: 1, role: 'user' }
    await auth.checkAuth()
    expect(auth.user).toBeNull()
  })

  it('clears user on network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')))
    const auth = useAuthStore()
    auth.user = { id: 1, role: 'user' }
    await auth.checkAuth()
    expect(auth.user).toBeNull()
  })
})

describe('useAuthStore — login', () => {
  it('sets user on successful login', async () => {
    const userData = { id: 1, email: 'user@test.com', role: 'user' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(userData),
    }))
    const auth = useAuthStore()
    const result = await auth.login('user@test.com', 'pass')
    expect(auth.user).toEqual(userData)
    expect(result).toEqual(userData)
  })

  it('throws on failed login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Invalid credentials' }),
    }))
    const auth = useAuthStore()
    await expect(auth.login('bad@test.com', 'wrong')).rejects.toThrow('Invalid credentials')
    expect(auth.user).toBeNull()
  })
})

describe('useAuthStore — logout', () => {
  it('clears user on successful logout', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }))
    const auth = useAuthStore()
    auth.user = { id: 1, role: 'user' }
    await auth.logout()
    expect(auth.user).toBeNull()
  })

  it('clears user on network error during logout', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')))
    const auth = useAuthStore()
    auth.user = { id: 1, role: 'user' }
    await auth.logout()
    expect(auth.user).toBeNull()
  })
})

describe('useAuthStore — isAdmin', () => {
  it('is true when role is admin', () => {
    const auth = useAuthStore()
    auth.user = { id: 1, role: 'admin' }
    expect(auth.isAdmin).toBe(true)
  })

  it('is false when role is user', () => {
    const auth = useAuthStore()
    auth.user = { id: 1, role: 'user' }
    expect(auth.isAdmin).toBe(false)
  })
})
