<script setup>
defineProps({
  updateDate: { type: String, default: '' }
})
</script>

<template>
  <footer class="px-6 py-6" :style="{ backgroundColor: 'var(--color-bg-secondary)', borderTop: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }">
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 text-sm">
      <div>
        <span v-if="updateDate">Last updated: {{ updateDate }}</span>
      </div>
      <nav class="flex gap-4">
        <router-link to="/about" class="hover:!text-accent" :style="{ color: 'var(--color-text-tertiary)' }">About</router-link>
        <router-link to="/contact" class="hover:!text-accent" :style="{ color: 'var(--color-text-tertiary)' }">Contact</router-link>
      </nav>
    </div>
  </footer>
</template>
