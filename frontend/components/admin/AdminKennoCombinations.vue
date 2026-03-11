<script setup>
import KennoVariationsGrid from './KennoVariationsGrid.vue'

const props = defineProps({
  // Currently active combination (letters string) — highlighted in the table
  activeCombination: { type: String, default: '' },
  // Currently active center letter — highlighted in the variations grid
  activeCenter: { type: String, default: '' },
  // Disable center selection (e.g. while saving)
  centerDisabled: { type: Boolean, default: false },
  // Initial value for the "requires" filter (e.g. today's center letter)
  initialRequires: { type: String, default: '' },
})

const emit = defineEmits(['select-center'])

// ---------------------------------------------------------------------------
// Filter state
// ---------------------------------------------------------------------------
const requiresInput = ref(props.initialRequires)
const excludesInput = ref('')
const minPangrams = ref(1)
const maxPangrams = ref(null)
const minWordsMax = ref(null)
const maxWordsMax = ref(null)
const minWordsMin = ref(null)
const maxWordsMin = ref(null)
const inRotation = ref('')
const sortBy = ref('pangrams')
const sortOrder = ref('desc')
const page = ref(1)
const perPage = ref(25)

// ---------------------------------------------------------------------------
// Results state
// ---------------------------------------------------------------------------
const combinations = ref([])
const total = ref(0)
const totalPages = ref(0)
const loading = ref(false)
const error = ref('')
const expandedLetters = ref(null)

// ---------------------------------------------------------------------------
// Debounced fetching
// ---------------------------------------------------------------------------
let debounceTimer = null

function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    fetchCombinations()
  }, 300)
}

watch([requiresInput, excludesInput, minPangrams, maxPangrams, minWordsMax, maxWordsMax, minWordsMin, maxWordsMin, inRotation], debouncedFetch)
watch([sortBy, sortOrder], () => {
  page.value = 1
  fetchCombinations()
})
watch(page, fetchCombinations)

// When the parent sets a new activeCombination, auto-expand that row if visible
watch(() => props.activeCombination, (letters) => {
  if (letters) expandedLetters.value = letters
})

// Sync requires filter when the parent loads a different puzzle
watch(() => props.initialRequires, (val) => {
  if (val) requiresInput.value = val
})

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

