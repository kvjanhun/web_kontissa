<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'

const WORDS_PER_COLUMN = 10
const FINNISH_LETTERS = new Set('abcdefghijklmnopqrstuvwxyzäö')

// ---------------------------------------------------------------------------
// Core state
// ---------------------------------------------------------------------------

const totalPuzzles = ref(null)
const currentSlot = ref(0)        // 0-indexed
const savedLetters = ref(null)    // array of 7 sorted letters, or null for new
const savedCenter = ref(null)
const lettersInput = ref('')
const selectedCenter = ref('')    // used in dirty mode only
const isCustom = ref(false)

const schedule = ref([])
const scheduleLoading = ref(false)
const slotListEl = ref(null)

const variations = ref([])
const variationsLoading = ref(false)
const variationsError = ref('')

const words = ref([])
const wordsLoading = ref(false)
const wordsError = ref('')

const centerSaving = ref(false)
const saving = ref(false)
const saveError = ref('')

const swapSlotInput = ref(null)
const swapLoading = ref(false)
const swapError = ref('')
const swapSuccess = ref('')

const deleteLoading = ref(false)
const deleteError = ref('')
const deleteSuccess = ref('')

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const parsedLetters = computed(() => {
  const raw = lettersInput.value.toLowerCase().replace(/[^a-zäö]/g, '')
  return [...new Set(raw.split(''))].slice(0, 7)
})

const lettersValid = computed(() => {
  const letters = parsedLetters.value
  if (letters.length !== 7) return false
  return letters.every(l => l.length === 1 && FINNISH_LETTERS.has(l))
})

const duplicates = computed(() => {
  const raw = lettersInput.value.toLowerCase().replace(/[^a-zäö]/g, '')
  const seen = new Set()
  const dupes = new Set()
  for (const c of raw) {
    if (seen.has(c)) dupes.add(c)
    seen.add(c)
  }
  return [...dupes]
})

const invalidChars = computed(() => {
  const raw = lettersInput.value
  const inv = new Set()
  for (const c of raw) {
    if (c === ' ') continue
    if (!FINNISH_LETTERS.has(c.toLowerCase())) inv.add(c)
  }
  return [...inv]
})

const validationMessage = computed(() => {
  if (invalidChars.value.length > 0) return `Virheelliset merkit: ${invalidChars.value.join(', ')}`
  if (duplicates.value.length > 0) return `Tuplat: ${duplicates.value.join(', ')}`
  const count = parsedLetters.value.length
  if (count < 7) return `${count}/7 eri kirjainta`
  return '7 eri kirjainta'
})

const validationOk = computed(() =>
  lettersValid.value && duplicates.value.length === 0 && invalidChars.value.length === 0
)

const isDirty = computed(() => {
  if (savedLetters.value === null) return true
  const sorted = [...parsedLetters.value].sort()
  if (sorted.length !== 7) return true
  return sorted.join(',') !== [...savedLetters.value].sort().join(',')
})

const todaySlot = computed(() => {
  const entry = schedule.value.find(e => e.is_today)
  return entry != null ? entry.slot : null
})

const isToday = computed(() =>
  todaySlot.value !== null && currentSlot.value === todaySlot.value
)

const displayNumber = computed(() => currentSlot.value + 1)

const canSave = computed(() => {
  if (!validationOk.value) return false
  if (!selectedCenter.value && isDirty.value) return false
  if (isToday.value) return false
  if (saving.value) return false
  return isDirty.value
})

const canSwap = computed(() => {
  if (swapSlotInput.value == null || swapSlotInput.value < 1) return false
  const other = swapSlotInput.value - 1
  if (other === currentSlot.value) return false
  if (todaySlot.value !== null && (currentSlot.value === todaySlot.value || other === todaySlot.value)) return false
  if (totalPuzzles.value && other >= totalPuzzles.value) return false
  return true
})

const canDelete = computed(() => {
  if (!isCustom.value) return false
  if (isToday.value) return false
  return true
})

const deleteLabel = computed(() =>
  currentSlot.value < 41 ? 'Palauta alkuperäinen' : 'Poista'
)

const customSlots = computed(() => {
  const set = new Set()
  for (const entry of schedule.value) {
    if (entry.is_custom) set.add(entry.slot)
  }
  return set
})

