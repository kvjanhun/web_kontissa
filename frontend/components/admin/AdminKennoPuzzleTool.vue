<script setup>
import KennoWordList from './KennoWordList.vue'
import KennoCombinations from './AdminKennoCombinations.vue'

// Rotation constants (must match kenno.py)
const ROTATION_START = new Date('2026-02-24T00:00:00')
const START_INDEX = 1

// ---------------------------------------------------------------------------
// Core state
// ---------------------------------------------------------------------------

const totalPuzzles = ref(null)
const currentSlot = ref(0)
const selectedDate = ref('')

// Saved puzzle state (from DB — "clean" state)
const savedCombo = ref('')      // sorted letters string, e.g. "aeklnsö"
const savedCenter = ref('')

// Active selection (what the user is working with)
const activeCombo = ref('')     // letters string of selected combination
const activeCenter = ref('')    // selected center letter

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
// Date ↔ slot conversion
// ---------------------------------------------------------------------------

function slotForDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  const days = Math.round((d - ROTATION_START) / 86400000)
  const total = totalPuzzles.value || 1
  return ((START_INDEX + days) % total + total) % total
}

function nextDateForSlot(slot) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const total = totalPuzzles.value || 1
  for (let i = 0; i <= total; i++) {
    const d = new Date(today.getTime() + i * 86400000)
    if (slotForDate(d.toISOString().slice(0, 10)) === slot) {
      return d.toISOString().slice(0, 10)
    }
  }
  return today.toISOString().slice(0, 10)
}

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const activeLettersArray = computed(() =>
  activeCombo.value ? activeCombo.value.split('') : []
)

const isDirty = computed(() => {
  if (!activeCombo.value || !activeCenter.value) return false
  return activeCombo.value !== savedCombo.value || activeCenter.value !== savedCenter.value
})

const todaySlot = computed(() =>
  totalPuzzles.value ? slotForDate(todayStr()) : null
)

const isToday = computed(() =>
  todaySlot.value !== null && currentSlot.value === todaySlot.value
)

const displayNumber = computed(() => currentSlot.value + 1)

const canSave = computed(() => {
  if (!isDirty.value) return false
  if (isToday.value) return false
  if (saving.value) return false
  return true
})

const canSwap = computed(() => {
  if (swapSlotInput.value == null || swapSlotInput.value < 1) return false
  const other = swapSlotInput.value - 1
  if (other === currentSlot.value) return false
  if (todaySlot.value !== null && (currentSlot.value === todaySlot.value || other === todaySlot.value)) return false
  if (totalPuzzles.value && other >= totalPuzzles.value) return false
  return true
})

const canDelete = computed(() => !isToday.value)

// ---------------------------------------------------------------------------
// Slot loading
// ---------------------------------------------------------------------------

async function loadSlot(slot) {
  currentSlot.value = slot
  savedCombo.value = ''
  savedCenter.value = ''
  activeCombo.value = ''
  activeCenter.value = ''
  words.value = []
  wordsError.value = ''
  saveError.value = ''
  swapError.value = ''
  swapSuccess.value = ''
  deleteError.value = ''
  deleteSuccess.value = ''

  if (totalPuzzles.value) {
    selectedDate.value = nextDateForSlot(slot)
  }

  await fetchPuzzle(slot)
}

