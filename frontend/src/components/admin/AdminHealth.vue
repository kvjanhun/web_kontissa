<script setup>
import { ref, onMounted } from 'vue'

const health = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/admin/health')
    if (res.ok) health.value = await res.json()
  } catch { /* ignore */ }
  finally { loading.value = false }
})

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let val = bytes
  while (val >= 1024 && i < units.length - 1) { val /= 1024; i++ }
  return `${val.toFixed(1)} ${units[i]}`
}

function formatUptime(seconds) {
  if (!seconds) return '0s'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const parts = []
  if (d) parts.push(`${d}d`)
  if (h) parts.push(`${h}h`)
  if (m) parts.push(`${m}m`)
  parts.push(`${s}s`)
  return parts.join(' ')
}
</script>

<template>
  <div>
    <div v-if="loading" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Loading...</div>
    <div v-else-if="!health" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Failed to load health data.</div>
    <div v-else class="space-y-2">
      <div v-for="(value, label) in {
        'Python': health.python_version,
        'Database Size': formatBytes(health.db_size_bytes),
        'Disk Total': formatBytes(health.disk_total_bytes),
        'Disk Free': formatBytes(health.disk_free_bytes),
        'Uptime': formatUptime(health.uptime_seconds),
      }" :key="label" class="flex justify-between py-2 px-3 rounded" :style="{ borderBottom: '1px solid var(--color-border)' }">
        <span class="text-sm font-medium" :style="{ color: 'var(--color-text-secondary)' }">{{ label }}</span>
        <span class="text-sm" :style="{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }">{{ value }}</span>
      </div>
    </div>
  </div>
</template>
