<script setup>
import { useI18n } from '../composables/useI18n.js'

const { locale, setLocale } = useI18n()

function toggle() {
  setLocale(locale.value === 'fi' ? 'en' : 'fi')
}
</script>

<template>
  <button
    @click="toggle"
    class="px-2 py-1 rounded text-xs font-medium transition-colors duration-200 hover:bg-white/10"
    :style="{ color: 'var(--color-text-secondary)', border: '1px solid rgba(255,255,255,0.15)' }"
    :aria-label="locale === 'fi' ? 'Switch to English' : 'Vaihda suomeksi'"
  >
    {{ locale === 'fi' ? 'EN' : 'FI' }}
  </button>
</template>
