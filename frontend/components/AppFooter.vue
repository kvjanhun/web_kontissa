<script setup>
const { t } = useI18nStore()

defineProps({
  updateDate: { type: String, default: '' }
})
</script>

<template>
  <footer
    :style="{
      backgroundColor: 'var(--color-bg-primary)',
    }"
  >
    <div class="max-w-3xl mx-auto px-6 py-5">
      <!-- Row 1: nav links -->
      <nav class="flex flex-wrap gap-x-5 gap-y-2 text-sm mb-3" aria-label="Footer">
        <NuxtLink to="/" class="transition-colors hover:opacity-80" :style="{ color: 'var(--color-text-secondary)' }">{{ t('nav.home') }}</NuxtLink>
        <a href="https://sanakenno.fi" target="_blank" rel="noopener" class="transition-colors hover:opacity-80" :style="{ color: 'var(--color-text-secondary)' }">{{ t('nav.sanakenno') }}</a>
      </nav>

      <!-- Row 2: last updated -->
      <div class="text-sm" :style="{ color: 'var(--color-accent, #ff643e)' }">
        <span v-if="updateDate">{{ t('footer.lastUpdated', { date: updateDate }) }}</span>
      </div>
    </div>
  </footer>
</template>
