<script setup>
definePageMeta({ titleKey: 'title.about' })

const i18nStore = useI18nStore()
const { t } = i18nStore
const { locale } = storeToRefs(i18nStore)

useHead({
  title: computed(() => t('about.metaTitle')),
  meta: [
    { name: 'description', content: computed(() => t('about.metaDescription')) }
  ]
})

const retrying = ref(false)

const { data: sections, pending, error, refresh } = await useFetch('/api/sections', {
  query: { locale },
  default: () => [],
  watch: [locale],
})

// Tech pills are language-independent — always fetch from EN
const { data: enSections } = await useFetch('/api/sections', {
  query: { locale: 'en' },
  default: () => [],
})

if (import.meta.client && error.value && !sections.value.length) {
  error.value = null
  retrying.value = true
  await refresh()
  retrying.value = false
}

const loading = computed(() => pending.value || retrying.value)

// Look up sections by type — admin only needs to pick the right type
const byType = computed(() => {
  const map = {}
  for (const s of sections.value) {
    map[s.section_type] = s
  }
  return map
})

// Slug-based lookup for free-form text sections (Beyond Code, Contact)
const bySlug = computed(() => {
  const map = {}
  for (const s of sections.value) map[s.slug] = s
  return map
})

const enByType = computed(() => {
  const map = {}
  for (const s of enSections.value) map[s.section_type] = s
  return map
})

const currentlyItems = computed(() => {
  const section = byType.value['currently']
  if (!section) return []
  return section.content.split('\n').map(line => {
    const idx = line.indexOf(':')
    if (idx === -1) return { label: line.trim(), value: '' }
    return { label: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() }
  }).filter(item => item.label)
})

// Categorize tech pills from the flat API list (case-sensitive to match DB)
const TECH_CATEGORIES = [
  { labelKey: 'about.tech.frontend', items: ['Nuxt', 'Vue.js', 'JavaScript', 'Tailwind CSS'] },
  { labelKey: 'about.tech.backend', items: ['Python', 'Flask', 'SQLite', 'Gunicorn'] },
  { labelKey: 'about.tech.infra', items: ['Docker', 'Nginx', 'nginx', 'Linux', 'RHEL', 'Bash', 'Git', 'GnuPG'] },
  { labelKey: 'about.tech.ai', items: ['Claude'] }
]

const techCategories = computed(() => {
  const section = enByType.value['pills']
  if (!section) return []
  const available = new Set(section.content.split(',').map(s => s.trim()).filter(Boolean))
  const cats = []
  const placed = new Set()

  for (const cat of TECH_CATEGORIES) {
    const items = cat.items.filter(i => available.has(i))
    if (items.length) {
      cats.push({ label: t(cat.labelKey), items })
      items.forEach(i => placed.add(i))
    }
  }

  const uncategorized = [...available].filter(i => !placed.has(i))
  if (uncategorized.length) {
    const last = cats[cats.length - 1]
    if (last) {
      last.items.push(...uncategorized)
    } else {
      cats.push({ label: t('about.tech.other'), items: uncategorized })
    }
  }

  return cats
})

const quoteText = computed(() => byType.value['quote']?.content || '')
const introText = computed(() => byType.value['intro']?.content || '')

// Parse project items from section content: "name|url|description" per line
const projectItems = computed(() => {
  const section = byType.value['project']
  if (!section) return []
  return section.content.split('\n').map(line => {
    const parts = line.split('|').map(s => s.trim())
    return { name: parts[0] || '', url: parts[1] || '', description: parts[2] || '' }
  }).filter(item => item.name)
})

</script>

<template>
  <div class="about-page">
    <!-- Loading -->
    <div v-if="loading" class="space-y-6">
      <div v-for="n in 3" :key="n" class="animate-pulse">
        <div class="h-8 rounded w-1/4 mb-3" :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"></div>
        <div class="h-4 rounded w-full mb-2" :style="{ backgroundColor: 'var(--color-bg-secondary)' }"></div>
        <div class="h-4 rounded w-3/4" :style="{ backgroundColor: 'var(--color-bg-secondary)' }"></div>
      </div>
    </div>

    <!-- Error -->
    <ClientOnly>
      <div v-if="error" class="rounded-lg p-6 text-center" :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }">
        <p class="text-red-500 mb-2">{{ t('about.loadError') }}</p>
        <p :style="{ color: 'var(--color-text-tertiary)' }" class="text-sm">{{ t('about.loadErrorHint') }}</p>
      </div>
    </ClientOnly>

    <template v-if="!loading && !error">
      <HeroBanner>
        <p
          v-if="quoteText"
          class="mt-4 text-sm italic"
          :style="{ color: 'var(--color-text-tertiary)' }"
        >&ldquo;{{ quoteText }}&rdquo;</p>
      </HeroBanner>

      <!-- Intro -->
      <AboutCard v-if="introText" class="mb-6" :accent="true" :delay="100">
        <p class="text-base leading-relaxed" :style="{ color: 'var(--color-text-primary)' }">
          {{ introText }}
        </p>
      </AboutCard>

      <!-- Tech Stack — frameless section -->
      <div class="tech-section mb-6">
        <div
          v-for="(cat, ci) in techCategories"
          :key="cat.label"
          class="tech-group"
          :style="{ animationDelay: (ci * 80) + 'ms' }"
        >
          <span class="tech-label" :style="{ color: 'var(--color-accent, #ff643e)' }">{{ cat.label }}</span>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="pill in cat.items"
              :key="pill"
              class="tech-pill px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200"
              :style="{
                background: 'var(--color-bg-tertiary)',
                color: 'var(--color-text-primary)',
                borderLeft: '2px solid var(--color-accent, #ff643e)'
              }"
            >{{ pill }}</span>
          </div>
        </div>
      </div>

      <!-- Card grid -->
      <div class="bento-grid">
        <!-- Row 1: Projects | Currently -->
        <AboutCard v-if="projectItems.length" :title="t('about.card.projects')" :delay="300">
          <div class="space-y-4">
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
        </AboutCard>

        <AboutCard
          v-if="currentlyItems.length"
          :title="t('about.card.currently')"
          :delay="350"
        >
          <div class="space-y-2">
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
        </AboutCard>

        <!-- Row 4: Beyond Code | Contact -->
        <AboutCard
          :title="t('about.card.beyondCode')"
          :summary="t('about.card.beyondCodeSummary')"
          :expandable="true"
          :delay="400"
        >
          <div
            class="section-content text-sm leading-relaxed"
            :style="{ color: 'var(--color-text-primary)' }"
            v-html="bySlug['what']?.content || ''"
          ></div>
        </AboutCard>

        <AboutCard
          :title="t('about.card.contact')"
          :delay="450"
        >
          <div
            class="section-content text-sm leading-relaxed"
            :style="{ color: 'var(--color-text-primary)' }"
            v-html="bySlug['where']?.content || ''"
          ></div>
        </AboutCard>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* Bento layout */
.bento-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  align-items: start;
}

@media (min-width: 768px) {
  .bento-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Tech section — frameless, accent dividers */
.tech-section {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem 2rem;
  padding: 1.25rem 0;
}
.tech-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.tech-group .flex {
  flex-wrap: wrap;
}
.tech-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

/* Section content styles */
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

/* Tech pills */
.tech-pill:hover {
  background: color-mix(in srgb, var(--color-accent, #ff643e) 15%, var(--color-bg-tertiary)) !important;
  transform: translateY(-1px);
}

/* Project items */
.project-item {
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: var(--color-bg-tertiary);
  transition: transform 0.2s ease;
}
.project-item:hover {
  transform: translateX(4px);
}
</style>
