<script setup>
import { ref, onMounted } from 'vue'

const stats = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/bee/stats')
    if (res.ok) stats.value = await res.json()
  } catch { /* ignore */ }
  finally { loading.value = false }
})
</script>

<template>
  <div>
    <div v-if="loading" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Loading...</div>
    <div v-else-if="!stats" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Failed to load stats.</div>
    <div v-else class="space-y-2">
      <div v-for="(value, label) in {
        'Sanakenno Page Views': stats.page_views,
        'Blocked Words': stats.blocked_words_count,
        'Total Puzzles': stats.total_puzzles,
      }" :key="label" class="flex justify-between py-2 px-3 rounded" :style="{ borderBottom: '1px solid var(--color-border)' }">
        <span class="text-sm font-medium" :style="{ color: 'var(--color-text-secondary)' }">{{ label }}</span>
        <span class="text-sm" :style="{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }">{{ value }}</span>
      </div>
    </div>
  </div>
</template>
