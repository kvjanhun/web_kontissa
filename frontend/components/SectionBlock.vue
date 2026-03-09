<script setup>
import { computed } from 'vue'

const props = defineProps({
  section: { type: Object, required: true },
  compact: { type: Boolean, default: false }
})

const pills = computed(() => {
  if (props.section.section_type !== 'pills') return []
  return props.section.content.split(',').map(s => s.trim()).filter(Boolean)
})

const currentlyItems = computed(() => {
  if (props.section.section_type !== 'currently') return []
  return props.section.content.split('\n').map(line => {
    const idx = line.indexOf(':')
    if (idx === -1) return { label: line.trim(), value: '' }
    return { label: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() }
  }).filter(item => item.label)
})
</script>

<template>
  <!-- Quote type: decorative centered blockquote -->
  <div
    v-if="section.section_type === 'quote'"
    :id="section.slug"
    class="mb-6 py-6 text-center"
  >
    <div class="quote-mark" :style="{ color: 'var(--color-accent, #ff643e)' }">&ldquo;</div>
    <blockquote
      class="text-3xl font-light italic px-6"
      :style="{ color: 'var(--color-text-primary)' }"
    >{{ section.content }}</blockquote>
    <div class="mt-3 mx-auto" :style="{ width: '3rem', height: '2px', background: 'var(--color-accent, #ff643e)', opacity: 0.5 }"></div>
  </div>

  <!-- Currently type: card with accent-bordered items -->
  <article
    v-else-if="section.section_type === 'currently'"
    class="text-base leading-relaxed rounded-lg overflow-hidden h-full"
    :class="{ 'mb-6': !compact }"
    :id="section.slug"
    :style="{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }"
  >
    <div class="px-5 pt-4 pb-4">
      <h2 class="text-xl font-medium m-0 pb-1">{{ section.title }}</h2>
      <div :style="{ width: '3rem', height: '2px', background: 'var(--color-accent, #ff643e)', opacity: 0.6 }"></div>
    </div>
    <div class="px-5 pb-4 space-y-2">
      <div
        v-for="(item, i) in currentlyItems"
        :key="i"
        class="flex items-baseline gap-3 pl-3 py-1.5 rounded"
        :style="{ borderLeft: '2px solid var(--color-accent, #ff643e)', background: 'var(--color-bg-tertiary)' }"
      >
        <span class="text-xs font-semibold uppercase tracking-wide shrink-0" :style="{ color: 'var(--color-accent, #ff643e)' }">{{ item.label }}</span>
        <span v-if="item.value" class="text-sm" :style="{ color: 'var(--color-text-primary)' }">{{ item.value }}</span>
      </div>
    </div>
  </article>

  <!-- Pills type: no accent bar, bright orange pills -->
  <article
    v-else-if="section.section_type === 'pills'"
    class="text-base leading-relaxed rounded-lg"
    :class="{ 'mb-6': !compact, 'h-full': compact }"
    :id="section.slug"
    :style="{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }"
  >
    <div class="px-5 pt-4 pb-4">
      <h2 class="text-xl font-medium m-0 pb-1">{{ section.title }}</h2>
      <div :style="{ width: '3rem', height: '2px', background: 'var(--color-accent, #ff643e)', opacity: 0.6 }"></div>
    </div>
    <div class="px-5 pb-4 grid grid-cols-3 gap-2">
      <div
        v-for="pill in pills"
        :key="pill"
        class="pill flex items-center pl-3 py-1.5 rounded text-sm transition-all duration-200"
        :style="{ borderLeft: '2px solid var(--color-accent, #ff643e)', background: 'var(--color-bg-tertiary)', color: 'var(--color-text-primary)' }"
      >{{ pill }}</div>
    </div>
  </article>

  <!-- Default: text type -->
  <article
    v-else
    class="text-base leading-relaxed rounded-lg"
    :class="{ 'mb-6': !compact, 'h-full': compact }"
    :id="section.slug"
    :style="{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }"
  >
    <div class="px-5 pt-4 pb-4">
      <h2 class="text-xl font-medium m-0 pb-1">{{ section.title }}</h2>
      <div :style="{ width: '3rem', height: '2px', background: 'var(--color-accent, #ff643e)', opacity: 0.6 }"></div>
    </div>
    <div class="section-content px-5 pb-4" v-html="section.content"></div>
  </article>
</template>

<style scoped>
.section-content :deep(p + p) {
  margin-top: 0.75em;
}
.quote-mark {
  font-size: 4rem;
  line-height: 1;
  font-family: Georgia, serif;
  opacity: 0.6;
}
.pill:hover {
  background: color-mix(in srgb, var(--color-accent, #ff643e) 15%, var(--color-bg-tertiary)) !important;
}
</style>
