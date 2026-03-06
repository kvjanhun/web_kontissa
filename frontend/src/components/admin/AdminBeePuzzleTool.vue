<script setup>
import { ref, computed, onMounted } from 'vue'

const WORDS_PER_COLUMN = 10

const puzzleInput = ref(1)
const totalPuzzles = ref(null)
const variations = ref([])
const variationsLoading = ref(false)
const variationsError = ref('')
const centerSaving = ref(false)

const words = ref([])
const wordsLoading = ref(false)
const wordsError = ref('')

const sortedWords = computed(() =>
  [...words.value].sort((a, b) => a.localeCompare(b) || a.length - b.length)
)

const wordColumns = computed(() => {
  const cols = []
  for (let i = 0; i < sortedWords.value.length; i += WORDS_PER_COLUMN) {
    cols.push(sortedWords.value.slice(i, i + WORDS_PER_COLUMN))
  }
  return cols
})

async function fetchStats() {
  try {
    const res = await fetch('/api/kenno/stats')
    if (res.ok) {
      const data = await res.json()
      totalPuzzles.value = data.total_puzzles
    }
  } catch { /* ignore */ }
}

async function fetchTodayPuzzle() {
  try {
    const res = await fetch('/api/kenno')
    if (res.ok) {
      const data = await res.json()
      puzzleInput.value = data.puzzle_number + 1
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
    await fetchWords()
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
    words.value = data.words ?? []
  } catch {
    wordsError.value = 'Failed to load word list.'
    words.value = []
  } finally {
    wordsLoading.value = false
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
  variationsError.value = ''
  wordsError.value = ''
  fetchVariations()
  fetchWords()
}

// ---------------------------------------------------------------------------
// Creator section
// ---------------------------------------------------------------------------

const creatorLettersInput = ref('')
const creatorPreviewVariations = ref([])
const creatorPreviewLoading = ref(false)
const creatorPreviewError = ref('')
const creatorSelectedCenter = ref('')
const creatorSlotInput = ref(null)
const creatorSaving = ref(false)
const creatorSaveError = ref('')
const creatorSaveSuccess = ref('')
const creatorSchedule = ref([])
const creatorScheduleLoading = ref(false)

const FINNISH_LETTERS = new Set('abcdefghijklmnopqrstuvwxyzäö')

const creatorLetters = computed(() => {
  const raw = creatorLettersInput.value.toLowerCase().replace(/[^a-zäö]/g, '')
  return [...new Set(raw.split(''))].slice(0, 7)
})

const creatorLettersValid = computed(() => {
  const letters = creatorLetters.value
  if (letters.length !== 7) return false
  return letters.every(l => l.length === 1 && FINNISH_LETTERS.has(l))
})

const creatorDuplicates = computed(() => {
  const raw = creatorLettersInput.value.toLowerCase().replace(/[^a-zäö]/g, '')
  const seen = new Set()
  const dupes = new Set()
  for (const c of raw) {
    if (seen.has(c)) dupes.add(c)
    seen.add(c)
  }
  return [...dupes]
})

const creatorInvalidChars = computed(() => {
  const raw = creatorLettersInput.value
  const invalid = new Set()
  for (const c of raw) {
    if (c === ' ') continue
    if (!FINNISH_LETTERS.has(c.toLowerCase())) invalid.add(c)
  }
  return [...invalid]
})

const creatorValidationMessage = computed(() => {
  if (creatorInvalidChars.value.length > 0) {
    return `Virheelliset merkit: ${creatorInvalidChars.value.join(', ')}`
  }
  if (creatorDuplicates.value.length > 0) {
    return `Tuplat: ${creatorDuplicates.value.join(', ')}`
  }
  const count = creatorLetters.value.length
  if (count < 7) return `${count}/7 eri kirjainta`
  return '7 eri kirjainta'
})

const creatorValidationOk = computed(() => {
  return creatorLettersValid.value && creatorDuplicates.value.length === 0 && creatorInvalidChars.value.length === 0
})

function clearCreatorLetters() {
  creatorLettersInput.value = ''
  creatorPreviewVariations.value = []
  creatorSelectedCenter.value = ''
  creatorSaveError.value = ''
  creatorSaveSuccess.value = ''
}

async function fetchCreatorPreview() {
  if (!creatorValidationOk.value) return
  creatorPreviewLoading.value = true
  creatorPreviewError.value = ''
  creatorSelectedCenter.value = ''
  creatorSaveSuccess.value = ''
  try {
    const res = await fetch('/api/kenno/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ letters: creatorLetters.value }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Preview failed')
    }
    const data = await res.json()
    creatorPreviewVariations.value = data.variations
  } catch (e) {
    creatorPreviewError.value = e.message || 'Preview failed.'
    creatorPreviewVariations.value = []
  } finally {
    creatorPreviewLoading.value = false
  }
}

function selectCreatorCenter(letter) {
  creatorSelectedCenter.value = letter
  creatorSaveError.value = ''
  creatorSaveSuccess.value = ''
}

const todaySlot = computed(() => {
  const entry = creatorSchedule.value.find(e => e.is_today)
  return entry ? entry.slot : null
})

const creatorCanSave = computed(() => {
  if (!creatorSelectedCenter.value) return false
  if (creatorSlotInput.value == null || creatorSlotInput.value < 1) return false
  const slot = creatorSlotInput.value - 1
  if (todaySlot.value !== null && slot === todaySlot.value) return false
  return true
})

async function fetchSchedule() {
  creatorScheduleLoading.value = true
  try {
    const res = await fetch('/api/kenno/schedule?days=14')
    if (res.ok) {
      const data = await res.json()
      creatorSchedule.value = data.schedule
    }
  } catch { /* ignore */ }
  creatorScheduleLoading.value = false
}

async function saveCreatorPuzzle() {
  if (!creatorCanSave.value || creatorSaving.value) return
  const slot = creatorSlotInput.value - 1

  // Check if overwriting an existing slot
  const existingInSchedule = creatorSchedule.value.find(e => e.slot === slot)
  if (existingInSchedule && existingInSchedule.is_custom) {
    if (!confirm(`Peli ${creatorSlotInput.value} on jo mukautettu. Ylikirjoitetaanko?`)) return
  } else if (slot < 41) {
    if (!confirm(`Peli ${creatorSlotInput.value} on alkuperäinen peli. Ylikirjoitetaanko mukautetulla?`)) return
  }

  creatorSaving.value = true
  creatorSaveError.value = ''
  creatorSaveSuccess.value = ''
  try {
    const res = await fetch('/api/kenno/puzzle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        slot,
        letters: creatorLetters.value,
        center: creatorSelectedCenter.value,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Save failed')
    }
    const data = await res.json()
    const nextDate = data.next_play_date
      ? new Date(data.next_play_date).toLocaleDateString('fi-FI')
      : '?'
    creatorSaveSuccess.value = `Tallennettu peliin ${slot + 1}. Seuraava pelipäivä: ${nextDate}.`
    await fetchStats()
    await fetchSchedule()
  } catch (e) {
    creatorSaveError.value = e.message || 'Save failed.'
  } finally {
    creatorSaving.value = false
  }
}

// ---------------------------------------------------------------------------
// Swap section
// ---------------------------------------------------------------------------

const swapSlotA = ref(null)
const swapSlotB = ref(null)
const swapLoading = ref(false)
const swapError = ref('')
const swapSuccess = ref('')

const swapCanExecute = computed(() => {
  if (swapSlotA.value == null || swapSlotB.value == null) return false
  if (swapSlotA.value < 1 || swapSlotB.value < 1) return false
  if (swapSlotA.value === swapSlotB.value) return false
  const a = swapSlotA.value - 1
  const b = swapSlotB.value - 1
  if (todaySlot.value !== null && (a === todaySlot.value || b === todaySlot.value)) return false
  return true
})

async function executeSwap() {
  if (!swapCanExecute.value || swapLoading.value) return
  const a = swapSlotA.value - 1
  const b = swapSlotB.value - 1

  if (!confirm(`Vaihda pelien ${swapSlotA.value} ja ${swapSlotB.value} paikat?`)) return

  swapLoading.value = true
  swapError.value = ''
  swapSuccess.value = ''
  try {
    const res = await fetch('/api/kenno/puzzle/swap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slot_a: a, slot_b: b }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Swap failed')
    }
    swapSuccess.value = `Pelit ${swapSlotA.value} ja ${swapSlotB.value} vaihdettu.`
    await fetchSchedule()
    await fetchStats()
    // Refresh browser if viewing one of the swapped slots
    const viewing = puzzleInput.value - 1
    if (viewing === a || viewing === b) {
      onPuzzleChange()
    }
  } catch (e) {
    swapError.value = e.message || 'Swap failed.'
  } finally {
    swapLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Delete section
// ---------------------------------------------------------------------------

const deleteSlotInput = ref(null)
const deleteLoading = ref(false)
const deleteError = ref('')
const deleteSuccess = ref('')

const deleteCanExecute = computed(() => {
  if (deleteSlotInput.value == null || deleteSlotInput.value < 1) return false
  const slot = deleteSlotInput.value - 1
  if (todaySlot.value !== null && slot === todaySlot.value) return false
  return true
})

async function executeDelete() {
  if (!deleteCanExecute.value || deleteLoading.value) return
  const slot = deleteSlotInput.value - 1

  if (!confirm(`Poista mukautettu peli ${deleteSlotInput.value}? Alkuperäinen peli palautetaan, jos sellainen on.`)) return

  deleteLoading.value = true
  deleteError.value = ''
  deleteSuccess.value = ''
  try {
    const res = await fetch(`/api/kenno/puzzle/${slot}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Delete failed')
    }
    const data = await res.json()
    if (data.reverted_to_hardcoded) {
      deleteSuccess.value = `Peli ${deleteSlotInput.value} palautettu alkuperäiseksi.`
    } else {
      deleteSuccess.value = `Peli ${deleteSlotInput.value} poistettu.`
    }
    await fetchSchedule()
    await fetchStats()
    // Refresh browser if viewing the deleted slot
    if (puzzleInput.value - 1 === slot) {
      onPuzzleChange()
    }
  } catch (e) {
    deleteError.value = e.message || 'Delete failed.'
  } finally {
    deleteLoading.value = false
  }
}

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleDateString('fi-FI', { weekday: 'short', day: 'numeric', month: 'numeric' })
}

onMounted(async () => {
  await fetchStats()
  await fetchTodayPuzzle()
  await fetchVariations()
  await fetchWords()
  await fetchSchedule()
})
</script>

<template>
  <div>
    <h3 class="text-sm font-semibold mb-3" :style="{ color: 'var(--color-text-primary)' }">Kenno Tool</h3>

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

    <!-- Word list (always visible) -->
    <div v-if="variations.length > 0">
      <div v-if="wordsLoading" class="text-sm py-2" :style="{ color: 'var(--color-text-secondary)' }">
        Loading words…
      </div>
      <div v-else-if="wordsError" class="text-sm py-2" :style="{ color: '#ef4444' }">
        {{ wordsError }}
      </div>
      <div v-else-if="sortedWords.length > 0">
        <p class="text-xs mb-2" :style="{ color: 'var(--color-text-tertiary)' }">
          {{ sortedWords.length }} words — click × to permanently block a word
        </p>
        <div class="flex flex-wrap gap-x-6 gap-y-2">
          <ul v-for="(col, ci) in wordColumns" :key="ci">
            <li
              v-for="word in col"
              :key="word"
              class="flex items-center gap-1 text-sm py-0.5"
            >
              <span :style="{ color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }">{{ word }}</span>
              <button
                @click="blockWord(word)"
                class="text-xs leading-none opacity-40 hover:opacity-100"
                style="color: #ef4444; background: none; border: none; cursor: pointer; padding: 0 2px;"
                aria-label="Block word"
              >×</button>
            </li>
          </ul>
        </div>
      </div>
      <div v-else class="text-sm py-2" :style="{ color: 'var(--color-text-tertiary)' }">
        No words found for this puzzle.
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- Creator section -->
    <!-- ================================================================= -->
    <hr class="my-6" :style="{ borderColor: 'var(--color-border)' }" />

    <h3 class="text-sm font-semibold mb-3" :style="{ color: 'var(--color-text-primary)' }">Luo uusi peli</h3>

    <!-- Letter input -->
    <div class="mb-3">
      <label class="text-xs block mb-1" :style="{ color: 'var(--color-text-secondary)' }">Kirjaimet (7 eri kirjainta)</label>
      <div class="flex items-center gap-2">
        <input
          type="text"
          v-model="creatorLettersInput"
          placeholder="esim. aeklnsö"
          maxlength="14"
          class="rounded"
          style="width: 10rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 4px 8px; font-size: 0.875rem; font-family: var(--font-mono);"
        />
        <button
          @click="clearCreatorLetters"
          class="rounded text-xs px-2 py-1"
          :style="{ background: 'var(--color-bg-secondary)', color: 'var(--color-text-tertiary)', border: '1px solid var(--color-border)' }"
        >Tyhjennä</button>
      </div>
    </div>

    <!-- Letter boxes -->
    <div class="flex gap-1 mb-2">
      <div
        v-for="i in 7"
        :key="i"
        class="flex items-center justify-center rounded font-semibold text-sm"
        :style="{
          width: '2rem',
          height: '2rem',
          background: creatorLetters[i - 1] ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
          color: creatorLetters[i - 1] ? 'white' : 'var(--color-text-tertiary)',
          border: '1px solid ' + (creatorLetters[i - 1] ? 'var(--color-accent)' : 'var(--color-border)'),
        }"
      >
        {{ creatorLetters[i - 1]?.toUpperCase() ?? '' }}
      </div>
    </div>

    <!-- Validation message -->
    <p class="text-xs mb-3" :style="{ color: creatorValidationOk ? 'var(--color-text-tertiary)' : '#ef4444' }">
      {{ creatorValidationMessage }}
    </p>

    <!-- Preview button -->
    <button
      @click="fetchCreatorPreview"
      :disabled="!creatorValidationOk || creatorPreviewLoading"
      class="rounded text-xs px-3 py-1.5 mb-3"
      :style="{
        background: creatorValidationOk ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
        color: creatorValidationOk ? 'white' : 'var(--color-text-tertiary)',
        border: '1px solid ' + (creatorValidationOk ? 'var(--color-accent)' : 'var(--color-border)'),
        cursor: creatorValidationOk && !creatorPreviewLoading ? 'pointer' : 'default',
        opacity: creatorPreviewLoading ? '0.6' : '1',
      }"
    >
      {{ creatorPreviewLoading ? 'Lasketaan…' : 'Esikatsele' }}
    </button>

    <!-- Preview error -->
    <div v-if="creatorPreviewError" class="text-xs mb-3" :style="{ color: '#ef4444' }">
      {{ creatorPreviewError }}
    </div>

    <!-- Preview variations grid -->
    <div v-if="creatorPreviewVariations.length > 0" class="mb-4">
      <p class="text-xs mb-2" :style="{ color: 'var(--color-text-tertiary)' }">
        Valitse keskuskirjain klikkaamalla.
      </p>
      <div class="grid grid-cols-7 gap-1">
        <button
          v-for="v in creatorPreviewVariations"
          :key="v.center"
          class="flex flex-col items-center py-1.5 px-0.5 rounded text-xs leading-tight"
          :style="{
            background: creatorSelectedCenter === v.center ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
            color: creatorSelectedCenter === v.center ? 'white' : 'var(--color-text-secondary)',
            border: '1px solid ' + (creatorSelectedCenter === v.center ? 'var(--color-accent)' : 'var(--color-border)'),
            cursor: 'pointer',
          }"
          @click="selectCreatorCenter(v.center)"
        >
          <span class="font-semibold text-sm">{{ v.center.toUpperCase() }}</span>
          <span>{{ v.word_count }}w</span>
          <span>{{ v.max_score }}p</span>
          <span class="text-xs" :style="{ color: creatorSelectedCenter === v.center ? 'rgba(255,255,255,0.8)' : 'var(--color-text-tertiary)' }">70%: {{ Math.ceil(v.max_score * 0.7) }}</span>
          <span>{{ v.pangram_count }}pg</span>
        </button>
      </div>
    </div>

    <!-- Slot assignment -->
    <div v-if="creatorSelectedCenter" class="mb-4">
      <label class="text-xs block mb-1" :style="{ color: 'var(--color-text-secondary)' }">Pelinumero (1-indeksoitu)</label>
      <input
        type="number"
        v-model.number="creatorSlotInput"
        min="1"
        class="rounded text-center mb-2"
        style="width: 5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 4px 8px; font-size: 0.875rem;"
      />

      <!-- Today's slot warning -->
      <p
        v-if="creatorSlotInput != null && todaySlot !== null && (creatorSlotInput - 1) === todaySlot"
        class="text-xs mb-2"
        style="color: #ef4444;"
      >
        Tämän päivän peliä ei voi muokata.
      </p>

      <!-- Save button -->
      <button
        @click="saveCreatorPuzzle"
        :disabled="!creatorCanSave || creatorSaving"
        class="rounded text-xs px-3 py-1.5"
        :style="{
          background: creatorCanSave ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
          color: creatorCanSave ? 'white' : 'var(--color-text-tertiary)',
          border: '1px solid ' + (creatorCanSave ? 'var(--color-accent)' : 'var(--color-border)'),
          cursor: creatorCanSave && !creatorSaving ? 'pointer' : 'default',
          opacity: creatorSaving ? '0.6' : '1',
        }"
      >
        {{ creatorSaving ? 'Tallennetaan…' : creatorSlotInput ? `Tallenna peliin ${creatorSlotInput}` : 'Tallenna' }}
      </button>

      <!-- Save error -->
      <p v-if="creatorSaveError" class="text-xs mt-2" style="color: #ef4444;">{{ creatorSaveError }}</p>

      <!-- Save success -->
      <p v-if="creatorSaveSuccess" class="text-xs mt-2" :style="{ color: 'var(--color-accent)' }">{{ creatorSaveSuccess }}</p>
    </div>

    <!-- ================================================================= -->
    <!-- Schedule + manage section -->
    <!-- ================================================================= -->
    <hr class="my-6" :style="{ borderColor: 'var(--color-border)' }" />

    <h3 class="text-sm font-semibold mb-3" :style="{ color: 'var(--color-text-primary)' }">Aikataulu ja hallinta</h3>

    <!-- Schedule table -->
    <div v-if="creatorSchedule.length > 0" class="mb-4">
      <div class="overflow-x-auto">
        <table class="text-xs" style="border-collapse: collapse;">
          <tbody>
            <tr
              v-for="entry in creatorSchedule"
              :key="entry.date"
              :style="{
                background: entry.is_today ? 'rgba(239, 68, 68, 0.1)' : 'transparent',
              }"
            >
              <td class="px-2 py-0.5" :style="{ color: 'var(--color-text-secondary)' }">{{ formatDate(entry.date) }}</td>
              <td class="px-2 py-0.5 text-center" :style="{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }">{{ entry.display_number }}</td>
              <td class="px-2 py-0.5">
                <span v-if="entry.is_today" class="text-xs px-1 rounded" style="background: #ef4444; color: white;">tänään</span>
                <span v-else-if="entry.is_custom" class="text-xs px-1 rounded" :style="{ background: 'var(--color-accent)', color: 'white' }">mukautettu</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else-if="creatorScheduleLoading" class="text-xs mb-4" :style="{ color: 'var(--color-text-secondary)' }">
      Ladataan aikataulua…
    </div>

    <!-- Swap puzzles -->
    <div class="mb-4">
      <p class="text-xs font-semibold mb-1" :style="{ color: 'var(--color-text-secondary)' }">Vaihda järjestystä</p>
      <div class="flex items-center gap-2 mb-1">
        <label class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Peli</label>
        <input
          type="number"
          v-model.number="swapSlotA"
          min="1"
          :max="totalPuzzles ?? 999"
          class="rounded text-center"
          style="width: 4rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 6px; font-size: 0.875rem;"
        />
        <span class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">&#8596;</span>
        <label class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Peli</label>
        <input
          type="number"
          v-model.number="swapSlotB"
          min="1"
          :max="totalPuzzles ?? 999"
          class="rounded text-center"
          style="width: 4rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 6px; font-size: 0.875rem;"
        />
        <button
          @click="executeSwap"
          :disabled="!swapCanExecute || swapLoading"
          class="rounded text-xs px-3 py-1"
          :style="{
            background: swapCanExecute ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
            color: swapCanExecute ? 'white' : 'var(--color-text-tertiary)',
            border: '1px solid ' + (swapCanExecute ? 'var(--color-accent)' : 'var(--color-border)'),
            cursor: swapCanExecute && !swapLoading ? 'pointer' : 'default',
            opacity: swapLoading ? '0.6' : '1',
          }"
        >
          {{ swapLoading ? 'Vaihdetaan…' : 'Vaihda' }}
        </button>
      </div>
      <p v-if="swapError" class="text-xs" style="color: #ef4444;">{{ swapError }}</p>
      <p v-if="swapSuccess" class="text-xs" :style="{ color: 'var(--color-accent)' }">{{ swapSuccess }}</p>
    </div>

    <!-- Delete custom puzzle -->
    <div class="mb-4">
      <p class="text-xs font-semibold mb-1" :style="{ color: 'var(--color-text-secondary)' }">Poista mukautettu peli</p>
      <div class="flex items-center gap-2 mb-1">
        <label class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Peli</label>
        <input
          type="number"
          v-model.number="deleteSlotInput"
          min="1"
          :max="totalPuzzles ?? 999"
          class="rounded text-center"
          style="width: 4rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 6px; font-size: 0.875rem;"
        />
        <button
          @click="executeDelete"
          :disabled="!deleteCanExecute || deleteLoading"
          class="rounded text-xs px-3 py-1"
          :style="{
            background: deleteCanExecute ? '#ef4444' : 'var(--color-bg-secondary)',
            color: deleteCanExecute ? 'white' : 'var(--color-text-tertiary)',
            border: '1px solid ' + (deleteCanExecute ? '#ef4444' : 'var(--color-border)'),
            cursor: deleteCanExecute && !deleteLoading ? 'pointer' : 'default',
            opacity: deleteLoading ? '0.6' : '1',
          }"
        >
          {{ deleteLoading ? 'Poistetaan…' : 'Poista' }}
        </button>
      </div>
      <p class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Palauttaa alkuperäisen pelin, jos sellainen on.</p>
      <p v-if="deleteError" class="text-xs" style="color: #ef4444;">{{ deleteError }}</p>
      <p v-if="deleteSuccess" class="text-xs" :style="{ color: 'var(--color-accent)' }">{{ deleteSuccess }}</p>
    </div>
  </div>
</template>
