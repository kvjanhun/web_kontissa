<script setup>
defineProps({
  updateDate: { type: String, default: '' }
})
</script>

<template>
  <footer
    class="px-6 py-6"
    :style="{
      backgroundColor: 'var(--color-header-bg)',
      borderTop: '2px solid var(--color-header-border)',
      color: 'var(--color-text-tertiary)'
    }"
  >
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 text-sm">
      <div>
        <span v-if="updateDate" class="text-stone-500">Last updated: {{ updateDate }}</span>
      </div>
      <nav class="flex gap-4">
        <router-link to="/about" class="!text-stone-500 hover:!text-accent">About</router-link>
        <router-link to="/contact" class="!text-stone-500 hover:!text-accent">Contact</router-link>
      </nav>
    </div>
  </footer>
</template>
