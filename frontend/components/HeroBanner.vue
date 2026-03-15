<script setup>
const { t } = useI18nStore()

const TAGLINE_KEYS = [
  'hero.tagline.1',
  'hero.tagline.2',
  'hero.tagline.3',
  'hero.tagline.4',
  'hero.tagline.5',
]

const taglineKey = TAGLINE_KEYS[Math.floor(Math.random() * TAGLINE_KEYS.length)]
</script>

<template>
  <div class="hero mb-8">
    <div class="flex flex-col items-center md:flex-row md:items-start md:gap-8 md:justify-center">
      <div class="mb-5 md:mb-0 shrink-0" aria-hidden="true">
        <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
          <rect x="10" y="10" width="100" height="100" rx="16" fill="var(--color-text-primary)" opacity="0.06"/>
          <path d="M45 40L25 60L45 80" stroke="var(--color-accent, #ff643e)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M75 40L95 60L75 80" stroke="var(--color-accent, #ff643e)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="65" y1="32" x2="55" y2="88" stroke="var(--color-text-primary)" stroke-width="3" stroke-linecap="round" opacity="0.4"/>
        </svg>
      </div>

      <div class="text-center md:text-left max-w-sm">
        <p class="text-sm font-semibold tracking-widest uppercase mb-2" :style="{ color: 'var(--color-accent, #ff643e)' }">
          {{ t('about.heroLabel') }}
        </p>
        <h1 class="hero-name text-4xl md:text-5xl font-bold mb-3">Konsta Janhunen</h1>
        <p class="text-lg md:text-xl font-light" :style="{ color: 'var(--color-text-secondary)' }">
          {{ t(taglineKey) }}
        </p>
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.hero-name {
  background: linear-gradient(135deg, var(--color-text-primary) 0%, var(--color-accent, #ff643e) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
</style>
