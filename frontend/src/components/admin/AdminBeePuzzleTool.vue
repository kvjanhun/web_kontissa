<script setup>
import { ref, onMounted, watch } from 'vue'

const puzzleInput = ref(1)
const totalPuzzles = ref(null)
const variations = ref([])
const variationsLoading = ref(false)
const variationsError = ref('')
const centerSaving = ref(false)

const wordListOpen = ref(false)
const words = ref([])
const wordsLoading = ref(false)
const wordsError = ref('')

async function fetchStats() {
  try {
    const res = await fetch('/api/kenno/stats')
    if (res.ok) {
      const data = await res.json()
      totalPuzzles.value = data.total_puzzles
    }
  } catch { /* ignore */ }
}

async function fetchVariations() {
  if (puzzleInput.value == null) return
  variationsLoading.value = true
  variationsError.value = ''
  try {
    const res = await fetch(`/api/kenno/variations?puzzle=${puzzleInput.value - 1}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    variations.value = data.variations
  } catch {
    variationsError.value = 'Failed to load variations.'
    variations.value = []
  } finally {
    variationsLoading.value = false
  }
}

async function setCenter(letter) {
  if (centerSaving.value) return
  centerSaving.value = true
  try {
    const res = await fetch('/api/kenno/center', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ puzzle: puzzleInput.value - 1, center: letter }),
    })
    if (!res.ok) throw new Error()
    await fetchVariations()
    if (wordListOpen.value) await fetchWords()
  } catch {
    variationsError.value = 'Could not change center letter.'
  } finally {
    centerSaving.value = false
  }
}

async function fetchWords() {
  wordsLoading.value = true
  wordsError.value = ''
  try {
    const res = await fetch(`/api/kenno?puzzle=${puzzleInput.value - 1}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    words.value = (data.words ?? []).slice().sort((a, b) => a.localeCompare(b) || a.length - b.length)
  } catch {
    wordsError.value = 'Failed to load word list.'
    words.value = []
  } finally {
    wordsLoading.value = false
  }
}

async function toggleWordList() {
  wordListOpen.value = !wordListOpen.value
  if (wordListOpen.value && words.value.length === 0) {
    await fetchWords()
  }
}

async function blockWord(word) {
  if (!confirm(`Remove "${word}" from the word list permanently?`)) return
  try {
    const res = await fetch('/api/kenno/block', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word }),
    })
    if (!res.ok) throw new Error()
    await fetchWords()
    await fetchVariations()
  } catch {
    wordsError.value = 'Could not remove word.'
  }
}

function onPuzzleChange() {
  variations.value = []
  words.value = []
  wordListOpen.value = false
  variationsError.value = ''
  wordsError.value = ''
  fetchVariations()
}

onMounted(async () => {
  await fetchStats()
  await fetchVariations()
})
</script>

<template>
  <div>
    <h3 class="text-sm font-semibold mb-3" :style="{ color: 'var(--color-text-primary)' }">Bee Puzzle Tool</h3>

    <!-- Puzzle selector -->
    <div class="flex items-center gap-2 mb-4">
      <label class="text-sm" :style="{ color: 'var(--color-text-secondary)' }">Puzzle</label>
      <input
        type="number"
        v-model.number="puzzleInput"
        min="1"
        :max="totalPuzzles ?? 999"
        @change="onPuzzleChange"
        class="rounded text-center"
        style="width: 4rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 6px; font-size: 0.875rem;"
      />
      <span class="text-sm" :style="{ color: 'var(--color-text-tertiary)' }">
        / {{ totalPuzzles ?? '…' }}
      </span>
    </div>

    <!-- Variations grid -->
    <div v-if="variationsLoading" class="text-sm py-2" :style="{ color: 'var(--color-text-secondary)' }">
      Loading variations…
    </div>
    <div v-else-if="variationsError" class="text-sm py-2" :style="{ color: '#ef4444' }">
      {{ variationsError }}
    </div>
    <div v-else-if="variations.length > 0" class="mb-4">
      <p class="text-xs mb-2" :style="{ color: 'var(--color-text-tertiary)' }">
        Click a letter to set it as the center. Active center is highlighted.
      </p>
      <div class="grid grid-cols-7 gap-1">
        <button
          v-for="v in variations"
          :key="v.center"
          class="flex flex-col items-center py-1.5 px-0.5 rounded text-xs leading-tight"
          :style="{
            background: v.is_active ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
            color: v.is_active ? 'white' : 'var(--color-text-secondary)',
            border: '1px solid ' + (v.is_active ? 'var(--color-accent)' : 'var(--color-border)'),
            cursor: v.is_active ? 'default' : centerSaving ? 'wait' : 'pointer',
            opacity: centerSaving && !v.is_active ? '0.6' : '1',
          }"
          :disabled="v.is_active || centerSaving"
          @click="!v.is_active && setCenter(v.center)"
        >
          <span class="font-semibold text-sm">{{ v.center.toUpperCase() }}</span>
          <span>{{ v.word_count }}w</span>
          <span>{{ v.max_score }}p</span>
          <span>{{ v.pangram_count }}pg</span>
        </button>
      </div>
    </div>

    <!-- Word list section -->
    <div v-if="variations.length > 0">
      <button
        class="text-sm font-medium mb-2"
        style="color: var(--color-text-secondary); background: none; border: none; cursor: pointer; padding: 0;"
        @click="toggleWordList"
        :aria-expanded="wordListOpen"
      >
        Word list {{ wordListOpen ? '▲' : '▼' }}
      </button>

      <div v-if="wordListOpen">
        <div v-if="wordsLoading" class="text-sm py-2" :style="{ color: 'var(--color-text-secondary)' }">
          Loading words…
        </div>
        <div v-else-if="wordsError" class="text-sm py-2" :style="{ color: '#ef4444' }">
          {{ wordsError }}
        </div>
        <div v-else-if="words.length > 0">
          <p class="text-xs mb-2" :style="{ color: 'var(--color-text-tertiary)' }">
            {{ words.length }} words — click × to permanently block a word
          </p>
          <div class="flex flex-wrap gap-x-4 gap-y-0.5">
            <div
              v-for="word in words"
              :key="word"
              class="flex items-center gap-0.5"
            >
              <span class="text-sm" :style="{ color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }">{{ word }}</span>
              <button
                @click="blockWord(word)"
                class="text-xs leading-none opacity-40 hover:opacity-100"
                style="color: #ef4444; background: none; border: none; cursor: pointer; padding: 0 2px;"
                aria-label="Block word"
              >×</button>
            </div>
          </div>
        </div>
        <div v-else class="text-sm py-2" :style="{ color: 'var(--color-text-tertiary)' }">
          No words found for this puzzle.
        </div>
      </div>
    </div>
  </div>
</template>
