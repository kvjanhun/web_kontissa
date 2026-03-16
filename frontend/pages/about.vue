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

const { data: sections, pending, error, refresh } = await useAsyncData(
  'about-sections',
  () => $fetch('/api/sections', { query: { locale: locale.value } }),
  { default: () => [], watch: [locale] }
)

// Tech pills are language-independent — always fetch from EN
const { data: enSections } = await useFetch('/api/sections', {
  key: 'sections-en-tech',
  query: { locale: 'en' },
  default: () => [],
})

const loading = computed(() => (pending.value || retrying.value) && !sections.value.length)

// SSG builds without Flask running, so sections fetch fails at build time.
// Retry after mount (not during setup) to avoid hydration mismatch between
// the empty pre-rendered HTML and client-rendered content.
onMounted(async () => {
  if (!sections.value.length) {
    retrying.value = true
    error.value = null
    await refresh()
    retrying.value = false
  }
})

// Look up sections by type — admin only needs to pick the right type
const byType = computed(() => {
  const map = {}
  for (const s of sections.value) {
    map[s.section_type] = s
  }
  return map
})

// Card sections: project, currently, text — positioned by number ranges
// 0–9 = full-width row, 10–19 = left column, 20–29 = right column
const cardTypes = new Set(['project', 'currently', 'text'])
const cardSections = computed(() =>
  sections.value
    .filter(s => cardTypes.has(s.section_type))
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
)
const fullWidthCards = computed(() => cardSections.value.filter(s => (s.position ?? 0) < 10))
const leftColumnCards = computed(() => cardSections.value.filter(s => (s.position ?? 0) >= 10 && (s.position ?? 0) < 20))
const rightColumnCards = computed(() => cardSections.value.filter(s => (s.position ?? 0) >= 20 && (s.position ?? 0) < 30))

const enByType = computed(() => {
  const map = {}
  for (const s of enSections.value) map[s.section_type] = s
  return map
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

      <!-- Full-width cards (position 0–9) -->
      <div v-if="fullWidthCards.length" class="space-y-4 mb-4">
        <AboutSectionCard
          v-for="(section, i) in fullWidthCards"
          :key="section.id"
          :section="section"
          :delay="300 + i * 50"
        />
      </div>

      <!-- Two-column grid (position 10–19 left, 20–29 right) -->
      <div v-if="leftColumnCards.length || rightColumnCards.length" class="bento-grid">
        <div class="space-y-4">
          <AboutSectionCard
            v-for="(section, i) in leftColumnCards"
            :key="section.id"
            :section="section"
            :delay="400 + i * 50"
          />
        </div>
        <div class="space-y-4">
          <AboutSectionCard
            v-for="(section, i) in rightColumnCards"
            :key="section.id"
            :section="section"
            :delay="400 + i * 50"
          />
        </div>
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

/* Tech pills */
.tech-pill:hover {
  background: color-mix(in srgb, var(--color-accent, #ff643e) 15%, var(--color-bg-tertiary)) !important;
  transform: translateY(-1px);
}

</style>
