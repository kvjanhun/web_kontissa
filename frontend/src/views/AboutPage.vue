<script setup>
import { ref, computed, onMounted } from 'vue'
import { useHead } from '@unhead/vue'
import { useI18n } from '../composables/useI18n.js'
import SectionBlock from '../components/SectionBlock.vue'

const { t } = useI18n()

useHead({
  title: computed(() => t('about.metaTitle')),
  meta: [
    { name: 'description', content: computed(() => t('about.metaDescription')) }
  ]
})

const sections = ref([])
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const res = await fetch('/api/sections')
    sections.value = await res.json()
  } catch (e) {
    console.error('Failed to load sections:', e)
    error.value = e
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-light mb-8" :style="{ color: 'var(--color-text-primary)' }">{{ t('about.heading') }}</h1>

    <div v-if="loading" class="space-y-6">
      <div v-for="n in 3" :key="n" class="animate-pulse">
        <div class="h-8 rounded w-1/4 mb-3" :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"></div>
        <div class="h-4 rounded w-full mb-2" :style="{ backgroundColor: 'var(--color-bg-secondary)' }"></div>
        <div class="h-4 rounded w-3/4" :style="{ backgroundColor: 'var(--color-bg-secondary)' }"></div>
      </div>
    </div>

    <div v-else-if="error" class="rounded-lg p-6 text-center" :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }">
      <p class="text-red-500 mb-2">{{ t('about.loadError') }}</p>
      <p :style="{ color: 'var(--color-text-tertiary)' }" class="text-sm">{{ t('about.loadErrorHint') }}</p>
    </div>

    <template v-else>
      <SectionBlock v-for="section in sections" :key="section.id" :section="section" />
    </template>
  </div>
</template>
