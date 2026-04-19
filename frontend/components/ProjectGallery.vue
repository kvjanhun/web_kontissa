<script setup>
import VueEasyLightbox from 'vue-easy-lightbox'

const { t } = useI18nStore()

const projects = computed(() => [
  {
    slug: 'sanakenno',
    name: t('gallery.sanakenno.name'),
    tagline: t('gallery.sanakenno.tagline'),
    description: t('gallery.sanakenno.description'),
    image: '/projects/sanakenno/hero.png',
    live: 'https://sanakenno.fi',
    github: 'https://github.com/kvjanhun/sanakenno',
  },
  {
    slug: 'sanakenno-admin',
    name: t('gallery.sanakennoAdmin.name'),
    tagline: t('gallery.sanakennoAdmin.tagline'),
    description: t('gallery.sanakennoAdmin.description'),
    image: '/projects/sanakenno-admin/hero.png',
  },
  {
    slug: 'site-admin',
    name: t('gallery.siteAdmin.name'),
    tagline: t('gallery.siteAdmin.tagline'),
    description: t('gallery.siteAdmin.description'),
    image: '/projects/site-admin/hero.png',
  },
])

const selectedIndex = ref(0)
const selected = computed(() => projects.value[selectedIndex.value])

const lightboxVisible = ref(false)
const lightboxImgs = computed(() =>
  projects.value.map(p => ({
    src: p.image,
    title: p.name,
    alt: t('gallery.screenshotAlt', { name: p.name }),
  }))
)
</script>

<template>
  <section class="gallery" :aria-label="t('gallery.sectionLabel')">
    <header class="gallery__label">// gallery</header>

    <div class="highlight">
      <button
        type="button"
        class="highlight__image"
        :aria-label="t('gallery.screenshotAlt', { name: selected.name })"
        @click="lightboxVisible = true"
      >
        <img :src="selected.image" :alt="t('gallery.screenshotAlt', { name: selected.name })" />
      </button>

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
            <span>{{ t('gallery.live') }}</span><span class="highlight__arrow">→</span>
          </a>
          <a
            v-if="selected.github"
            :href="selected.github"
            target="_blank"
            rel="noopener"
            class="highlight__link"
          >
            <span>{{ t('gallery.github') }}</span><span class="highlight__arrow">→</span>
          </a>
        </div>
      </div>
    </div>

    <div class="thumbs" role="tablist" :aria-label="t('gallery.projectsLabel')">
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

    <ClientOnly>
      <VueEasyLightbox
        teleport="body"
        :visible="lightboxVisible"
        :imgs="lightboxImgs"
        :index="selectedIndex"
        move-disabled
        rotate-disabled
        @hide="lightboxVisible = false"
        @index-change="i => (selectedIndex = i)"
      />
    </ClientOnly>
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
  top: -1.4rem;
  left: 0.85rem;
  padding: 0;
  background: transparent;
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 500;
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
  padding: 0;
  cursor: zoom-in;
  transition: border-color 0.15s ease, transform 0.15s ease;
}
.highlight__image:hover {
  border-color: rgba(255, 100, 62, 0.55);
}
.highlight__image:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
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
  font-size: 0.8125rem;
  color: var(--color-accent);
}

.highlight__desc {
  margin: 0;
  font-family: var(--font-sans);
  font-size: 0.875rem;
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
  font-size: 0.875rem;
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
  font-size: 0.75rem;
  letter-spacing: 0.02em;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

<style>
/* Cap the teleported lightbox image at terminal width (60rem) */
.vel-img-modal .vel-img {
  max-width: min(100%, 60rem) !important;
  max-height: 90vh;
  object-fit: contain;
}
</style>
