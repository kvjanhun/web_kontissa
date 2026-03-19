<script setup>
const { t } = useI18nStore()

const props = defineProps({
  section: { type: Object, required: true },
  delay: { type: Number, default: 0 }
})

// Strip markdown syntax and truncate for summary preview
function summarize(md, maxLen = 100) {
  const text = md.replace(/[*_`#>~\-+]/g, '').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/\s+/g, ' ').trim()
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

const renderedContent = computed(() => renderMarkdown(props.section.content))

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
          <svg class="shrink-0" width="32" height="32" viewBox="0 0 24 24" fill="none" :style="{ color: 'var(--color-accent, #ff643e)' }">
            <!-- puzzle -->
            <template v-if="proj.icon === 'puzzle'">
              <path d="M5,6 L8,6 A3,3 0 0 1 14,6 L17,6 L17,9 A3,3 0 0 1 17,15 L17,18 L5,18 L5,15 A3,3 0 0 0 5,9 Z" fill="currentColor" opacity="0.10"/>
              <path d="M5,6 L8,6 A3,3 0 0 1 14,6 L17,6 L17,9 A3,3 0 0 1 17,15 L17,18 L5,18 L5,15 A3,3 0 0 0 5,9 Z" stroke="currentColor" stroke-width="0.75" fill="none" stroke-linejoin="round"/>
            </template>
            <!-- browser / website -->
            <template v-else-if="proj.icon === 'website'">
              <svg x="0" y="0" width="24" height="24" viewBox="0 -0.08 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M15.69,4.31H4.31A1.61,1.61,0,0,0,2.7,5.92v8a1.61,1.61,0,0,0,1.61,1.61H15.69a1.61,1.61,0,0,0,1.61-1.61v-8A1.61,1.61,0,0,0,15.69,4.31ZM4.31,4.92H15.69a1,1,0,0,1,1,1v.72H3.31V5.92A1,1,0,0,1,4.31,4.92Zm11.38,10H4.31a1,1,0,0,1-1-1V7.25H16.69v6.67A1,1,0,0,1,15.69,14.92Z"/>
                <path d="M4.31,6.18A.34.34,0,1,0,4,5.85.34.34,0,0,0,4.31,6.18Z"/>
                <path d="M5.16,6.18a.34.34,0,1,0-.33-.33A.34.34,0,0,0,5.16,6.18Z"/>
                <path d="M6,6.18a.34.34,0,1,0-.33-.33A.34.34,0,0,0,6,6.18Z"/>
                <path d="M11,10.19l-.39.88-.4-.88s0,0-.07-.07,0-.06-.08-.08h0s-.07,0-.11,0a.17.17,0,0,0-.12,0h0s-.06.06-.08.08-.06,0-.08.07l-.39.88-.39-.88A.32.32,0,0,0,8.45,10a.3.3,0,0,0-.15.4L9,12a.38.38,0,0,0,.14.14h0l.12,0,.12,0h0A.38.38,0,0,0,9.53,12l.39-.89.4.89a.38.38,0,0,0,.14.14h0a.28.28,0,0,0,.13,0l.12,0h0a.38.38,0,0,0,.14-.14l.68-1.51a.31.31,0,0,0-.16-.4A.3.3,0,0,0,11,10.19Z"/>
                <path d="M14.42,10.19l-.39.88-.4-.88s-.05,0-.07-.07,0-.06-.08-.08h0a.17.17,0,0,0-.12,0s-.07,0-.11,0h0s-.05.05-.08.08-.06,0-.07.07l-.4.88-.39-.88a.3.3,0,0,0-.4-.15.3.3,0,0,0-.16.4L12.41,12a.38.38,0,0,0,.14.14h0l.12,0a.28.28,0,0,0,.13,0h0A.38.38,0,0,0,13,12l.4-.89.39.89a.38.38,0,0,0,.14.14h0a.31.31,0,0,0,.13,0l.12,0h0a.41.41,0,0,0,.15-.14L15,10.44a.3.3,0,0,0-.16-.4A.3.3,0,0,0,14.42,10.19Z"/>
                <path d="M7.56,10.19l-.39.88-.39-.88a.24.24,0,0,0-.08-.06A.23.23,0,0,0,6.62,10h0a.17.17,0,0,0-.12,0s-.07,0-.11,0h0l-.08.08s-.06,0-.07.07l-.4.88-.39-.88A.3.3,0,0,0,5,10a.31.31,0,0,0-.16.4L5.55,12a.38.38,0,0,0,.14.14h0l.12,0a.28.28,0,0,0,.13,0H6A.38.38,0,0,0,6.1,12l.4-.89.39.89a.38.38,0,0,0,.14.14h0l.12,0,.12,0h0A.38.38,0,0,0,7.45,12l.67-1.51A.3.3,0,0,0,8,10,.32.32,0,0,0,7.56,10.19Z"/>
              </svg>
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
      v-html="renderedContent"
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
.section-content :deep(ul),
.section-content :deep(ol) {
  margin: 0.5em 0 0.5em 1.25em;
}
.section-content :deep(li) {
  margin: 0.25em 0;
}
.section-content :deep(code) {
  font-family: var(--font-mono);
  background: var(--color-bg-tertiary);
  padding: 0.1em 0.35em;
  border-radius: 3px;
  font-size: 0.9em;
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
