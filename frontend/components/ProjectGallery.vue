<script setup>
const projects = [
  {
    slug: 'sanakenno',
    name: 'Sanakenno',
    tagline: 'Finnish word puzzle — NYT Spelling Bee inspired',
    description:
      'Daily Finnish word puzzles with scoring, streaks, and PWA offline support. Nuxt 3 + Flask + SQLite, BDD-first test suite.',
    image: '/projects/sanakenno/hero.png',
    live: 'https://sanakenno.fi',
    github: 'https://github.com/kvjanhun/sanakenno',
  },
  {
    slug: 'sanakenno-admin',
    name: 'Sanakenno admin',
    tagline: 'Puzzle curation and player ops',
    description:
      'Private admin panel for generating daily puzzles, managing word lists, and inspecting player stats and combinations.',
    image: '/projects/sanakenno-admin/hero.png',
  },
  {
    slug: 'site-admin',
    name: 'erez.ac admin',
    tagline: 'Portfolio CMS and server ops',
    description:
      'Admin panel for this site: editing sections, managing recipes, page views analytics, and server health checks.',
    image: '/projects/site-admin/hero.png',
  },
]

const selectedIndex = ref(0)
const selected = computed(() => projects[selectedIndex.value])
</script>

<template>
  <section class="gallery" aria-label="Project gallery">
    <header class="gallery__label">// gallery</header>

    <div class="highlight">
      <div class="highlight__image">
        <img :src="selected.image" :alt="selected.name + ' screenshot'" />
      </div>

      <div class="highlight__meta">
        <h3 class="highlight__name">{{ selected.name }}</h3>
        <p class="highlight__tagline">{{ selected.tagline }}</p>
        <p class="highlight__desc">{{ selected.description }}</p>
        <div class="highlight__links">
          <a
            v-if="selected.live"
            :href="selected.live"
            target="_blank"
            rel="noopener"
            class="highlight__link"
          >
            <span>live</span><span class="highlight__arrow">→</span>
          </a>
          <a
            v-if="selected.github"
            :href="selected.github"
            target="_blank"
            rel="noopener"
            class="highlight__link"
          >
            <span>github</span><span class="highlight__arrow">→</span>
          </a>
        </div>
      </div>
    </div>

    <div class="thumbs" role="tablist" aria-label="Projects">
      <button
        v-for="(p, i) in projects"
        :key="p.slug"
        class="thumb"
        :class="{ 'thumb--active': i === selectedIndex }"
        role="tab"
        :aria-selected="i === selectedIndex"
        :aria-label="p.name"
        @click="selectedIndex = i"
      >
        <span class="thumb__image">
          <img :src="p.image" :alt="''" />
        </span>
        <span class="thumb__name">{{ p.name }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.gallery {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  height: 100%;
  min-height: 0;
  border: 1px solid rgba(255, 100, 62, 0.35);
  border-radius: 16px;
  background: var(--color-bg-secondary);
  padding: 1rem 1rem 0.9rem;
}

.gallery__label {
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

.highlight {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
}

.highlight__image {
  width: 100%;
  aspect-ratio: 16 / 10;
  border: 1px solid rgba(255, 100, 62, 0.25);
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}
.highlight__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.highlight__meta {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.highlight__name {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: 0.01em;
}

.highlight__tagline {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--color-accent);
}

.highlight__desc {
  margin: 0;
  font-family: var(--font-sans);
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.highlight__links {
  display: flex;
  gap: 0.9rem;
  margin-top: 0.15rem;
}
.highlight__link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  color: var(--color-text-primary);
  text-decoration: none;
}
.highlight__link:hover { color: var(--color-accent); }
.highlight__link:hover .highlight__arrow { transform: translateX(2px); }
.highlight__arrow {
  color: var(--color-accent);
  transition: transform 0.15s ease;
}

.thumbs {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
  gap: 0.5rem;
}

.thumb {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.4rem;
  border-radius: 8px;
  border: 1px solid rgba(255, 100, 62, 0.2);
  background: var(--color-bg-primary);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, transform 0.15s ease;
  font-family: var(--font-mono);
}
.thumb:hover {
  border-color: rgba(255, 100, 62, 0.55);
  color: var(--color-text-primary);
}
.thumb--active {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.thumb__image {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 4px;
  overflow: hidden;
  background: var(--color-bg-secondary);
}
.thumb__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb__name {
  font-size: 0.7rem;
  letter-spacing: 0.02em;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
