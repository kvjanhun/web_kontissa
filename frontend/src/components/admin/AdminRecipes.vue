<script setup>
import { ref, onMounted } from 'vue'

const recipes = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const res = await fetch('/api/recipes')
    if (res.ok) recipes.value = await res.json()
  } catch { /* ignore */ }
  finally { loading.value = false }
})

function formatDate(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString()
}

async function deleteRecipe(id) {
  if (!confirm('Delete this recipe?')) return
  error.value = ''
  const res = await fetch(`/api/recipes/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const data = await res.json()
    error.value = data.error || 'Failed to delete'
    return
  }
  recipes.value = recipes.value.filter(r => r.id !== id)
}
</script>

<template>
  <div>
    <div v-if="error" role="alert" class="mb-4 p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">{{ error }}</div>
    <div v-if="loading" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Loading...</div>
    <div v-else-if="recipes.length === 0" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">No recipes yet.</div>
    <div v-else class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr :style="{ borderBottom: '1px solid var(--color-border)' }">
          <th class="text-left py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Title</th>
          <th class="text-left py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Category</th>
          <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Created</th>
          <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="recipe in recipes" :key="recipe.id" :style="{ borderBottom: '1px solid var(--color-border)' }">
          <td class="py-2 px-3" :style="{ color: 'var(--color-text-primary)' }">{{ recipe.title }}</td>
          <td class="py-2 px-3" :style="{ color: 'var(--color-text-secondary)' }">{{ recipe.category || '-' }}</td>
          <td class="text-right py-2 px-3 text-xs" :style="{ color: 'var(--color-text-secondary)' }">{{ formatDate(recipe.created_at) }}</td>
          <td class="text-right py-2 px-3">
            <a :href="`/recipes/${recipe.slug}/edit`" class="text-xs px-2 py-1 rounded transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">Edit</a>
            <button @click="deleteRecipe(recipe.id)" class="ml-2 text-xs px-2 py-1 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" :style="{ border: '1px solid var(--color-border)' }">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
    </div>
  </div>
</template>
