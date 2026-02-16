<script setup>
import { ref, onMounted } from 'vue'
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
import { useAuth } from './composables/useAuth'

const { checkAuth } = useAuth()
const updateDate = ref('')

onMounted(async () => {
  checkAuth()
  try {
    const res = await fetch('/api/meta')
    const meta = await res.json()
    updateDate.value = meta.update_date
  } catch (e) {
    console.error('Failed to load meta:', e)
  }
})
</script>

<template>
  <div class="flex flex-col min-h-screen">
    <AppHeader />
    <main class="grow p-6" :style="{ backgroundColor: 'var(--color-bg-primary)', color: 'var(--color-text-primary)' }">
      <router-view />
    </main>
    <AppFooter :update-date="updateDate" />
  </div>
</template>