// Map slot → nearest upcoming date string (for showing dates in the list)
const slotNextDate = computed(() => {
  const map = new Map()
  for (const entry of schedule.value) {
    // Keep only the first (soonest) occurrence of each slot
    if (!map.has(entry.slot)) {
      map.set(entry.slot, entry.date)
    }
  }
  return map
})

function formatDateShort(isoDate) {
  return new Date(isoDate).toLocaleDateString('fi-FI', { weekday: 'short', day: 'numeric', month: 'numeric' })
}

const allSlotRows = computed(() => {
  const total = totalPuzzles.value ?? 0
  const rows = []
  for (let i = 0; i < total; i++) {
    const dateStr = slotNextDate.value.get(i)
    rows.push({
      slot: i,
      displayNumber: i + 1,
      isToday: todaySlot.value === i,
      isCustom: customSlots.value.has(i),
      date: dateStr ? formatDateShort(dateStr) : null,
    })
  }
  return rows
})

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

// ---------------------------------------------------------------------------
// Slot loading
// ---------------------------------------------------------------------------

async function loadSlot(slot) {
  currentSlot.value = slot
  savedLetters.value = null
  savedCenter.value = null
  selectedCenter.value = ''
  variations.value = []
  words.value = []
  variationsError.value = ''
  wordsError.value = ''
  saveError.value = ''
  swapError.value = ''
  swapSuccess.value = ''
  deleteError.value = ''
  deleteSuccess.value = ''

  // Fetch puzzle data + variations in parallel
  const [puzzleOk, variationsOk] = await Promise.all([
    fetchPuzzle(slot),
    fetchVariations(slot),
  ])

  if (puzzleOk) {
    // lettersInput is set inside fetchPuzzle
  }
}

async function fetchPuzzle(slot) {
  wordsLoading.value = true
  wordsError.value = ''
  try {
    const res = await fetch(`/api/kenno?puzzle=${slot}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    const allLetters = [data.center, ...data.letters].sort()
    savedLetters.value = allLetters
    savedCenter.value = data.center
    lettersInput.value = allLetters.join('')
    words.value = data.words ?? []
    totalPuzzles.value = data.total_puzzles
    return true
  } catch {
    wordsError.value = 'Pelin lataus epäonnistui.'
    words.value = []
    return false
  } finally {
    wordsLoading.value = false
  }
}

async function fetchVariations(slot) {
  variationsLoading.value = true
  variationsError.value = ''
  try {
    const res = await fetch(`/api/kenno/variations?puzzle=${slot}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    variations.value = data.variations
    return true
  } catch {
    variationsError.value = 'Variaatioiden lataus epäonnistui.'
    variations.value = []
    return false
  } finally {
    variationsLoading.value = false
  }
}

async function fetchStats() {
  try {
    const res = await fetch('/api/kenno/stats')
    if (res.ok) {
      const data = await res.json()
      totalPuzzles.value = data.total_puzzles
    }
  } catch { /* ignore */ }
}

async function fetchSchedule() {
  scheduleLoading.value = true
  try {
    // Fetch a full cycle to detect custom overrides for all slots
    const days = Math.min(totalPuzzles.value ?? 42, 90)
    const res = await fetch(`/api/kenno/schedule?days=${days}`)
    if (res.ok) {
      const data = await res.json()
      schedule.value = data.schedule
    }
  } catch { /* ignore */ }
  scheduleLoading.value = false
}

function scrollToCurrentSlot() {
  nextTick(() => {
    if (!slotListEl.value) return
    const row = slotListEl.value.querySelector('[data-active="true"]')
    if (row) row.scrollIntoView({ block: 'start' })
  })
}

// ---------------------------------------------------------------------------
// Actions — clean state
// ---------------------------------------------------------------------------

async function setCenter(letter) {
  if (centerSaving.value) return
  centerSaving.value = true
  try {
    const res = await fetch('/api/kenno/center', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ puzzle: currentSlot.value, center: letter }),
    })
    if (!res.ok) throw new Error()
    await loadSlot(currentSlot.value)
  } catch {
    variationsError.value = 'Keskuskirjaimen vaihto epäonnistui.'
  } finally {
    centerSaving.value = false
  }
}

async function blockWord(word) {
  if (!confirm(`Poista "${word}" sanalistalta pysyvästi?`)) return
  try {
    const res = await fetch('/api/kenno/block', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word }),
    })
    if (!res.ok) throw new Error()
    await loadSlot(currentSlot.value)
  } catch {
    wordsError.value = 'Sanan poisto epäonnistui.'
  }
}

