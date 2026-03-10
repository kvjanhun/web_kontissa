<script setup>
definePageMeta({ titleKey: 'title.about' })

const { t } = useI18nStore()

useHead({
  title: computed(() => t('about.metaTitle')),
  meta: [
    { name: 'description', content: computed(() => t('about.metaDescription')) }
  ]
})

const { data: sections, pending: loading, error, refresh } = await useFetch('/api/sections', {
  default: () => [],
})

// If pre-render failed (no Flask during nuxt generate), retry on client
if (import.meta.client && error.value && !sections.value.length) {
  await refresh()
}

const COMPACT_TYPES = new Set(['currently', 'pills'])

const layoutGroups = computed(() => {
  const groups = []
  let compactBuffer = []

  for (const s of sections.value) {
    if (COMPACT_TYPES.has(s.section_type)) {
      compactBuffer.push(s)
      if (compactBuffer.length === 2) {
        groups.push({ type: 'pair', sections: [...compactBuffer] })
        compactBuffer = []
      }
    } else {
      if (compactBuffer.length) {
        groups.push({ type: 'single', section: compactBuffer[0] })
        compactBuffer = []
      }
      groups.push({ type: 'single', section: s })
    }
  }
  if (compactBuffer.length) {
    groups.push({ type: 'single', section: compactBuffer[0] })
  }
  return groups
})
</script>

<template>
  <div>
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
      <template v-for="(group, gi) in layoutGroups" :key="gi">
        <div v-if="group.type === 'pair'" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <SectionBlock v-for="s in group.sections" :key="s.id" :section="s" :compact="true" />
        </div>
        <SectionBlock v-else :section="group.section" />
      </template>
    </template>
  </div>
</template>
