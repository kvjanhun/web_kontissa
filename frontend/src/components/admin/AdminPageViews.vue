<script setup>
import { ref, onMounted } from 'vue'

const pageViews = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/pageviews')
    if (res.ok) pageViews.value = await res.json()
  } catch { /* ignore */ }
  finally { loading.value = false }
})

function formatDate(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}
</script>

<template>
  <div>
    <div v-if="loading" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Loading...</div>
    <div v-else-if="pageViews.length === 0" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">No page views recorded yet.</div>
    <table v-else class="w-full text-sm">
      <thead>
        <tr :style="{ borderBottom: '1px solid var(--color-border)' }">
          <th class="text-left py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Path</th>
          <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Views</th>
          <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">First Seen</th>
          <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Last Updated</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pv in pageViews" :key="pv.path" :style="{ borderBottom: '1px solid var(--color-border)' }">
          <td class="py-2 px-3" :style="{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }">{{ pv.path }}</td>
          <td class="text-right py-2 px-3" :style="{ color: 'var(--color-text-primary)' }">{{ pv.count }}</td>
          <td class="text-right py-2 px-3 text-xs" :style="{ color: 'var(--color-text-secondary)' }">{{ formatDate(pv.created_at) }}</td>
          <td class="text-right py-2 px-3 text-xs" :style="{ color: 'var(--color-text-secondary)' }">{{ formatDate(pv.updated_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
