<script setup>
import { useI18nStore } from '../stores/i18n.js'

const { t } = useI18nStore()

defineProps({
  updateDate: { type: String, default: '' }
})
</script>

<template>
  <footer
    class="px-6 py-5"
    :style="{
      backgroundColor: 'var(--color-header-bg)',
      borderTop: '2px solid var(--color-header-border)',
    }"
  >
    <!-- Row 1: nav links -->
    <nav class="flex flex-wrap gap-x-5 gap-y-2 text-sm mb-3" aria-label="Footer">
      <router-link to="/about" class="!text-stone-400 hover:!text-accent transition-colors">{{ t('nav.about') }}</router-link>
      <router-link to="/contact" class="!text-stone-400 hover:!text-accent transition-colors">{{ t('nav.contact') }}</router-link>
      <router-link to="/sanakenno" class="!text-stone-400 hover:!text-accent transition-colors">{{ t('nav.sanakenno') }}</router-link>
    </nav>

    <!-- Row 2: last updated -->
    <div class="text-sm" style="color: var(--color-text-tertiary);">
      <span v-if="updateDate">{{ t('footer.lastUpdated', { date: updateDate }) }}</span>
    </div>
  </footer>
</template>
