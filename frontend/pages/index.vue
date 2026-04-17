<script setup>
definePageMeta({
  layout: 'standalone',
  titleKey: 'title.home',
})

const i18nStore = useI18nStore()
const { t } = i18nStore
const { locale } = storeToRefs(i18nStore)

useHead({
  title: computed(() => t('home.metaTitle')),
  meta: [
    { name: 'description', content: computed(() => t('home.metaDescription')) },
  ],
})

// Fetch sections for the side panel (localized)
const { data: sections, refresh } = await useAsyncData(
  'home-sections',
  () => $fetch('/api/sections', { query: { locale: locale.value } }),
  { default: () => [], watch: [locale] }
)

// Tech pills are language-independent — always fetch from EN.
const { data: enSections, refresh: refreshEn } = await useFetch('/api/sections', {
  key: 'home-sections-en',
  query: { locale: 'en' },
  default: () => [],
})

// SSG: retry after mount (API not running at build time)
onMounted(async () => {
  if (!sections.value.length) {
    await Promise.all([refresh(), refreshEn()])
  }
})

const byType = computed(() => {
  const map = {}
  for (const s of sections.value) map[s.section_type] = map[s.section_type] || s
  return map
})

const bySlug = computed(() => {
  const map = {}
  for (const s of sections.value) map[s.slug] = s
  return map
})

// Tech pills: all pills sections, ordered
const techCategories = computed(() =>
  enSections.value
    .filter(s => s.section_type === 'pills')
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
    .map(s => ({
      label: t(`about.tech.${s.slug}`) || s.title,
      items: s.content.split(',').map(i => i.trim()).filter(Boolean),
    }))
    .filter(c => c.items.length)
)

// Projects — content format: "Name|url|description|icon" per line
const projects = computed(() => {
  const raw = sections.value.find(s => s.section_type === 'project')?.content || ''
  return raw.split('\n').map(line => {
    const [name, url, desc] = line.split('|')
    return { name: name?.trim(), url: url?.trim(), desc: desc?.trim() }
  }).filter(p => p.name)
})

const intro = computed(() => byType.value['intro']?.content || '')
const contact = computed(() => bySlug.value['where']?.content || '')

// Simple markdown-ish link parser: [text](url)
function renderLinks(text) {
  if (!text) return ''
  return text
    .replace(/</g, '&lt;')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) =>
      `<a href="${url}" class="contact-link">${label}</a>`
    )
}
</script>

<template>
  <div class="home-root">
    <!-- Floating top-right controls -->
    <div class="home-controls">
      <LangToggle />
      <ThemeToggle />
    </div>

    <div class="home-grid">
      <!-- Terminal pane (left on desktop, top on mobile) -->
      <section class="term-pane" aria-label="Terminal">
        <div class="term-frame">
          <!-- ASCII banner -->
          <pre class="term-banner" aria-label="erez.ac">███████╗██████╗ ███████╗███████╗    █████╗  ██████╗
██╔════╝██╔══██╗██╔════╝╚══███╔╝   ██╔══██╗██╔════╝
█████╗  ██████╔╝█████╗    ███╔╝    ███████║██║
██╔══╝  ██╔══██╗██╔══╝   ███╔╝  ▄  ██╔══██║██║
███████╗██║  ██║███████╗███████╗ ▀ ██║  ██║╚██████╗
╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝  ╚═╝ ╚═════╝</pre>

          <!-- Interactive terminal -->
          <div class="term-live">
            <TerminalWindow :fill="true" />
          </div>
        </div>
      </section>

      <!-- Info panels -->
      <aside class="info-pane" aria-label="About">
        <article class="card">
          <header class="card__label">// whoami</header>
          <p v-if="intro" class="card__body">{{ intro }}</p>
          <p v-else class="card__body card__body--muted">—</p>
        </article>

        <article class="card">
          <header class="card__label">// stack</header>
          <div class="stack-list">
            <div v-for="cat in techCategories" :key="cat.label" class="stack-row">
              <span class="stack-label">{{ cat.label.toLowerCase() }}</span>
              <span class="stack-items">{{ cat.items.join(' · ') }}</span>
            </div>
          </div>
        </article>

        <article class="card">
          <header class="card__label">// projects</header>
          <ul class="proj-list">
            <li v-for="p in projects" :key="p.name">
              <a v-if="p.url" :href="p.url" class="proj-link">
                <span class="proj-name">{{ p.name }}</span>
                <span class="proj-arrow">→</span>
              </a>
              <span v-else class="proj-name">{{ p.name }}</span>
              <span v-if="p.desc" class="proj-desc">{{ p.desc }}</span>
            </li>
          </ul>
        </article>

        <article class="card">
          <header class="card__label">// ping</header>
          <p class="card__body card__body--contact" v-html="renderLinks(contact)"></p>
        </article>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.home-root {
  min-height: 100vh;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  padding: 1rem;
  box-sizing: border-box;
  position: relative;
}

