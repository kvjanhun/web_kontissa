<script setup>
const darkModeStore = useDarkModeStore()
const { isDark } = storeToRefs(darkModeStore)
const { toggleDark } = darkModeStore
const { t } = useI18nStore()
</script>

<template>
  <button
    @click="toggleDark"
    class="p-2 rounded-lg transition-colors duration-200 hover:opacity-80"
    :style="{ color: 'var(--color-accent, #ff643e)' }"
    :aria-label="isDark ? t('theme.switchToLight') : t('theme.switchToDark')"
    :aria-pressed="isDark"
  >
    <!-- Sun shown in dark mode (click → light), moon shown in light mode (click → dark) -->
    <Icon class="size-5" :name="isDark ? 'solar:sun-2-bold' : 'solar:moon-bold'" aria-hidden="true" />
  </button>
</template>
