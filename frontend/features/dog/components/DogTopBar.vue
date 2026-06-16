<script setup>
import ThemeToggle from '../../../components/ThemeToggle.vue'

defineProps({
  currentView: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    default: '',
  },
})

defineEmits(['go-list', 'go-detail'])
</script>

<template>
  <header class="dog-top-bar">
    <div class="dog-top-left">
      <button v-if="currentView === 'detail'" class="dog-back-link" aria-label="Näyttelyt" @click="$emit('go-list')">
        <svg class="dog-back-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="160 208 80 128 160 48" />
        </svg>
        <span>Näyttelyt</span>
      </button>
      <button v-else-if="currentView === 'results'" class="dog-back-link" aria-label="Näyttely" @click="$emit('go-detail')">
        <svg class="dog-back-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="160 208 80 128 160 48" />
        </svg>
        <span>Näyttely</span>
      </button>
    </div>

    <div class="dog-top-center">
      <h1 class="dog-top-title">{{ title }}</h1>
    </div>

    <div class="dog-top-right">
      <ThemeToggle />
    </div>
  </header>
</template>
