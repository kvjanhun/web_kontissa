<script setup>
const { t } = useI18nStore()

defineProps({
  updateDate: { type: String, default: '' }
})
</script>

<template>
  <footer
    class="px-6 py-5"
    :style="{
      backgroundColor: 'var(--color-bg-primary)',
    }"
  >
    <!-- Row 1: nav links -->
    <nav class="flex flex-wrap gap-x-5 gap-y-2 text-sm mb-3" aria-label="Footer">
      <NuxtLink to="/about" class="transition-colors hover:opacity-80" :style="{ color: 'var(--color-text-secondary)' }">{{ t('nav.about') }}</NuxtLink>
      <NuxtLink to="/contact" class="transition-colors hover:opacity-80" :style="{ color: 'var(--color-text-secondary)' }">{{ t('nav.contact') }}</NuxtLink>
      <NuxtLink to="/sanakenno" class="transition-colors hover:opacity-80" :style="{ color: 'var(--color-text-secondary)' }">{{ t('nav.sanakenno') }}</NuxtLink>
    </nav>

    <!-- Row 2: last updated -->
    <div class="text-sm" :style="{ color: 'var(--color-accent, #ff643e)' }">
      <span v-if="updateDate">{{ t('footer.lastUpdated', { date: updateDate }) }}</span>
    </div>
  </footer>
</template>
