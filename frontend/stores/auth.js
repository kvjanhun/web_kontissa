import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isAuthenticated = computed(() => user.value !== null)

  async function login(email, password) {
    let res, data
    try {
      res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      data = await res.json()
    } catch {
      throw new Error('Unable to reach the server')
    }
    if (!res.ok) throw new Error(typeof data?.error === 'string' ? data.error : 'Login failed')
    user.value = data
    return data
  }

  async function logout() {
    try {
      const res = await fetch('/api/logout', { method: 'POST' })
      if (res.ok) user.value = null
    } catch {
      user.value = null
    }
  }

  async function checkAuth() {
    try {
      const res = await fetch('/api/me')
      if (res.ok) {
        user.value = await res.json()  // null when not authenticated
      }
    } catch {
      user.value = null
    }
  }

  return { user, isAdmin, isAuthenticated, login, logout, checkAuth }
})
