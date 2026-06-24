<script setup>
const i18n = useI18nStore()
const { t, tm } = i18n

const taglines = computed(() => tm('home.hero.taglines') || [])
const index = ref(0)

// Render the tagline in normal text colour with only a trailing "." accented
// orange (the hero's signature dot).
const currentTagline = computed(() => taglines.value[index.value] || '')
const taglineBody = computed(() => currentTagline.value.replace(/\.$/, ''))
const taglineDot = computed(() => (currentTagline.value.endsWith('.') ? '.' : ''))

// Cycle through the taglines: each holds for a beat, slides out left, and the
// next slides in from the right (driven by the <Transition> below).
//
// Under prefers-reduced-motion the carousel is disabled entirely: instead we
// pick a single tagline at random on page load (as the original site did) and
// leave it static — no sliding, no timer.
let timer = null
onMounted(() => {
  if (typeof window === 'undefined') return
  if (taglines.value.length <= 1) return

  const prefersReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (prefersReduced) {
    index.value = Math.floor(Math.random() * taglines.value.length)
    return
  }

  timer = setInterval(() => {
    index.value = (index.value + 1) % taglines.value.length
  }, 4300)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <section class="hero">
    <div class="hero__eyebrow">
      <span class="hero__dot" aria-hidden="true"></span>
      <span class="hero__eyebrow-text">{{ t('home.hero.eyebrow') }}</span>
    </div>
    <h1 class="hero__title">
      <span class="hero__tagline-track">
        <Transition name="tagline" mode="out-in">
          <span :key="index" class="hero__tagline-text">{{ taglineBody }}<span class="hero__accent">{{ taglineDot }}</span></span>
        </Transition>
      </span>
      <span class="hero__line2">{{ t('home.hero.titleLine2') }}</span>
    </h1>
    <p class="hero__body">{{ t('home.hero.body') }}</p>
    <div class="hero__cta">
      <a href="#work" class="cta cta--primary">{{ t('home.hero.ctaPrimary') }} <span aria-hidden="true">→</span></a>
      <a href="#stack" class="cta cta--ghost">{{ t('home.hero.ctaSecondary') }}</a>
    </div>
  </section>
</template>

<style scoped>
.hero {
  padding: 104px 0 84px;
  border-bottom: 1px solid var(--line);
}
.hero__eyebrow {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 30px;
}
.hero__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 12px var(--accent);
  flex: none;
}
.hero__eyebrow-text {
  font-family: var(--font-plex-mono);
  font-size: 12px;
  color: var(--tx-2);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  line-height: 1.3;
}
.hero__title {
  margin: 0;
  font-size: clamp(40px, 6.4vw, 80px);
  line-height: 1.02;
  font-weight: 600;
  letter-spacing: -0.03em;
}
/* Rotating tagline: one fixed-height line so the layout below never jumps.
   The text is a full-width block, so translateX(±100%) carries it fully off
   the right/left edges; overflow:hidden clips the horizontal travel. The height
   / line-height leave room for descenders (g, p, j) so they aren't cropped. */
.hero__tagline-track {
  display: block;
  overflow: hidden;
  line-height: 1.35;
  height: 1.35em;
}
.hero__tagline-text {
  display: block;
  white-space: nowrap;
  line-height: 1.35;
  color: var(--tx);
}
.hero__accent {
  color: var(--accent);
}
.hero__line2 {
  display: block;
}
.tagline-enter-active {
  transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.tagline-leave-active {
  transition: transform 0.3s cubic-bezier(0.7, 0, 0.84, 0);
}
.tagline-enter-from {
  transform: translateX(100%);
}
.tagline-leave-to {
  transform: translateX(-100%);
}
.hero__body {
  margin: 34px 0 0;
  max-width: 60ch;
  font-size: clamp(16px, 1.8vw, 19px);
  line-height: 1.6;
  color: var(--tx-2);
  font-weight: 300;
}
.hero__cta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 40px;
}
.cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  font-family: var(--font-plex-mono);
  font-size: 13px;
  font-weight: 500;
  padding: 13px 22px;
  border-radius: 8px;
  letter-spacing: 0.02em;
  transition: opacity 0.15s ease, border-color 0.15s ease;
}
.cta--primary {
  background: var(--accent);
  color: #fff;
}
.cta--primary:hover { opacity: 0.9; }
.cta--ghost {
  background: transparent;
  color: var(--tx);
  border: 1px solid var(--line);
}
.cta--ghost:hover { border-color: var(--tx-3); }

@media (max-width: 720px) {
  .hero { padding: 34px 0 40px; }
  .hero__eyebrow { margin-bottom: 22px; }
  .hero__body { margin-top: 24px; }
  .hero__cta {
    flex-direction: column;
    margin-top: 28px;
  }
  .cta {
    justify-content: center;
    padding: 13px;
  }
}
</style>
