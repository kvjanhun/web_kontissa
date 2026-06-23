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

const emit = defineEmits(['go-list', 'go-detail'])

// Keep the /dog brand a real anchor so right-click and modifier-click still
// open a new tab, but treat a plain left-click as in-app navigation back to
// the show list (no full page reload).
function onBrandClick(event) {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  emit('go-list')
}
</script>

<template>
  <header class="dog-top-bar">
    <!-- Persistent /dog brand — visible on every view -->
    <a class="dog-brand" href="/dog" aria-label="/dog" @click="onBrandClick">
      <svg class="dog-brand-mark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" aria-hidden="true">
        <polygon points="18.5,28 24,30 21.5,47 17.5,43 13.5,46" class="dog-mark-ribbon" />
        <polygon points="29.5,28 24,30 26.5,47 30.5,43 34.5,46" class="dog-mark-ribbon" />
        <circle cx="24.00" cy="4.80" r="3.1" class="dog-mark-petal" />
        <circle cx="31.60" cy="6.84" r="3.1" class="dog-mark-petal" />
        <circle cx="37.16" cy="12.40" r="3.1" class="dog-mark-petal" />
        <circle cx="39.20" cy="20.00" r="3.1" class="dog-mark-petal" />
        <circle cx="37.16" cy="27.60" r="3.1" class="dog-mark-petal" />
        <circle cx="31.60" cy="33.16" r="3.1" class="dog-mark-petal" />
        <circle cx="24.00" cy="35.20" r="3.1" class="dog-mark-petal" />
        <circle cx="16.40" cy="33.16" r="3.1" class="dog-mark-petal" />
        <circle cx="10.84" cy="27.60" r="3.1" class="dog-mark-petal" />
        <circle cx="8.80" cy="20.00" r="3.1" class="dog-mark-petal" />
        <circle cx="10.84" cy="12.40" r="3.1" class="dog-mark-petal" />
        <circle cx="16.40" cy="6.84" r="3.1" class="dog-mark-petal" />
        <circle cx="24" cy="20" r="11.6" class="dog-mark-disc" />
        <circle cx="24" cy="20" r="8.4" class="dog-mark-ring" />
        <circle cx="24" cy="20" r="4.6" class="dog-mark-pip" />
        <circle cx="24" cy="20" r="1.9" class="dog-mark-pip-center" />
      </svg>
      <span class="dog-brand-word"><span class="dog-brand-slash">/</span>dog</span>
    </a>

    <div class="dog-top-center">
      <span class="dog-top-divider" aria-hidden="true"></span>
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
      <h1 class="dog-top-title">{{ title }}</h1>
    </div>

    <div class="dog-top-right">
      <ThemeToggle />
    </div>
  </header>
</template>
