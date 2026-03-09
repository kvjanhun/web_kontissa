<script setup>
import { computed } from 'vue'

const WORDS_PER_COLUMN = 10

const props = defineProps({
  words: { type: Array, required: true },
  letters: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  emptyMessage: { type: String, default: 'Ei sanoja tälle pelille.' },
})

const emit = defineEmits(['block'])

const sortedWords = computed(() =>
  [...props.words].sort((a, b) => a.localeCompare(b) || a.length - b.length)
)

const wordColumns = computed(() => {
  const cols = []
  for (let i = 0; i < sortedWords.value.length; i += WORDS_PER_COLUMN) {
    cols.push(sortedWords.value.slice(i, i + WORDS_PER_COLUMN))
  }
  return cols
})

function isPangram(word) {
  return props.letters.every(l => word.includes(l))
}
</script>

<template>
  <div v-if="loading" class="text-sm py-2" :style="{ color: 'var(--color-text-secondary)' }">
    Ladataan sanoja…
  </div>
  <div v-else-if="error" class="text-sm py-2" :style="{ color: '#ef4444' }">
    {{ error }}
  </div>
  <div v-else-if="sortedWords.length > 0">
    <p class="text-xs mb-2" :style="{ color: 'var(--color-text-tertiary)' }">
      {{ sortedWords.length }} sanaa — klikkaa × poistaaksesi sanan pysyvästi
    </p>
    <div class="flex flex-wrap gap-x-6 gap-y-2">
      <ul v-for="(col, ci) in wordColumns" :key="ci">
        <li
          v-for="word in col"
          :key="word"
          class="flex items-center gap-1 text-sm py-0.5"
        >
          <span :style="{ color: isPangram(word) ? 'var(--color-accent)' : 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', fontWeight: isPangram(word) ? '600' : 'normal' }">{{ word }}</span>
          <button
            @click="emit('block', word)"
            class="text-xs leading-none opacity-40 hover:opacity-100"
            style="color: #ef4444; background: none; border: none; cursor: pointer; padding: 0 2px;"
            aria-label="Block word"
          >×</button>
        </li>
      </ul>
    </div>
  </div>
  <div v-else class="text-sm py-2" :style="{ color: 'var(--color-text-tertiary)' }">
    {{ emptyMessage }}
  </div>
</template>
