import { ref, computed } from 'vue'

const user = ref(null)
const isAdmin = computed(() => user.value?.role === 'admin')
const isAuthenticated = computed(() => user.value !== null)

async function login(email, password) {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Login failed')
  user.value = data
  return data
}

async function logout() {
  await fetch('/api/logout', { method: 'POST' })
  user.value = null
}

async function checkAuth() {
  try {
    const res = await fetch('/api/me')
    if (res.ok) {
      user.value = await res.json()
    } else {
      user.value = null
    }
  } catch {
    user.value = null
  }
}

export function useAuth() {
  return { user, isAdmin, isAuthenticated, login, logout, checkAuth }
}
