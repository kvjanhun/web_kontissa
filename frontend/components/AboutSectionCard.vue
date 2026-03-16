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

// Parse "name|url|description|icon" lines for 'project' type
const projectItems = computed(() => {
  if (props.section.section_type !== 'project') return []
  return props.section.content.split('\n').map(line => {
    const parts = line.split('|').map(s => s.trim())
    return { name: parts[0] || '', url: parts[1] || '', description: parts[2] || '', icon: parts[3] || 'code' }
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
            <!-- puzzle -->
            <template v-if="proj.icon === 'puzzle'">
              <path d="M12 2L14.5 7H9.5L12 2Z" fill="currentColor" opacity="0.3"/>
              <path d="M5 8h14v10a2 2 0 01-2 2H7a2 2 0 01-2-2V8z" stroke="currentColor" stroke-width="1.5" fill="none"/>
              <path d="M9 8V6a3 3 0 016 0v2" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>
              <circle cx="12" cy="13" r="2" fill="currentColor" opacity="0.5"/>
            </template>
            <!-- server -->
            <template v-else-if="proj.icon === 'server'">
              <rect x="3" y="4" width="18" height="4" rx="1" stroke="currentColor" stroke-width="1.5" fill="none"/>
              <rect x="3" y="10" width="18" height="4" rx="1" stroke="currentColor" stroke-width="1.5" fill="none"/>
              <rect x="3" y="16" width="18" height="4" rx="1" stroke="currentColor" stroke-width="1.5" fill="none"/>
              <circle cx="7" cy="6" r="0.8" fill="currentColor"/>
              <circle cx="7" cy="12" r="0.8" fill="currentColor"/>
              <circle cx="7" cy="18" r="0.8" fill="currentColor"/>
            </template>
            <!-- globe -->
            <template v-else-if="proj.icon === 'globe'">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.5" fill="none"/>
              <path d="M12 3c-2.5 3-4 5.5-4 9s1.5 6 4 9" stroke="currentColor" stroke-width="1.5" fill="none"/>
              <path d="M12 3c2.5 3 4 5.5 4 9s-1.5 6-4 9" stroke="currentColor" stroke-width="1.5" fill="none"/>
              <path d="M3 12h18" stroke="currentColor" stroke-width="1.5"/>
            </template>
            <!-- star -->
            <template v-else-if="proj.icon === 'star'">
              <path d="M12 2l2.9 6.1L22 9.3l-5 4.9 1.2 7-6.2-3.3L5.8 21.2l1.2-7-5-4.9 7.1-1.2L12 2z" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linejoin="round"/>
              <path d="M12 2l2.9 6.1L22 9.3l-5 4.9 1.2 7-6.2-3.3L5.8 21.2l1.2-7-5-4.9 7.1-1.2L12 2z" fill="currentColor" opacity="0.15"/>
            </template>
            <!-- code (default) -->
            <template v-else>
              <path d="M8 6L3 12l5 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
              <path d="M16 6l5 6-5 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
              <path d="M13 4l-2 16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
            </template>
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
