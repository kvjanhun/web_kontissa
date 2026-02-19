<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useHead } from '@unhead/vue'
import { useAuth } from '../composables/useAuth'
import { useI18n } from '../composables/useI18n.js'

useHead({
  meta: [
    { name: 'robots', content: 'noindex' }
  ]
})

const router = useRouter()
const { user, isAuthenticated, login, logout } = useAuth()
const { t } = useI18n()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    router.push('/about')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function handleLogout() {
  await logout()
  router.push('/')
}
</script>

<template>
  <div class="max-w-sm mx-auto mt-12">
    <!-- Already logged in -->
    <div v-if="isAuthenticated" class="text-center space-y-4">
      <h1 class="text-3xl font-light mb-4" :style="{ color: 'var(--color-text-primary)' }">{{ t('login.loggedIn') }}</h1>
      <p :style="{ color: 'var(--color-text-secondary)' }">
        {{ t('login.signedInAs') }} <strong>{{ user.username }}</strong> ({{ user.email }})
      </p>
      <button
        @click="handleLogout"
        class="bg-accent text-white px-6 py-2 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
      >
        {{ t('nav.logout') }}
      </button>
    </div>

    <!-- Login form -->
    <div v-else>
      <h1 class="text-3xl font-light mb-8 text-center" :style="{ color: 'var(--color-text-primary)' }">{{ t('login.heading') }}</h1>

      <div v-if="error" id="login-error" role="alert" class="mb-4 p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">
        {{ error }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label for="email" class="block text-sm mb-1" :style="{ color: 'var(--color-text-secondary)' }">{{ t('login.email') }}</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            required
            :aria-invalid="!!error"
            :aria-describedby="error ? 'login-error' : undefined"
            class="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors duration-200 focus:ring-2 focus:ring-accent"
            :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
          />
        </div>

        <div>
          <label for="password" class="block text-sm mb-1" :style="{ color: 'var(--color-text-secondary)' }">{{ t('login.password') }}</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            class="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors duration-200 focus:ring-2 focus:ring-accent"
            :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
          />
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-accent text-white py-2 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90 disabled:opacity-50"
        >
          {{ loading ? t('login.signingIn') : t('login.signIn') }}
        </button>
      </form>
    </div>
  </div>
</template>