// ---------------------------------------------------------------------------
// Actions — dirty state (preview + save)
// ---------------------------------------------------------------------------

async function fetchPreview() {
  if (!validationOk.value) return
  variationsLoading.value = true
  variationsError.value = ''
  selectedCenter.value = ''
  try {
    const res = await fetch('/api/kenno/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ letters: parsedLetters.value }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Esikatselu epäonnistui')
    }
    const data = await res.json()
    variations.value = data.variations.map(v => ({ ...v, is_active: false }))
  } catch (e) {
    variationsError.value = e.message || 'Esikatselu epäonnistui.'
    variations.value = []
  } finally {
    variationsLoading.value = false
  }
}

async function selectPreviewCenter(letter) {
  selectedCenter.value = letter
  // Fetch word list for this center from the preview endpoint
  wordsLoading.value = true
  wordsError.value = ''
  try {
    const res = await fetch('/api/kenno/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ letters: parsedLetters.value, center: letter }),
    })
    if (!res.ok) {
      if (res.status === 429) {
        wordsError.value = 'Liian monta pyyntöä — odota hetki.'
      }
      throw new Error()
    }
    const data = await res.json()
    words.value = data.words ?? []
  } catch {
    if (!wordsError.value) wordsError.value = 'Sanalistan lataus epäonnistui.'
    words.value = []
  } finally {
    wordsLoading.value = false
  }
}

