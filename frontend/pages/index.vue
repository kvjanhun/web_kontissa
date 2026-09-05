<script setup>
definePageMeta({
  layout: 'standalone',
  titleKey: 'title.home',
})

const i18n = useI18nStore()
const { t, loadHomeContent } = i18n
const { locale } = storeToRefs(i18n)

// Social cards follow the visitor's locale: without the og:* overrides here the
// share preview would keep the English defaults from nuxt.config.ts regardless of
// what the page actually says.
useHead({
  title: computed(() => t('home.metaTitle')),
  // Preloaded here rather than in nuxt.config.ts: IBM Plex Sans is this page's
  // body font, and no other page uses it. Without the hint the browser only
  // discovers it after matching the CSS, and font-display: swap paints the
  // system-ui fallback first — whose metrics differ enough to reflow the page.
  link: [
    {
      rel: 'preload',
      as: 'font',
      type: 'font/woff2',
      href: '/fonts/ibm-plex-sans-latin.woff2',
      crossorigin: '',
    },
  ],
  meta: [
    { name: 'description', content: computed(() => t('home.metaDescription')) },
    { property: 'og:title', content: computed(() => t('home.metaTitle')) },
    { property: 'og:description', content: computed(() => t('home.metaDescription')) },
    { property: 'og:locale', content: computed(() => (locale.value === 'fi' ? 'fi_FI' : 'en_US')) },
  ],
})

// The page paints from the build snapshot, then swaps in the live DB content.
// Re-fetch when the visitor switches language so the other locale is fresh too.
onMounted(() => loadHomeContent())
watch(locale, (loc) => loadHomeContent(loc))
</script>

<template>
  <div class="home-dc">
    <a href="#top" class="home-skip">{{ t('home.skipToContent') }}</a>
    <HomeHeader />
    <main id="top" class="home-main">
      <HomeHero />
      <HomeWork />
      <HomeStack />
      <HomeTerminal />
    </main>
    <HomeFooter />
  </div>
</template>

<style scoped>
.home-dc {
  min-height: 100vh;
  /* Clip horizontal overflow: the readability plates (.home-plate::before) feather
     ~0.9em past their text box, which exceeds the page's 18px mobile padding on the
     large hero title and pokes a few transparent px past the viewport — producing a
     phantom horizontal scroll that reveals nothing. overflow-x: clip (not hidden)
     removes it without creating a scroll container, so the sticky header and the
     terminal's inner scroll are unaffected; only the invisible feather tail is cut. */
  overflow-x: clip;
  background: var(--bg);
  color: var(--tx);
  font-family: var(--font-plex-sans);
  background-image:
    linear-gradient(var(--grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid) 1px, transparent 1px);
  background-size: 64px 64px;
}

.home-main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 28px;
}

/* Offset in-page anchor jumps so the sticky header doesn't cover the heading */
.home-main :deep(section[id]) {
  scroll-margin-top: 84px;
}

.home-skip {
  position: absolute;
  left: 16px;
  top: -100%;
  z-index: 100;
  background: var(--accent);
  color: #fff;
  padding: 8px 16px;
  border-radius: 8px;
  font-family: var(--font-plex-mono);
  font-size: 13px;
}
.home-skip:focus { top: 12px; }

@media (max-width: 720px) {
  .home-dc { background-size: 44px 44px; }
  .home-main { padding: 0 18px; }
}
</style>
