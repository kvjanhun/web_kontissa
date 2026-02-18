<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const recipe = ref(null)
const loading = ref(true)
const error = ref('')

async function fetchRecipe() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/recipes/${route.params.slug}`)
    if (res.status === 404) {
      error.value = 'Recipe not found'
      return
    }
    if (!res.ok) throw new Error('Failed to load recipe')
    recipe.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function deleteRecipe() {
  if (!confirm('Delete this recipe?')) return
  try {
    const res = await fetch(`/api/recipes/${recipe.value.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Failed to delete')
    router.push('/recipes')
  } catch (e) {
    error.value = e.message
  }
}

onMounted(fetchRecipe)
</script>

<template>
  <div class="max-w-3xl mx-auto py-8 px-4">
    <p
      v-if="loading"
      class="text-center py-12"
      :style="{ color: 'var(--color-text-secondary)' }"
    >Loading...</p>

    <p v-else-if="error" class="text-center py-12 text-red-500">{{ error }}</p>

    <template v-else-if="recipe">
      <div class="flex justify-between items-start mb-6">
        <div>
          <h1 class="text-3xl font-light mb-1" :style="{ color: 'var(--color-text-primary)' }">
            {{ recipe.title }}
          </h1>
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
        </div>
        <div class="flex gap-2">
          <router-link
            :to="`/recipes/${recipe.slug}/edit`"
            class="px-3 py-1.5 rounded-lg text-sm transition-colors duration-200"
            :style="{
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-primary)'
            }"
          >
            Edit
          </router-link>
          <button
            @click="deleteRecipe"
            class="px-3 py-1.5 rounded-lg text-sm text-red-500 transition-colors duration-200 hover:bg-red-500/10"
            :style="{ border: '1px solid var(--color-border)' }"
          >
            Delete
          </button>
        </div>
      </div>

      <section class="mb-8">
        <h2
          class="text-xl font-medium mb-3 pb-2"
          :style="{ color: 'var(--color-text-primary)', borderBottom: '1px solid var(--color-border)' }"
        >
          Ingredients
        </h2>
        <ul class="space-y-1">
          <li
            v-for="ing in recipe.ingredients"
            :key="ing.id"
            :style="{ color: 'var(--color-text-primary)' }"
          >
            <span v-if="ing.amount" class="font-medium">{{ ing.amount }}</span>
            <span v-if="ing.unit"> {{ ing.unit }}</span>
            {{ ing.name }}
          </li>
        </ul>
      </section>

      <section>
        <h2
          class="text-xl font-medium mb-3 pb-2"
          :style="{ color: 'var(--color-text-primary)', borderBottom: '1px solid var(--color-border)' }"
        >
          Steps
        </h2>
        <ol class="space-y-3 list-decimal list-inside">
          <li
            v-for="step in recipe.steps"
            :key="step.id"
            :style="{ color: 'var(--color-text-primary)' }"
          >
            {{ step.content }}
          </li>
        </ol>
      </section>

      <div class="mt-8">
        <router-link
          to="/recipes"
          class="text-sm transition-colors duration-200"
          :style="{ color: 'var(--color-text-secondary)' }"
        >
          &larr; Back to recipes
        </router-link>
      </div>
    </template>
  </div>
</template>
