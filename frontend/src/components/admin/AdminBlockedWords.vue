<script setup>
import { ref, onMounted } from 'vue'

const words = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/bee/blocked')
    if (res.ok) words.value = await res.json()
  } catch { /* ignore */ }
  finally { loading.value = false }
})

function formatDate(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}

async function unblock(id, word) {
  if (!confirm(`Unblock "${word}"? It will reappear in puzzles.`)) return
  error.value = ''
  const res = await fetch(`/api/bee/block/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const data = await res.json()
    error.value = data.error || 'Failed to unblock'
    return
  }
  words.value = words.value.filter(w => w.id !== id)
}
</script>

<template>
  <div>
    <div v-if="error" role="alert" class="mb-4 p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">{{ error }}</div>
    <div v-if="loading" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Loading...</div>
    <div v-else-if="words.length === 0" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">No blocked words.</div>
    <div v-else class="max-h-96 overflow-y-auto overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="sticky top-0" :style="{ backgroundColor: 'var(--color-bg-primary)' }">
          <tr :style="{ borderBottom: '1px solid var(--color-border)' }">
            <th class="text-left py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Word</th>
            <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Blocked At</th>
            <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="bw in words" :key="bw.id" :style="{ borderBottom: '1px solid var(--color-border)' }">
            <td class="py-2 px-3" :style="{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }">{{ bw.word }}</td>
            <td class="text-right py-2 px-3 text-xs" :style="{ color: 'var(--color-text-secondary)' }">{{ formatDate(bw.blocked_at) }}</td>
            <td class="text-right py-2 px-3">
              <button @click="unblock(bw.id, bw.word)" class="text-xs px-2 py-1 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" :style="{ border: '1px solid var(--color-border)' }">Unblock</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