async function fetchCombinations() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams()
    if (requiresInput.value.trim()) params.set('requires', requiresInput.value.trim())
    if (excludesInput.value.trim()) params.set('excludes', excludesInput.value.trim())
    if (minPangrams.value > 1) params.set('min_pangrams', minPangrams.value)
    if (maxPangrams.value != null) params.set('max_pangrams', maxPangrams.value)
    if (minWordsMax.value != null) params.set('min_words', minWordsMax.value)
    if (maxWordsMax.value != null) params.set('max_words', maxWordsMax.value)
    if (minWordsMin.value != null) params.set('min_words_min', minWordsMin.value)
    if (maxWordsMin.value != null) params.set('max_words_min', maxWordsMin.value)
    if (inRotation.value) params.set('in_rotation', inRotation.value)
    params.set('sort', sortBy.value)
    params.set('order', sortOrder.value)
    params.set('page', page.value)
    params.set('per_page', perPage.value)

    const res = await fetch(`/api/kenno/combinations?${params}`)
    if (!res.ok) throw new Error('Haku epäonnistui')
    const data = await res.json()
    combinations.value = data.combinations
    total.value = data.total
    totalPages.value = data.pages
  } catch (e) {
    error.value = e.message
    combinations.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function toggleExpand(letters) {
  expandedLetters.value = expandedLetters.value === letters ? null : letters
}

function toggleSort(col) {
  if (sortBy.value === col) {
    sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
  } else {
    sortBy.value = col
    sortOrder.value = 'desc'
  }
}

function sortIndicator(col) {
  if (sortBy.value !== col) return ''
  return sortOrder.value === 'desc' ? ' ▼' : ' ▲'
}

function formatRange(min, max) {
  if (min === max) return String(min)
  return `${min}–${max}`
}

function onCenterClick(combo, center) {
  emit('select-center', combo.letters, center)
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
onMounted(fetchCombinations)
</script>

<template>
  <div>
    <!-- Filters -->
    <div class="flex flex-wrap items-end gap-x-3 gap-y-2 mb-2">
      <div class="flex flex-col gap-0.5">
        <label class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Sisältää</label>
        <input
          type="text"
          v-model="requiresInput"
          placeholder="a,ö,k"
          class="rounded"
          style="width: 6rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 6px; font-size: 0.875rem; font-family: var(--font-mono);"
        />
      </div>
      <div class="flex flex-col gap-0.5">
        <label class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Ei sisällä</label>
        <input
          type="text"
          v-model="excludesInput"
          placeholder="b,c,d"
          class="rounded"
          style="width: 6rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 6px; font-size: 0.875rem; font-family: var(--font-mono);"
        />
      </div>
      <div class="flex flex-col gap-0.5">
        <label class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Pangrammit</label>
        <div class="flex items-center gap-1">
          <input type="number" v-model.number="minPangrams" min="1" class="rounded text-center" style="width: 3.5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;" />
          <span class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">–</span>
          <input type="number" v-model.number="maxPangrams" min="1" placeholder="∞" class="rounded text-center" style="width: 3.5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;" />
        </div>
      </div>
      <div class="flex flex-col gap-0.5">
        <label class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Sanoja (paras)</label>
        <div class="flex items-center gap-1">
          <input type="number" v-model.number="minWordsMax" min="1" placeholder="min" class="rounded text-center" style="width: 3.5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;" />
          <span class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">–</span>
          <input type="number" v-model.number="maxWordsMax" min="1" placeholder="max" class="rounded text-center" style="width: 3.5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;" />
        </div>
      </div>
      <div class="flex flex-col gap-0.5">
        <label class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Sanoja (heikoin)</label>
        <div class="flex items-center gap-1">
          <input type="number" v-model.number="minWordsMin" min="1" placeholder="min" class="rounded text-center" style="width: 3.5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;" />
          <span class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">–</span>
          <input type="number" v-model.number="maxWordsMin" min="1" placeholder="max" class="rounded text-center" style="width: 3.5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 4px; font-size: 0.875rem;" />
        </div>
      </div>
      <div class="flex flex-col gap-0.5">
        <label class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Kierrossa</label>
        <select v-model="inRotation" class="rounded" style="background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 2px 6px; font-size: 0.875rem;">
          <option value="">Kaikki</option>
          <option value="true">Kyllä</option>
          <option value="false">Ei</option>
        </select>
      </div>
    </div>

    <!-- Status + pagination inline -->
    <div class="flex items-center gap-3 mb-1">
      <p class="text-xs" :style="{ color: error ? '#ef4444' : 'var(--color-text-tertiary)' }">
        {{ error || (loading ? 'Haetaan…' : `${total} yhdistelmää`) }}
      </p>
      <div v-if="totalPages > 1" class="flex items-center gap-1">
        <button @click="page = Math.max(1, page - 1)" :disabled="page <= 1" class="rounded text-xs px-1.5 py-0.5" :style="{ background: 'var(--color-bg-secondary)', color: page > 1 ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)', border: '1px solid var(--color-border)', cursor: page > 1 ? 'pointer' : 'default' }">&#8592;</button>
        <span class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">{{ page }}/{{ totalPages }}</span>
        <button @click="page = Math.min(totalPages, page + 1)" :disabled="page >= totalPages" class="rounded text-xs px-1.5 py-0.5" :style="{ background: 'var(--color-bg-secondary)', color: page < totalPages ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)', border: '1px solid var(--color-border)', cursor: page < totalPages ? 'pointer' : 'default' }">&#8594;</button>
      </div>
    </div>

    <!-- Results table -->
    <div v-if="combinations.length > 0" :style="{ border: '1px solid var(--color-border)', borderRadius: '4px', maxHeight: '24rem', overflowY: 'auto' }">
      <table class="w-full text-sm" style="border-collapse: collapse;">
        <thead style="position: sticky; top: 0; z-index: 1;">
          <tr :style="{ background: 'var(--color-bg-secondary)' }">
            <th class="text-left px-2 py-1.5 cursor-pointer select-none" :style="{ color: 'var(--color-text-secondary)', borderBottom: '1px solid var(--color-border)' }" @click="toggleSort('letters')">Kirjaimet{{ sortIndicator('letters') }}</th>
            <th class="text-right px-2 py-1.5 cursor-pointer select-none" :style="{ color: 'var(--color-text-secondary)', borderBottom: '1px solid var(--color-border)' }" @click="toggleSort('pangrams')">Pg{{ sortIndicator('pangrams') }}</th>
            <th class="text-right px-2 py-1.5 cursor-pointer select-none" :style="{ color: 'var(--color-text-secondary)', borderBottom: '1px solid var(--color-border)' }" @click="toggleSort('words_max')">Sanoja &#9650;{{ sortIndicator('words_max') }}</th>
            <th class="text-right px-2 py-1.5 cursor-pointer select-none" :style="{ color: 'var(--color-text-secondary)', borderBottom: '1px solid var(--color-border)' }" @click="toggleSort('words_min')">Sanoja &#9660;{{ sortIndicator('words_min') }}</th>
            <th class="text-right px-2 py-1.5 cursor-pointer select-none" :style="{ color: 'var(--color-text-secondary)', borderBottom: '1px solid var(--color-border)' }" @click="toggleSort('score_max')">Pisteet{{ sortIndicator('score_max') }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="combo in combinations" :key="combo.letters">
            <tr
              class="cursor-pointer hover:opacity-80"
              :style="{
                background: activeCombination === combo.letters
                  ? 'rgba(255, 100, 62, 0.15)'
                  : expandedLetters === combo.letters
                    ? 'rgba(255, 100, 62, 0.06)'
                    : 'transparent',
                borderBottom: expandedLetters === combo.letters ? 'none' : '1px solid var(--color-border)',
              }"
              @click="toggleExpand(combo.letters)"
            >
              <td class="px-2 py-1.5" style="font-family: var(--font-mono); letter-spacing: 0.1em;" :style="{ color: 'var(--color-text-primary)' }">
                {{ combo.letters.toUpperCase() }}
                <span v-if="combo.in_rotation" class="ml-1 px-1 rounded" style="background: var(--color-accent); color: white; font-size: 0.625rem; letter-spacing: 0;">kierrossa</span>
              </td>
              <td class="text-right px-2 py-1.5" :style="{ color: 'var(--color-text-secondary)' }">{{ combo.total_pangrams }}</td>
              <td class="text-right px-2 py-1.5" :style="{ color: 'var(--color-text-secondary)' }">{{ combo.max_word_count }}</td>
              <td class="text-right px-2 py-1.5" :style="{ color: 'var(--color-text-tertiary)' }">{{ combo.min_word_count }}</td>
              <td class="text-right px-2 py-1.5" :style="{ color: 'var(--color-text-secondary)' }">{{ formatRange(combo.min_max_score, combo.max_max_score) }}</td>
            </tr>
            <!-- Expanded row: variations grid as center selector -->
            <tr v-if="expandedLetters === combo.letters" :style="{ borderBottom: '1px solid var(--color-border)' }">
              <td colspan="5" class="px-2 py-2" :style="{ background: 'rgba(255, 100, 62, 0.04)' }">
                <p class="text-xs mb-1.5" :style="{ color: 'var(--color-text-tertiary)' }">Valitse keskuskirjain:</p>
                <KennoVariationsGrid
                  :variations="combo.variations"
                  :active-center="activeCombination === combo.letters ? activeCenter : ''"
                  :disabled="centerDisabled"
                  :show-target="true"
                  @select="center => onCenterClick(combo, center)"
                />
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- No results -->
    <p v-else-if="!loading && !error" class="text-xs py-2" :style="{ color: 'var(--color-text-tertiary)' }">
      Ei tuloksia nykyisillä suodattimilla.
    </p>
  </div>
</template>
