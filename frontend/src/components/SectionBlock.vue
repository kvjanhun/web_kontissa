<script setup>
import { computed } from 'vue'

const props = defineProps({
  section: { type: Object, required: true }
})

const pills = computed(() => {
  if (props.section.section_type !== 'pills') return []
  return props.section.content.split(',').map(s => s.trim()).filter(Boolean)
})
</script>

<template>
  <article
    class="text-base leading-relaxed mb-6 rounded-lg"
    :id="section.slug"
    :style="{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }"
  >
    <h2 class="text-xl font-medium px-5 pt-4 pb-2 m-0">{{ section.title }}</h2>
    <div v-if="section.section_type === 'pills'" class="px-5 pb-4 flex flex-wrap gap-2">
      <span
        v-for="pill in pills"
        :key="pill"
        class="px-3 py-1 rounded-full text-sm font-medium"
        :style="{ background: 'var(--color-bg-tertiary)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)' }"
      >{{ pill }}</span>
    </div>
    <div v-else class="section-content px-5 pb-4" v-html="section.content"></div>
  </article>
</template>

<style scoped>
.section-content :deep(p + p) {
  margin-top: 0.75em;
}
</style>