async function fetchPuzzle(slot) {
  wordsLoading.value = true
  wordsError.value = ''
  try {
    const res = await fetch(`/api/kenno?puzzle=${slot}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    const allLetters = [data.center, ...data.letters].sort()
    const comboKey = allLetters.join('')

    savedCombo.value = comboKey
    savedCenter.value = data.center
    activeCombo.value = comboKey
    activeCenter.value = data.center
    words.value = data.words ?? []
    totalPuzzles.value = data.total_puzzles
  } catch {
    wordsError.value = 'Pelin lataus epäonnistui.'
    words.value = []
  } finally {
    wordsLoading.value = false
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

// ---------------------------------------------------------------------------
// Date picker
// ---------------------------------------------------------------------------

function onDateChange(e) {
  const dateStr = e.target.value
  if (!dateStr || !totalPuzzles.value) return
  selectedDate.value = dateStr
  const slot = slotForDate(dateStr)
  if (slot !== currentSlot.value) {
    loadSlot(slot)
  }
}

// ---------------------------------------------------------------------------
// Center selection from browser
// ---------------------------------------------------------------------------

async function onSelectCenter(comboLetters, center) {
  activeCombo.value = comboLetters
  activeCenter.value = center

  // If this is the saved combo, change center on the server (clean mode)
  if (comboLetters === savedCombo.value && !isToday.value) {
    centerSaving.value = true
    try {
      const res = await fetch('/api/kenno/center', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ puzzle: currentSlot.value, center }),
      })
      if (!res.ok) throw new Error()
      savedCenter.value = center
      // Reload word list
      await fetchPuzzle(currentSlot.value)
    } catch {
      wordsError.value = 'Keskuskirjaimen vaihto epäonnistui.'
    } finally {
      centerSaving.value = false
    }
    return
  }

  // Dirty mode: fetch word list via preview
  wordsLoading.value = true
  wordsError.value = ''
  try {
    const res = await fetch('/api/kenno/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ letters: comboLetters.split(''), center }),
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

// ---------------------------------------------------------------------------
// Block word
// ---------------------------------------------------------------------------

async function blockWord(word) {
  if (!confirm(`Poista "${word}" sanalistalta pysyvästi?`)) return
  try {
    const res = await fetch('/api/kenno/block', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word }),
    })
    if (!res.ok) throw new Error()
    // Refresh word list
    if (activeCombo.value && activeCenter.value) {
      await onSelectCenter(activeCombo.value, activeCenter.value)
    }
  } catch {
    wordsError.value = 'Sanan poisto epäonnistui.'
  }
}

// ---------------------------------------------------------------------------
// Save
// ---------------------------------------------------------------------------

async function savePuzzle() {
  if (!canSave.value) return
  saving.value = true
  saveError.value = ''
  try {
    const res = await fetch('/api/kenno/puzzle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        slot: currentSlot.value,
        letters: activeCombo.value.split(''),
        center: activeCenter.value,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Tallennus epäonnistui')
    }
    savedCombo.value = activeCombo.value
    savedCenter.value = activeCenter.value
    await Promise.all([
      fetchPuzzle(currentSlot.value),
      fetchStats(),
    ])
  } catch (e) {
    saveError.value = e.message || 'Tallennus epäonnistui.'
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------------------
// Swap
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
    await Promise.all([loadSlot(currentSlot.value), fetchStats()])
  } catch (e) {
    swapError.value = e.message || 'Vaihto epäonnistui.'
  } finally {
    swapLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Delete
// ---------------------------------------------------------------------------

async function executeDelete() {
  if (!canDelete.value || deleteLoading.value) return
  if (!confirm(`Poista peli ${displayNumber.value}?`)) return

  deleteLoading.value = true
  deleteError.value = ''
  deleteSuccess.value = ''
  try {
    const res = await fetch(`/api/kenno/puzzle/${currentSlot.value}`, { method: 'DELETE' })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Poisto epäonnistui')
    }
    await res.json()
    deleteSuccess.value = `Peli ${displayNumber.value} poistettu.`
    await Promise.all([loadSlot(currentSlot.value), fetchStats()])
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
  savedCombo.value = ''
  savedCenter.value = ''
  activeCombo.value = ''
  activeCenter.value = ''
  words.value = []
  wordsError.value = ''
  saveError.value = ''
  swapError.value = ''
  swapSuccess.value = ''
  deleteError.value = ''
  deleteSuccess.value = ''
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

onMounted(async () => {
  await fetchStats()
  try {
    const res = await fetch('/api/kenno')
    if (res.ok) {
      const data = await res.json()
      await loadSlot(data.puzzle_number)
    }
  } catch { /* ignore */ }
})
</script>

<template>
  <div>
    <!-- ================================================================= -->
    <!-- Slot toolbar -->
    <!-- ================================================================= -->
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2 mb-3">
      <!-- Date picker -->
      <div class="flex items-center gap-1">
        <label class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">Pvm</label>
        <input
          type="date"
          :value="selectedDate"
          @change="onDateChange"
          class="rounded"
          style="background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;"
        />
      </div>
      <!-- Slot number with +/- buttons -->
      <div class="flex items-center gap-0.5">
        <label class="text-xs mr-0.5" :style="{ color: 'var(--color-text-secondary)' }">Peli</label>
        <button
          @click="currentSlot > 0 && loadSlot(currentSlot - 1)"
          :disabled="currentSlot <= 0"
          class="rounded text-xs px-1.5 py-0.5 select-none"
          :style="{
            background: 'var(--color-bg-secondary)',
            color: currentSlot > 0 ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)',
            border: '1px solid var(--color-border)',
            cursor: currentSlot > 0 ? 'pointer' : 'default',
            lineHeight: '1.4',
          }"
        >&minus;</button>
        <input
          type="text"
          inputmode="numeric"
          pattern="[0-9]*"
          :value="displayNumber"
          @change="e => { currentSlot = Math.max(0, (parseInt(e.target.value) || 1) - 1); onSlotInput() }"
          class="rounded text-center"
          style="width: 3rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;"
        />
        <button
          @click="(!totalPuzzles || currentSlot < totalPuzzles - 1) && loadSlot(currentSlot + 1)"
          :disabled="totalPuzzles && currentSlot >= totalPuzzles - 1"
          class="rounded text-xs px-1.5 py-0.5 select-none"
          :style="{
            background: 'var(--color-bg-secondary)',
            color: (!totalPuzzles || currentSlot < totalPuzzles - 1) ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)',
            border: '1px solid var(--color-border)',
            cursor: (!totalPuzzles || currentSlot < totalPuzzles - 1) ? 'pointer' : 'default',
            lineHeight: '1.4',
          }"
        >+</button>
        <span class="text-xs ml-0.5" :style="{ color: 'var(--color-text-tertiary)' }">/{{ totalPuzzles ?? '…' }}</span>
      </div>
      <!-- Swap -->
      <div class="flex items-center gap-1">
        <span class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">&#8596;</span>
        <input type="text" inputmode="numeric" pattern="[0-9]*" v-model.number="swapSlotInput" placeholder="#" class="rounded text-center" style="width: 3rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;" />
        <button @click="executeSwap" :disabled="!canSwap || swapLoading" class="rounded text-xs px-1.5 py-0.5" :style="{ background: canSwap ? 'var(--color-accent)' : 'var(--color-bg-secondary)', color: canSwap ? 'white' : 'var(--color-text-tertiary)', border: '1px solid ' + (canSwap ? 'var(--color-accent)' : 'var(--color-border)'), cursor: canSwap && !swapLoading ? 'pointer' : 'default', opacity: swapLoading ? '0.6' : '1' }">{{ swapLoading ? '…' : 'Vaihda' }}</button>
      </div>
      <!-- Delete -->
      <button v-if="canDelete" @click="executeDelete" :disabled="deleteLoading" class="rounded text-xs px-1.5 py-0.5" :style="{ background: '#ef4444', color: 'white', border: '1px solid #ef4444', cursor: deleteLoading ? 'wait' : 'pointer', opacity: deleteLoading ? '0.6' : '1' }">{{ deleteLoading ? '…' : 'Poista' }}</button>
      <!-- New -->
      <button @click="newPuzzle" class="rounded text-xs px-2 py-0.5" :style="{ background: 'var(--color-accent)', color: 'white', border: '1px solid var(--color-accent)', cursor: 'pointer' }">Uusi</button>
    </div>

    <!-- Status messages -->
    <p v-if="isToday" class="text-xs mb-2" style="color: #ef4444;">Tämän päivän peliä ei voi muokata.</p>
    <p v-if="swapError" class="text-xs mb-2" style="color: #ef4444;">{{ swapError }}</p>
    <p v-if="swapSuccess" class="text-xs mb-2" :style="{ color: 'var(--color-accent)' }">{{ swapSuccess }}</p>
    <p v-if="deleteError" class="text-xs mb-2" style="color: #ef4444;">{{ deleteError }}</p>
    <p v-if="deleteSuccess" class="text-xs mb-2" :style="{ color: 'var(--color-accent)' }">{{ deleteSuccess }}</p>

    <!-- Current puzzle indicator -->
    <div v-if="activeCombo" class="flex items-center gap-2 mb-3">
      <div class="flex gap-1">
        <div
          v-for="(letter, i) in activeLettersArray"
          :key="i"
          class="flex items-center justify-center rounded font-semibold text-xs"
          :style="{
            width: '1.75rem',
            height: '1.75rem',
            background: letter === activeCenter ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
            color: letter === activeCenter ? 'white' : 'var(--color-text-primary)',
            border: '1px solid ' + (letter === activeCenter ? 'var(--color-accent)' : 'var(--color-border)'),
          }"
        >{{ letter.toUpperCase() }}</div>
      </div>
      <span v-if="isDirty" class="text-xs px-1.5 py-0.5 rounded" style="background: #fbbf24; color: #78350f;">muokattu</span>
      <button
        v-if="canSave"
        @click="savePuzzle"
        class="rounded text-xs px-2.5 py-1"
        :style="{
          background: 'var(--color-accent)',
          color: 'white',
          border: '1px solid var(--color-accent)',
          cursor: 'pointer',
          opacity: saving ? '0.6' : '1',
        }"
      >{{ saving ? 'Tallennetaan…' : `Tallenna → ${displayNumber}` }}</button>
      <button
        v-if="isDirty && savedCombo"
        @click="loadSlot(currentSlot)"
        class="rounded text-xs px-1.5 py-0.5"
        :style="{ background: 'var(--color-bg-secondary)', color: 'var(--color-text-tertiary)', border: '1px solid var(--color-border)', cursor: 'pointer' }"
      >Palauta</button>
      <p v-if="saveError" class="text-xs" style="color: #ef4444;">{{ saveError }}</p>
    </div>

    <!-- ================================================================= -->
    <!-- Combination browser (with integrated center selector) -->
    <!-- ================================================================= -->
    <KennoCombinations
      :active-combination="activeCombo"
      :active-center="activeCenter"
      :center-disabled="centerSaving || saving"
      :initial-requires="savedCombo ? savedCombo.split('').join(',') : ''"
      @select-center="onSelectCenter"
    />

    <!-- ================================================================= -->
    <!-- Word list -->
    <!-- ================================================================= -->
    <div v-if="activeCenter" class="mt-4">
      <KennoWordList
        :words="words"
        :letters="activeLettersArray"
        :loading="wordsLoading"
        :error="wordsError"
        @block="blockWord"
      />
    </div>
  </div>
</template>
