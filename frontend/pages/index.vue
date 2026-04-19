<script setup>
definePageMeta({
  layout: 'standalone',
  titleKey: 'title.home',
})

const i18nStore = useI18nStore()
const { t } = i18nStore
const { locale } = storeToRefs(i18nStore)

// Banner kept as a JS array so text interpolation preserves consecutive spaces
// (Vue's template compiler condenses whitespace inside inline template text).
const bannerRows = [
' ▄▄▄▖▗▄▄▖ ▗▄▄▄▖▗▄▄▄▖  ▗▄▖  ▗▄▄▖',
'▐▌   ▐▌ ▐▌▐▌      ▞▘ ▐▌ ▐▌▐▌   ',
'▐▛▀▀▘▐▛▀▚▖▐▛▀▀▘ ▗▞   ▐▛▀▜▌▐▌   ',
'▐▙▄▄▖▐▌ ▐▌▐▙▄▄▖▐▙▄▄▖▄▐▌ ▐▌▝▚▄▄▖',
 '▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁',
 '▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔',
]

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

// SSG: retry after mount (API not running at build time)
onMounted(async () => {
  if (!sections.value.length) {
    await refresh()
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

// Projects — content format: "Name|url|description|icon" per line
const projects = computed(() => {
  const raw = sections.value.find(s => s.section_type === 'project')?.content || ''
  return raw.split('\n').map(line => {
    const [name, url, desc] = line.split('|')
    return { name: name?.trim(), url: url?.trim(), desc: desc?.trim() }
  }).filter(p => p.name)
})

const intro = computed(() => byType.value['intro']?.content || '')
const contact = computed(() => bySlug.value['contact']?.content || '')

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
    <div class="home-content">
      <section class="term-pane" aria-label="Terminal">
        <div class="term-frame">
          <div class="term-toggles">
            <ThemeToggle />
            <LangToggle />
          </div>

          <div class="term-banner" aria-label="erez.ac">
            <span v-for="(row, i) in bannerRows" :key="i" class="term-banner__row">{{ row }}</span>
          </div>

          <div class="term-live">
            <TerminalWindow :fill="true" />
          </div>
        </div>
      </section>

      <div class="home-below">
        <aside class="info-pane" aria-label="About">
          <article class="card">
            <header class="card__label">// whoami</header>
            <p v-if="intro" class="card__body">{{ intro }}</p>
            <p v-else class="card__body card__body--muted">—</p>
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

        <ProjectGallery class="home-gallery" />
      </div>
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
    padding: 1.25rem;
  }
}

/* Left-aligned wrapper; cards + gallery share the terminal's max width */
.home-content {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
  min-width: 0;
}

@media (min-width: 1024px) {
  .home-content {
    max-width: 60rem;
    gap: 2rem;
  }
}

/* Row below the terminal: cards (left) + gallery (right) */
.home-below {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1.75rem;
  min-width: 0;
}

@media (min-width: 1024px) {
  .home-below {
    grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
    gap: 1.25rem;
    align-items: stretch;
  }
}

.home-gallery {
  min-width: 0;
}

/* Terminal pane */
.term-pane {
  display: flex;
  min-width: 0;
}
.term-frame {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 424px;
  max-height: calc(100vh - 2rem);
  background: var(--color-term-bg);
  border: 1px solid rgba(255, 100, 62, 0.35);
  border-radius: 12px;
  overflow: hidden;
  padding: 0.75rem 1rem 0.25rem;
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}

@media (min-width: 1024px) {
  .term-frame {
    height: 57vh;
    padding-top: 1.25rem;
  }
}

/* Overlay toggles in the terminal's top-right corner */
.term-toggles {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.35rem;
  z-index: 5;
}

/* Desktop: stack vertically so they take less horizontal space */
@media (min-width: 1024px) {
  .term-toggles {
    top: 1.25rem;
    flex-direction: column;
  }
}

.term-banner {
  /* Single font for the whole banner — avoids mixed-width cells. */
  font-family: Menlo, Consolas, "DejaVu Sans Mono", monospace;
  font-size: clamp(7px, 2vw, 12px);
  line-height: 1;
  margin: 0 0 0.25rem;
  padding: 0;
  overflow: hidden;
  user-select: none;
  letter-spacing: 0;
}
.term-banner__row {
  display: block;
  white-space: pre;
}

@media (min-width: 1024px) {
  .term-banner {
    font-size: clamp(12px, 1.35vw, 17px);
  }
}

/* Classic row-gradient: each row its own hue. */
.term-banner__row:nth-child(1) { color: #8a2a18; text-shadow: 0 0 6px rgba(138, 42, 24, 0.45); }
.term-banner__row:nth-child(2) { color: #c73a1e; text-shadow: 0 0 6px rgba(199, 58, 30, 0.45); }
.term-banner__row:nth-child(3) { color: #ff643e; text-shadow: 0 0 8px rgba(255, 100, 62, 0.55); }
.term-banner__row:nth-child(4) { color: #ff8b3c; text-shadow: 0 0 8px rgba(255, 139, 60, 0.55); }
.term-banner__row:nth-child(5) { color: #ffb43c; text-shadow: 0 0 8px rgba(255, 180, 60, 0.50); }
.term-banner__row:nth-child(6) { color: #c73a1e; text-shadow: 0 0 8px rgba(255, 217, 122, 0.45); }

.term-live {
  flex: 1;
  min-height: 0;
  display: flex;
}
.term-live > * {
  flex: 1;
  min-height: 0;
}
.term-live :deep(.overflow-y-scroll) {
  padding: 0.25rem 1rem 0.25rem 0;
}

/* Info pane (cards column) */
.info-pane {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
  min-width: 0;
}

.card {
  position: relative;
  border: 1px solid rgba(255, 100, 62, 0.35);
  border-radius: 16px;
  background: var(--color-bg-secondary);
  padding: 1rem 1rem 0.9rem;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
  min-width: 0;
}

.card__label {
  position: absolute;
  top: -1.2rem;
  left: 0.85rem;
  padding: 0;
  background: transparent;
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
