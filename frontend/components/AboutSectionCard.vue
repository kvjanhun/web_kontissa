<script setup>
const { t } = useI18nStore()

const props = defineProps({
  section: { type: Object, required: true },
  delay: { type: Number, default: 0 }
})

// Strip HTML and truncate for summary preview
function summarize(html, maxLen = 80) {
  const text = html.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

// Parse "label: value" lines for 'currently' type
const currentlyItems = computed(() => {
  if (props.section.section_type !== 'currently') return []
  return props.section.content.split('\n').map(line => {
    const idx = line.indexOf(':')
    if (idx === -1) return { label: line.trim(), value: '' }
    return { label: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() }
  }).filter(item => item.label)
})

// Parse "name|url|description" lines for 'project' type
const projectItems = computed(() => {
  if (props.section.section_type !== 'project') return []
  return props.section.content.split('\n').map(line => {
    const parts = line.split('|').map(s => s.trim())
    return { name: parts[0] || '', url: parts[1] || '', description: parts[2] || '' }
  }).filter(item => item.name)
})

const cardTitle = computed(() => {
  if (props.section.section_type === 'project') return t('about.card.projects')
  if (props.section.section_type === 'currently') return t('about.card.currently')
  return props.section.title
})

const isExpandable = computed(() => props.section.section_type === 'text' && props.section.collapsible)
</script>

<template>
  <AboutCard
    :title="cardTitle"
    :summary="isExpandable ? summarize(section.content) : ''"
    :expandable="isExpandable"
    :delay="delay"
  >
    <!-- Project type -->
    <div v-if="section.section_type === 'project'" class="space-y-4">
      <div v-for="proj in projectItems" :key="proj.name" class="project-item">
        <div class="flex items-center gap-2.5 mb-1">
          <svg class="shrink-0" width="20" height="20" viewBox="0 0 24 24" fill="none" :style="{ color: 'var(--color-accent, #ff643e)' }">
            <path d="M12 2L17.5 5.5V12.5L12 16L6.5 12.5V5.5L12 2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M12 8L15.5 10V14L12 16L8.5 14V10L12 8Z" fill="currentColor" opacity="0.2"/>
          </svg>
          <a
            v-if="proj.url"
            :href="proj.url"
            class="font-semibold hover:underline"
            :style="{ color: 'var(--color-text-primary)' }"
          >{{ proj.name }}</a>
          <span v-else class="font-semibold" :style="{ color: 'var(--color-text-primary)' }">{{ proj.name }}</span>
        </div>
        <p class="text-sm" :style="{ color: 'var(--color-text-secondary)' }">
          {{ proj.description }}
        </p>
      </div>
    </div>

    <!-- Currently type -->
    <div v-else-if="section.section_type === 'currently'" class="space-y-2">
      <div
        v-for="(item, i) in currentlyItems"
        :key="i"
        class="flex items-baseline gap-3 pl-3 py-1.5 rounded-lg"
        :style="{ borderLeft: '2px solid var(--color-accent, #ff643e)', background: 'var(--color-bg-tertiary)' }"
      >
        <span class="text-xs font-bold uppercase tracking-wider shrink-0" :style="{ color: 'var(--color-accent, #ff643e)' }">{{ item.label }}</span>
        <span v-if="item.value" class="text-sm" :style="{ color: 'var(--color-text-primary)' }">{{ item.value }}</span>
      </div>
    </div>

    <!-- Text type (expandable) -->
    <div
      v-else
      class="section-content text-sm leading-relaxed"
      :style="{ color: 'var(--color-text-primary)' }"
      v-html="section.content"
    ></div>
  </AboutCard>
</template>

<style scoped>
.project-item {
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: var(--color-bg-tertiary);
  transition: transform 0.2s ease;
}
.project-item:hover {
  transform: translateX(4px);
}

.section-content :deep(p + p) {
  margin-top: 0.75em;
}
.section-content :deep(a) {
  color: var(--color-accent, #ff643e);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.section-content :deep(a:hover) {
  opacity: 0.8;
}
</style>
