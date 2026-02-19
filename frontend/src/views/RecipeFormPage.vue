<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from '../composables/useI18n.js'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const isEdit = computed(() => !!route.params.slug)
const recipeId = ref(null)
const title = ref('')
const category = ref('')
const categories = ref([])
const ingredients = ref([{ amount: '', unit: '', name: '' }])
const steps = ref([{ content: '' }])
const error = ref('')
const saving = ref(false)
const loading = ref(false)

function addIngredient() {
  ingredients.value.push({ amount: '', unit: '', name: '' })
}

function removeIngredient(index) {
  if (ingredients.value.length > 1) ingredients.value.splice(index, 1)
}

function addStep() {
  steps.value.push({ content: '' })
}

function removeStep(index) {
  if (steps.value.length > 1) steps.value.splice(index, 1)
}

async function fetchCategories() {
  try {
    const res = await fetch('/api/recipes/categories')
    if (res.ok) categories.value = await res.json()
  } catch {}
}

async function fetchRecipe() {
  loading.value = true
  try {
    const res = await fetch(`/api/recipes/${route.params.slug}`)
    if (!res.ok) throw new Error(t('recipeForm.notFound'))
    const data = await res.json()
    recipeId.value = data.id
    title.value = data.title
    category.value = data.category || ''
    ingredients.value = data.ingredients.map(i => ({
      amount: i.amount || '',
      unit: i.unit || '',
      name: i.name,
    }))
    steps.value = data.steps.map(s => ({ content: s.content }))
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function submit() {
  error.value = ''
  saving.value = true
  try {
    const payload = {
      title: title.value,
      category: category.value || null,
      ingredients: ingredients.value.filter(i => i.name.trim()),
      steps: steps.value.filter(s => s.content.trim()),
    }

    const url = isEdit.value ? `/api/recipes/${recipeId.value}` : '/api/recipes'
    const method = isEdit.value ? 'PUT' : 'POST'

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    const data = await res.json()
    if (!res.ok) throw new Error(data.error || t('recipeForm.saveError'))

    router.push(`/recipes/${data.slug}`)
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchCategories()
  if (isEdit.value) fetchRecipe()
})
</script>

<template>
  <div class="max-w-3xl mx-auto py-8 px-4">
    <h1 class="text-3xl font-light mb-6" :style="{ color: 'var(--color-text-primary)' }">
      {{ isEdit ? t('recipeForm.editHeading') : t('recipeForm.newHeading') }}
    </h1>

    <p v-if="loading" class="text-center py-12" :style="{ color: 'var(--color-text-secondary)' }">
      {{ t('recipes.loading') }}
    </p>

    <form v-else @submit.prevent="submit" class="space-y-6">
      <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>

      <div>
        <label class="block text-sm mb-1" :style="{ color: 'var(--color-text-secondary)' }">{{ t('recipeForm.title') }}</label>
        <input
          v-model="title"
          type="text"
          required
          class="w-full px-4 py-2 rounded-lg text-sm outline-none"
          :style="{
            backgroundColor: 'var(--color-input-bg)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-primary)'
          }"
        />
      </div>

      <div>
        <label class="block text-sm mb-1" :style="{ color: 'var(--color-text-secondary)' }">{{ t('recipeForm.category') }}</label>
        <select
          v-model="category"
          class="w-full px-4 py-2 rounded-lg text-sm outline-none"
          :style="{
            backgroundColor: 'var(--color-input-bg)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-primary)'
          }"
        >
          <option value="">{{ t('recipeForm.none') }}</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>

      <div>
        <label class="block text-sm mb-2" :style="{ color: 'var(--color-text-secondary)' }">{{ t('recipeForm.ingredients') }}</label>
        <div v-for="(ing, i) in ingredients" :key="i" class="flex gap-2 mb-2">
          <input
            v-model="ing.amount"
            type="text"
            :placeholder="t('recipeForm.amount')"
            class="w-20 px-3 py-2 rounded-lg text-sm outline-none"
            :style="{
              backgroundColor: 'var(--color-input-bg)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-primary)'
            }"
          />
          <input
            v-model="ing.unit"
            type="text"
            :placeholder="t('recipeForm.unit')"
            class="w-20 px-3 py-2 rounded-lg text-sm outline-none"
            :style="{
              backgroundColor: 'var(--color-input-bg)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-primary)'
            }"
          />
          <input
            v-model="ing.name"
            type="text"
            :placeholder="t('recipeForm.ingredientName')"
            class="flex-1 px-3 py-2 rounded-lg text-sm outline-none"
            :style="{
              backgroundColor: 'var(--color-input-bg)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-primary)'
            }"
          />
          <button
            type="button"
            @click="removeIngredient(i)"
            class="px-2 text-red-500 hover:bg-red-500/10 rounded"
            :disabled="ingredients.length === 1"
          >
            &times;
          </button>
        </div>
        <button
          type="button"
          @click="addIngredient"
          class="text-sm transition-colors duration-200 hover:opacity-80"
          :style="{ color: 'var(--color-text-secondary)' }"
        >
          {{ t('recipeForm.addIngredient') }}
        </button>
      </div>

      <div>
        <label class="block text-sm mb-2" :style="{ color: 'var(--color-text-secondary)' }">{{ t('recipeForm.steps') }}</label>
        <div v-for="(step, i) in steps" :key="i" class="flex gap-2 mb-2">
          <span class="py-2 text-sm w-6 text-right" :style="{ color: 'var(--color-text-secondary)' }">{{ i + 1 }}.</span>
          <textarea
            v-model="step.content"
            :placeholder="t('recipeForm.stepPlaceholder')"
            rows="2"
            class="flex-1 px-3 py-2 rounded-lg text-sm outline-none resize-y"
            :style="{
              backgroundColor: 'var(--color-input-bg)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-primary)'
            }"
          ></textarea>
          <button
            type="button"
            @click="removeStep(i)"
            class="px-2 text-red-500 hover:bg-red-500/10 rounded self-start mt-2"
            :disabled="steps.length === 1"
          >
            &times;
          </button>
        </div>
        <button
          type="button"
          @click="addStep"
          class="text-sm transition-colors duration-200 hover:opacity-80"
          :style="{ color: 'var(--color-text-secondary)' }"
        >
          {{ t('recipeForm.addStep') }}
        </button>
      </div>

      <div class="flex gap-3 pt-2">
        <button
          type="submit"
          :disabled="saving"
          class="px-6 py-2 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90 disabled:opacity-50"
        >
          {{ saving ? t('recipeForm.saving') : (isEdit ? t('recipeForm.update') : t('recipeForm.create')) }}
        </button>
        <router-link
          :to="isEdit ? `/recipes/${route.params.slug}` : '/recipes'"
          class="px-6 py-2 rounded-lg text-sm font-medium transition-colors duration-200"
          :style="{
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-primary)'
          }"
        >
          {{ t('recipeForm.cancel') }}
        </router-link>
      </div>
    </form>
  </div>
</template>