async function savePuzzle() {
  if (!canSave.value) return
  saving.value = true
  saveError.value = ''
  try {
    const center = selectedCenter.value
    if (!center) {
      saveError.value = 'Valitse keskuskirjain ensin.'
      return
    }
    const res = await fetch('/api/kenno/puzzle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        slot: currentSlot.value,
        letters: parsedLetters.value,
        center,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Tallennus epäonnistui')
    }
    // Reload slot as clean state + refresh schedule/stats
    await Promise.all([
      loadSlot(currentSlot.value),
      fetchSchedule(),
      fetchStats(),
    ])
  } catch (e) {
    saveError.value = e.message || 'Tallennus epäonnistui.'
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------------------
// Actions — swap
// ---------------------------------------------------------------------------

async function executeSwap() {
  if (!canSwap.value || swapLoading.value) return
  const other = swapSlotInput.value - 1

  if (!confirm(`Vaihda pelien ${displayNumber.value} ja ${swapSlotInput.value} paikat?`)) return

  swapLoading.value = true
  swapError.value = ''
  swapSuccess.value = ''
  try {
    const res = await fetch('/api/kenno/puzzle/swap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slot_a: currentSlot.value, slot_b: other }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Vaihto epäonnistui')
    }
    swapSuccess.value = `Pelit ${displayNumber.value} ja ${swapSlotInput.value} vaihdettu.`
    await Promise.all([
      loadSlot(currentSlot.value),
      fetchSchedule(),
      fetchStats(),
    ])
  } catch (e) {
    swapError.value = e.message || 'Vaihto epäonnistui.'
  } finally {
    swapLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Actions — delete/revert
// ---------------------------------------------------------------------------

async function executeDelete() {
  if (!canDelete.value || deleteLoading.value) return

  const msg = currentSlot.value < 41
    ? `Palauta peli ${displayNumber.value} alkuperäiseksi?`
    : `Poista peli ${displayNumber.value}?`
  if (!confirm(msg)) return

  deleteLoading.value = true
  deleteError.value = ''
  deleteSuccess.value = ''
  try {
    const res = await fetch(`/api/kenno/puzzle/${currentSlot.value}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Poisto epäonnistui')
    }
    const data = await res.json()
    deleteSuccess.value = data.reverted_to_hardcoded
      ? `Peli ${displayNumber.value} palautettu alkuperäiseksi.`
      : `Peli ${displayNumber.value} poistettu.`
    await Promise.all([
      loadSlot(currentSlot.value),
      fetchSchedule(),
      fetchStats(),
    ])
  } catch (e) {
    deleteError.value = e.message || 'Poisto epäonnistui.'
  } finally {
    deleteLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function onSlotInput() {
  const val = displayNumber.value
  if (val >= 1 && (totalPuzzles.value == null || val <= totalPuzzles.value)) {
    loadSlot(val - 1)
  }
}

function newPuzzle() {
  const nextSlot = totalPuzzles.value ?? 41
  currentSlot.value = nextSlot
  savedLetters.value = null
  savedCenter.value = null
  lettersInput.value = ''
  selectedCenter.value = ''
  variations.value = []
  words.value = []
  variationsError.value = ''
  wordsError.value = ''
  saveError.value = ''
  swapError.value = ''
  swapSuccess.value = ''
  deleteError.value = ''
  deleteSuccess.value = ''
}

function updateIsCustom() {
  isCustom.value = customSlots.value.has(currentSlot.value)
}

watch(schedule, updateIsCustom)
watch(currentSlot, updateIsCustom)

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

onMounted(async () => {
  await fetchStats()
  await fetchSchedule()

  // Load today's puzzle
  try {
    const res = await fetch('/api/kenno')
    if (res.ok) {
      const data = await res.json()
      await loadSlot(data.puzzle_number)
      scrollToCurrentSlot()
    }
  } catch { /* ignore */ }
})
</script>

<template>
  <div>
    <!-- ================================================================= -->
    <!-- Two-column layout: slot list left, editor right on md+ -->
    <!-- ================================================================= -->
    <div class="flex flex-col md:flex-row gap-4">

    <!-- ================================================================= -->
    <!-- Slot list (left column on desktop) -->
    <!-- ================================================================= -->
    <div class="md:shrink-0" style="width: fit-content; max-width: 11rem;">
      <div class="flex items-center gap-2 mb-1">
        <p class="text-xs font-semibold" :style="{ color: 'var(--color-text-secondary)' }">Pelit</p>
        <button
          @click="newPuzzle"
          class="rounded text-xs px-2 py-0.5"
          :style="{
            background: 'var(--color-accent)',
            color: 'white',
            border: '1px solid var(--color-accent)',
            cursor: 'pointer',
          }"
        >Uusi</button>
      </div>
      <div
        v-if="allSlotRows.length > 0"
        ref="slotListEl"
        style="max-height: 32rem; overflow-y: auto;"
        :style="{ border: '1px solid var(--color-border)', borderRadius: '4px' }"
      >
        <div
          v-for="row in allSlotRows"
          :key="row.slot"
          :data-active="row.slot === currentSlot ? 'true' : undefined"
          @click="loadSlot(row.slot)"
          class="flex items-center gap-1 px-0.5 py-0.5 text-xs cursor-pointer hover:opacity-80"
          :style="{
            background: row.slot === currentSlot
              ? 'var(--color-bg-secondary)'
              : row.isToday
                ? 'rgba(239, 68, 68, 0.1)'
                : 'transparent',
          }"
        >
          <span :style="{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', minWidth: '1.25rem', textAlign: 'right' }">{{ row.displayNumber }}</span>
          <span v-if="row.date" class="truncate" :style="{ color: 'var(--color-text-tertiary)' }">{{ row.date }}</span>
          <span v-if="row.isToday" class="px-1 rounded shrink-0" style="background: #ef4444; color: white; font-size: 0.625rem; line-height: 1.4;">tänään</span>
          <span v-else-if="row.isCustom" class="px-1 rounded shrink-0" :style="{ background: 'var(--color-accent)', color: 'white', fontSize: '0.625rem', lineHeight: '1.4' }">muk.</span>
          <span v-if="row.slot === currentSlot" class="shrink-0" :style="{ color: 'var(--color-accent)' }">&#9679;</span>
        </div>
      </div>
      <div v-else-if="scheduleLoading" class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">
        Ladataan…
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- 3. Puzzle editor (right column on desktop) -->
    <!-- ================================================================= -->
    <div class="flex-1 min-w-0">

    <!-- Toolbar: Peli N/NN | Kirjaimet [____] Tyhjennä | Vaihda ↔ [__] | Delete — single row on md+ -->
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2 mb-3">
      <!-- Slot number -->
      <div class="flex items-center gap-1">
        <label class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">Peli</label>
        <input
          type="number"
          :value="displayNumber"
          @change="e => { currentSlot = Math.max(0, (parseInt(e.target.value) || 1) - 1); onSlotInput() }"
          min="1"
          :max="totalPuzzles ?? 999"
          class="rounded text-center"
          style="width: 3.5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;"
        />
        <span class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">/{{ totalPuzzles ?? '…' }}</span>
      </div>
      <!-- Letters input -->
      <div class="flex items-center gap-1">
        <input
          type="text"
          v-model="lettersInput"
          placeholder="kirjaimet"
          maxlength="14"
          class="rounded"
          style="width: 7rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 6px; font-size: 0.875rem; font-family: var(--font-mono);"
          @keydown.enter="isDirty && validationOk && !variationsLoading && fetchPreview()"
        />
        <button
          @click="lettersInput = ''; variations = []; selectedCenter = ''; saveError = ''"
          class="rounded text-xs px-1.5 py-0.5"
          :style="{ background: 'var(--color-bg-secondary)', color: 'var(--color-text-tertiary)', border: '1px solid var(--color-border)' }"
        >Tyhjennä</button>
        <button
          v-if="isDirty && savedLetters !== null"
          @click="loadSlot(currentSlot)"
          class="rounded text-xs px-1.5 py-0.5"
          :style="{ background: 'var(--color-bg-secondary)', color: 'var(--color-text-tertiary)', border: '1px solid var(--color-border)' }"
        >Palauta</button>
      </div>
      <!-- Swap -->
      <div class="flex items-center gap-1">
        <span class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">&#8596;</span>
        <input
          type="number"
          v-model.number="swapSlotInput"
          min="1"
          :max="totalPuzzles ?? 999"
          class="rounded text-center"
          style="width: 3.5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;"
        />
        <button
          @click="executeSwap"
          :disabled="!canSwap || swapLoading"
          class="rounded text-xs px-1.5 py-0.5"
          :style="{
            background: canSwap ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
            color: canSwap ? 'white' : 'var(--color-text-tertiary)',
            border: '1px solid ' + (canSwap ? 'var(--color-accent)' : 'var(--color-border)'),
            cursor: canSwap && !swapLoading ? 'pointer' : 'default',
            opacity: swapLoading ? '0.6' : '1',
          }"
        >
          {{ swapLoading ? '…' : 'Vaihda' }}
        </button>
      </div>
      <!-- Delete/revert -->
      <button
        v-if="canDelete"
        @click="executeDelete"
        :disabled="deleteLoading"
        class="rounded text-xs px-1.5 py-0.5"
        :style="{
          background: '#ef4444',
          color: 'white',
          border: '1px solid #ef4444',
          cursor: deleteLoading ? 'wait' : 'pointer',
          opacity: deleteLoading ? '0.6' : '1',
        }"
      >
        {{ deleteLoading ? '…' : deleteLabel }}
      </button>
    </div>

    <!-- Status messages -->
    <p v-if="isToday" class="text-xs mb-2" style="color: #ef4444;">Tämän päivän peliä ei voi muokata.</p>
    <p v-if="swapError" class="text-xs mb-2" style="color: #ef4444;">{{ swapError }}</p>
    <p v-if="swapSuccess" class="text-xs mb-2" :style="{ color: 'var(--color-accent)' }">{{ swapSuccess }}</p>
    <p v-if="deleteError" class="text-xs mb-2" style="color: #ef4444;">{{ deleteError }}</p>
    <p v-if="deleteSuccess" class="text-xs mb-2" :style="{ color: 'var(--color-accent)' }">{{ deleteSuccess }}</p>

    <!-- Letter boxes -->
    <div class="flex gap-1 mb-2">
      <div
        v-for="i in 7"
        :key="i"
        class="flex items-center justify-center rounded font-semibold text-sm"
        :style="{
          width: '2rem',
          height: '2rem',
          background: parsedLetters[i - 1] ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
          color: parsedLetters[i - 1] ? 'white' : 'var(--color-text-tertiary)',
          border: '1px solid ' + (parsedLetters[i - 1] ? 'var(--color-accent)' : 'var(--color-border)'),
        }"
      >
        {{ parsedLetters[i - 1]?.toUpperCase() ?? '' }}
      </div>
    </div>

    <!-- Validation message -->
    <p class="text-xs mb-3" :style="{ color: validationOk ? 'var(--color-text-tertiary)' : '#ef4444' }">
      {{ validationMessage }}
    </p>

    <!-- ── Dirty state: Preview + Save ─────────────────────────────────── -->
    <template v-if="isDirty">
      <!-- Preview button -->
      <button
        @click="fetchPreview"
        :disabled="!validationOk || variationsLoading"
        class="rounded text-xs px-3 py-1.5 mb-3"
        :style="{
          background: validationOk ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
          color: validationOk ? 'white' : 'var(--color-text-tertiary)',
          border: '1px solid ' + (validationOk ? 'var(--color-accent)' : 'var(--color-border)'),
          cursor: validationOk && !variationsLoading ? 'pointer' : 'default',
          opacity: variationsLoading ? '0.6' : '1',
        }"
      >
        {{ variationsLoading ? 'Lasketaan…' : 'Esikatsele' }}
      </button>

      <!-- Dirty variations grid (click selects center locally) -->
      <div v-if="variationsError" class="text-xs mb-3" :style="{ color: '#ef4444' }">
        {{ variationsError }}
      </div>
      <div v-if="variations.length > 0" class="mb-4">
        <p class="text-xs mb-2" :style="{ color: 'var(--color-text-tertiary)' }">
          Valitse keskuskirjain klikkaamalla.
        </p>
        <div class="grid grid-cols-7 gap-1">
          <button
            v-for="v in variations"
            :key="v.center"
            class="flex flex-col items-center py-1.5 px-0.5 rounded text-xs leading-tight"
            :style="{
              background: selectedCenter === v.center ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
              color: selectedCenter === v.center ? 'white' : 'var(--color-text-secondary)',
              border: '1px solid ' + (selectedCenter === v.center ? 'var(--color-accent)' : 'var(--color-border)'),
              cursor: 'pointer',
            }"
            @click="selectPreviewCenter(v.center)"
          >
            <span class="font-semibold text-sm">{{ v.center.toUpperCase() }}</span>
            <span>{{ v.word_count }}w</span>
            <span>{{ v.max_score }}p</span>
            <span class="text-xs" :style="{ color: selectedCenter === v.center ? 'rgba(255,255,255,0.8)' : 'var(--color-text-tertiary)' }">70%: {{ Math.ceil(v.max_score * 0.7) }}</span>
            <span>{{ v.pangram_count }}pg</span>
          </button>
        </div>
      </div>

      <!-- Save button -->
      <div v-if="selectedCenter" class="mb-3">
        <button
          @click="savePuzzle"
          :disabled="!canSave"
          class="rounded text-xs px-3 py-1.5"
          :style="{
            background: canSave ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
            color: canSave ? 'white' : 'var(--color-text-tertiary)',
            border: '1px solid ' + (canSave ? 'var(--color-accent)' : 'var(--color-border)'),
            cursor: canSave ? 'pointer' : 'default',
            opacity: saving ? '0.6' : '1',
          }"
        >
          {{ saving ? 'Tallennetaan…' : `Tallenna peliin ${displayNumber}` }}
        </button>
      </div>

      <p v-if="saveError" class="text-xs mb-3" style="color: #ef4444;">{{ saveError }}</p>

      <!-- Word list (preview mode — fetched when center is selected) -->
      <div v-if="selectedCenter">
        <div v-if="wordsLoading" class="text-sm py-2" :style="{ color: 'var(--color-text-secondary)' }">
          Ladataan sanoja…
        </div>
        <div v-else-if="wordsError" class="text-sm py-2" :style="{ color: '#ef4444' }">
          {{ wordsError }}
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
        <div v-else-if="!wordsLoading" class="text-sm py-2" :style="{ color: 'var(--color-text-tertiary)' }">
          Ei sanoja tälle pelille.
        </div>
      </div>
    </template>

    <!-- ── Clean state: live variations + words ────────────────────────── -->
    <template v-else>
      <!-- Variations grid (click changes center on server) -->
      <div v-if="variationsLoading" class="text-sm py-2" :style="{ color: 'var(--color-text-secondary)' }">
        Ladataan variaatioita…
      </div>
      <div v-else-if="variationsError" class="text-sm py-2" :style="{ color: '#ef4444' }">
        {{ variationsError }}
      </div>
      <div v-else-if="variations.length > 0" class="mb-4">
        <p class="text-xs mb-2" :style="{ color: 'var(--color-text-tertiary)' }">
          Keskuskirjain — klikkaa vaihtaaksesi.
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

      <!-- Word list -->
      <div v-if="variations.length > 0">
        <div v-if="wordsLoading" class="text-sm py-2" :style="{ color: 'var(--color-text-secondary)' }">
          Ladataan sanoja…
        </div>
        <div v-else-if="wordsError" class="text-sm py-2" :style="{ color: '#ef4444' }">
          {{ wordsError }}
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
          Ei sanoja tälle pelille.
        </div>
      </div>
    </template>

    </div><!-- /editor right column -->
    </div><!-- /two-column flex row -->
  </div>
</template>
