<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const recipes = ref([])
const categories = ref([])
const search = ref('')
const selectedCategory = ref('')
const loading = ref(true)
const error = ref('')

let debounceTimer = null

async function fetchRecipes() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams()
    if (search.value) params.set('q', search.value)
    if (selectedCategory.value) params.set('category', selectedCategory.value)
    const res = await fetch(`/api/recipes?${params}`)
    if (!res.ok) throw new Error('Failed to load recipes')
    recipes.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function fetchCategories() {
  try {
    const res = await fetch('/api/recipes/categories')
    if (res.ok) categories.value = await res.json()
  } catch {}
}

function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchRecipes, 300)
}

watch(search, debouncedFetch)
watch(selectedCategory, fetchRecipes)

onMounted(() => {
  fetchCategories()
  fetchRecipes()
})
</script>

<template>
  <div class="max-w-4xl mx-auto py-8 px-4">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-light" :style="{ color: 'var(--color-text-primary)' }">Recipes</h1>
      <router-link
        to="/recipes/new"
        class="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
      >
        New Recipe
      </router-link>
    </div>

    <div class="flex flex-col sm:flex-row gap-3 mb-6">
      <input
        v-model="search"
        type="text"
        placeholder="Search recipes or ingredients..."
        class="flex-1 px-4 py-2 rounded-lg text-sm outline-none"
        :style="{
          backgroundColor: 'var(--color-input-bg)',
          border: '1px solid var(--color-border)',
          color: 'var(--color-text-primary)'
        }"
      />
      <select
        v-model="selectedCategory"
        class="px-4 py-2 rounded-lg text-sm outline-none"
        :style="{
          backgroundColor: 'var(--color-input-bg)',
          border: '1px solid var(--color-border)',
          color: 'var(--color-text-primary)'
        }"
      >
        <option value="">All categories</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
    </div>

    <p v-if="error" class="text-red-500 mb-4">{{ error }}</p>

    <p
      v-if="loading"
      class="text-center py-12"
      :style="{ color: 'var(--color-text-secondary)' }"
    >Loading...</p>

    <p
      v-else-if="recipes.length === 0"
      class="text-center py-12"
      :style="{ color: 'var(--color-text-secondary)' }"
    >No recipes found.</p>

    <div v-else class="grid gap-4 sm:grid-cols-2">
      <router-link
        v-for="recipe in recipes"
        :key="recipe.id"
        :to="`/recipes/${recipe.slug}`"
        class="block p-5 rounded-lg transition-colors duration-200"
        :style="{
          backgroundColor: 'var(--color-card-bg)',
          border: '1px solid var(--color-border)'
        }"
      >
        <h2 class="text-lg font-medium mb-1" :style="{ color: 'var(--color-text-primary)' }">
          {{ recipe.title }}
        </h2>
        <span
          v-if="recipe.category"
          class="inline-block text-xs px-2 py-0.5 rounded-full"
          :style="{
            backgroundColor: 'var(--color-tag-bg)',
            color: 'var(--color-text-secondary)'
          }"
        >
          {{ recipe.category }}
        </span>
      </router-link>
    </div>
  </div>
</template>