@media (min-width: 1024px) {
  .home-root {
    height: 100vh;
    max-height: 100vh;
    overflow: hidden;
    padding: 1.25rem;
  }
}

.home-controls {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  gap: 0.25rem;
  z-index: 30;
}

@media (min-width: 1024px) {
  .home-controls {
    top: 1.5rem;
    right: 1.75rem;
  }
}

.home-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: 1fr;
  min-height: calc(100vh - 2rem);
}

@media (min-width: 1024px) {
  .home-grid {
    grid-template-columns: minmax(0, 1fr) minmax(18rem, 22rem);
    height: 100%;
    min-height: 0;
    gap: 1.5rem;
  }
}

/* Terminal pane */
.term-pane {
  display: flex;
  min-height: 0;
}
.term-frame {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 380px;
  background: var(--color-term-bg);
  border-radius: 8px;
  overflow: hidden;
  padding: 1.25rem 0.5rem 0.25rem;
  box-shadow: 0 0 0 1px rgba(255, 100, 62, 0.12), 0 10px 30px rgba(0,0,0,0.25);
}

@media (min-width: 1024px) {
  .term-frame {
    min-height: 0;
    height: 100%;
  }
}

.term-banner {
  font-family: var(--font-mono);
  font-size: clamp(7px, 2vw, 12px);
  line-height: 1.05;
  margin: 0 0 0.9rem;
  padding: 0 1rem;
  white-space: pre;
  overflow: hidden;
  color: transparent;
  background: linear-gradient(120deg, #ff643e 0%, #ffb43c 55%, #ff643e 100%);
  -webkit-background-clip: text;
  background-clip: text;
  text-shadow: 0 0 0 transparent;
  user-select: none;
  letter-spacing: 0;
}

@media (min-width: 1024px) {
  .term-banner {
    font-size: clamp(11px, 1.5vw, 18px);
  }
}

.term-live {
  flex: 1;
  min-height: 0;
  display: flex;
}
.term-live > * {
  flex: 1;
  min-height: 0;
}

/* Info pane */
.info-pane {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 0;
  padding-top: 0.75rem;
}

@media (min-width: 1024px) {
  .info-pane {
    height: 100%;
    overflow-y: auto;
    padding-top: 2.75rem;
    padding-right: 0.25rem;
    scrollbar-width: thin;
  }
}

.card {
  position: relative;
  border: 1px solid var(--color-border);
  border-top-color: var(--color-accent);
  background: var(--color-bg-secondary);
  padding: 1rem 1rem 0.9rem;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.card__label {
  position: absolute;
  top: -0.65rem;
  left: 0.85rem;
  padding: 0 0.45rem;
  background: var(--color-bg-primary);
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.03em;
}

.card__body {
  margin: 0;
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  font-size: 0.9rem;
  line-height: 1.55;
}
.card__body--muted { color: var(--color-text-tertiary); }
.card__body--contact :deep(.contact-link) {
  color: var(--color-accent);
}
.card__body--contact :deep(.contact-link:hover) {
  text-decoration: underline;
}

/* Stack list */
.stack-list { display: flex; flex-direction: column; gap: 0.4rem; }
.stack-row {
  display: grid;
  grid-template-columns: 6.5rem 1fr;
  gap: 0.75rem;
  align-items: baseline;
}
.stack-label {
  color: var(--color-accent);
  font-size: 0.75rem;
  text-transform: lowercase;
}
.stack-items {
  color: var(--color-text-primary);
  font-size: 0.82rem;
}

/* Projects */
.proj-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.proj-list li {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.proj-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 0.88rem;
  font-weight: 500;
  width: fit-content;
}
.proj-link:hover { color: var(--color-accent); }
.proj-link:hover .proj-arrow { transform: translateX(2px); }
.proj-name { font-family: var(--font-mono); font-size: 0.88rem; color: var(--color-text-primary); }
.proj-arrow {
  color: var(--color-accent);
  transition: transform 0.15s ease;
}
.proj-desc {
  font-family: var(--font-sans);
  color: var(--color-text-secondary);
  font-size: 0.78rem;
  line-height: 1.45;
}
</style>
