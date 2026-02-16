<script setup>
import { ref } from 'vue'

const email = ref('')
const password = ref('')

function handleSubmit() {
  console.log('Login attempt:', { email: email.value, password: password.value })
}
</script>

<template>
  <div class="max-w-sm mx-auto mt-12">
    <h1 class="text-3xl font-light mb-8 text-center" :style="{ color: 'var(--color-text-primary)' }">Login</h1>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <div>
        <label for="email" class="block text-sm mb-1" :style="{ color: 'var(--color-text-secondary)' }">Email</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          class="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors duration-200 focus:ring-2 focus:ring-accent"
          :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
        />
      </div>

      <div>
        <label for="password" class="block text-sm mb-1" :style="{ color: 'var(--color-text-secondary)' }">Password</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          class="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors duration-200 focus:ring-2 focus:ring-accent"
          :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
        />
      </div>

      <button
        type="submit"
        class="w-full bg-accent text-white py-2 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
      >
        Sign in
      </button>
    </form>
  </div>
</template>
