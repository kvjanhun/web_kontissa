<script setup>
import { formatTimestamp } from '../dogResults.js'

const props = defineProps({
  judge: {
    type: String,
    default: '',
  },
  sourceUrl: {
    type: String,
    default: '',
  },
  fetchedAtIso: {
    type: String,
    default: '',
  },
})

const safeSourceUrl = computed(() => safeHref(props.sourceUrl))
</script>

<template>
  <div v-if="judge || sourceUrl || fetchedAtIso" class="dog-meta-bar">
    <span v-if="judge" class="dog-judge-pill">
      <svg class="dog-pill-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="128" cy="96" r="64"/>
        <path d="M32,224a96,96,0,0,1,192,0"/>
      </svg>
      Tuomari: <strong>{{ judge }}</strong>
    </span>

    <a
      v-if="safeSourceUrl"
      :href="safeSourceUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="dog-source-link-pill"
    >
      <svg class="dog-pill-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
        <path d="M128,48H48V208H208V128" />
        <polyline points="160 48 208 48 208 96" />
        <line x1="128" y1="128" x2="208" y2="48" />
      </svg>
      Showlink
    </a>

    <span v-if="fetchedAtIso" class="dog-updated-pill">
      Päivitetty {{ formatTimestamp(fetchedAtIso) }}
    </span>
  </div>
</template>
