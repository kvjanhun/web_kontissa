<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '../composables/useI18n.js'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const recipe = ref(null)
const loading = ref(true)
const error = ref('')
const completedSteps = ref(new Set())

// Screen Wake Lock — keeps display on while cooking
let wakeLock = null

async function acquireWakeLock() {
  if (!('wakeLock' in navigator)) return
  try {
    wakeLock = await navigator.wakeLock.request('screen')
    wakeLock.addEventListener('release', () => { wakeLock = null })
  } catch {}
}

function releaseWakeLock() {
  if (wakeLock) {
    wakeLock.release()
    wakeLock = null
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') acquireWakeLock()
}

function toggleStep(id) {
  const s = completedSteps.value
  if (s.has(id)) s.delete(id)
  else s.add(id)
}

async function fetchRecipe() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/recipes/${route.params.slug}`)
    if (res.status === 404) {
      error.value = t('recipe.notFound')
      return
    }
    if (!res.ok) throw new Error(t('recipe.loadError'))
    recipe.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function deleteRecipe() {
  if (!confirm(t('recipe.confirmDelete'))) return
  try {
    const res = await fetch(`/api/recipes/${recipe.value.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(t('recipe.deleteError'))
    router.push('/recipes')
  } catch (e) {
    error.value = e.message
  }
}

onMounted(() => {
  fetchRecipe()
  acquireWakeLock()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  releaseWakeLock()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="max-w-3xl mx-auto py-8 px-4">
    <p
      v-if="loading"
      class="text-center py-12"
      :style="{ color: 'var(--color-text-secondary)' }"
      role="status"
    >{{ t('recipes.loading') }}</p>

    <p v-else-if="error" class="text-center py-12 text-red-500" role="alert">{{ error }}</p>

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
            {{ t('recipe.edit') }}
          </router-link>
          <button
            @click="deleteRecipe"
            class="px-3 py-1.5 rounded-lg text-sm text-red-500 transition-colors duration-200 hover:bg-red-500/10"
            :style="{ border: '1px solid var(--color-border)' }"
          >
            {{ t('recipe.delete') }}
          </button>
        </div>
      </div>

      <section class="mb-8">
        <h2
          class="text-xl font-medium mb-3 pb-2"
          :style="{ color: 'var(--color-text-primary)', borderBottom: '1px solid var(--color-border)' }"
        >
          {{ t('recipe.ingredients') }}
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
          {{ t('recipe.steps') }}
        </h2>
        <ol class="space-y-3">
          <li
            v-for="(step, i) in recipe.steps"
            :key="step.id"
            class="flex items-start gap-3 cursor-pointer select-none transition-opacity duration-200"
            :style="{ color: 'var(--color-text-primary)', opacity: completedSteps.has(step.id) ? 0.4 : 1 }"
            @click="toggleStep(step.id)"
          >
            <input
              type="checkbox"
              :checked="completedSteps.has(step.id)"
              :aria-label="`${t('recipe.steps')} ${i + 1}: ${step.content}`"
              class="mt-1 shrink-0 accent-[var(--color-accent,#ff643e)]"
              @click.stop="toggleStep(step.id)"
            />
            <span>
              <span class="font-medium" :style="{ color: 'var(--color-text-secondary)' }">{{ i + 1 }}.</span>
              {{ step.content }}
            </span>
          </li>
        </ol>
      </section>

      <div class="mt-8">
        <router-link
          to="/recipes"
          class="text-sm transition-colors duration-200"
          :style="{ color: 'var(--color-text-secondary)' }"
        >
          {{ t('recipe.backToRecipes') }}
        </router-link>
      </div>
    </template>
  </div>
</template>
