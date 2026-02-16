<script setup>
import { ref, onMounted } from 'vue'
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'

const sections = ref([])
const updateDate = ref('')
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const [sectionsRes, metaRes] = await Promise.all([
      fetch('/api/sections'),
      fetch('/api/meta')
    ])
    sections.value = await sectionsRes.json()
    const meta = await metaRes.json()
    updateDate.value = meta.update_date
  } catch (e) {
    console.error('Failed to load site data:', e)
    error.value = e
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="flex flex-col min-h-full shadow-lg">
    <AppHeader />
    <main class="grow p-6 bg-white text-dark border-t-4 border-b-4 border-accent">
      <router-view :sections="sections" :loading="loading" :error="error" />
    </main>
    <AppFooter :update-date="updateDate" />
  </div>
</template>
