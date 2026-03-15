<script setup>
const i18nStore = useI18nStore()
const { locale } = storeToRefs(i18nStore)
const { setLocale } = i18nStore

function toggle() {
  setLocale(locale.value === 'fi' ? 'en' : 'fi')
}
</script>

<template>
  <button
    @click="toggle"
    class="px-2 py-1 rounded text-xs font-bold tracking-wide transition-colors duration-200 hover:opacity-80"
    :style="{ color: 'var(--color-accent, #ff643e)', border: '1px solid var(--color-accent, #ff643e)' }"
    :aria-label="locale === 'fi' ? 'Switch to English' : 'Vaihda suomeksi'"
  >
    {{ locale === 'fi' ? 'EN' : 'FI' }}
  </button>
</template>
