<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuth } from '../composables/useAuth'

const { isAdmin } = useAuth()

// --- State ---
const puzzle = ref(null)
const outerLetters = ref([])
const currentWord = ref('')
const foundWords = ref(new Set())
const score = ref(0)
const message = ref('')
const messageType = ref('ok')
const loading = ref(true)
const fetchError = ref('')
const puzzleNumber = ref(null)
const totalPuzzles = ref(null)
const showRanks = ref(false)

// --- Computed ---
const center = computed(() => puzzle.value?.center ?? '')
const wordsSet = computed(() => new Set(puzzle.value?.words ?? []))
const allLetters = computed(() => new Set([center.value, ...outerLetters.value]))

const RANKS = [
  { pct: 100, name: 'Mehiläiskuningatar \uD83C\uDF6F' },
  { pct: 70,  name: 'Nero' },
  { pct: 50,  name: 'Hämmästyttävä' },
  { pct: 40,  name: 'Loistava' },
  { pct: 25,  name: 'Kiva' },
  { pct: 15,  name: 'Vakaa' },
  { pct: 8,   name: 'Hyvä' },
  { pct: 5,   name: 'Nouseva' },
  { pct: 2,   name: 'Hyvä alku' },
  { pct: 0,   name: 'Aloittelija' },
]

const rank = computed(() => {
  if (!puzzle.value || puzzle.value.max_score === 0) return 'Aloittelija'
  const pct = (score.value / puzzle.value.max_score) * 100
  for (const r of RANKS) {
    if (pct >= r.pct) return r.name
  }
  return 'Aloittelija'
})

const rankThresholds = computed(() => {
  const max = puzzle.value?.max_score ?? 0
  return [...RANKS].reverse().map(r => ({
    name: r.name,
    points: Math.ceil(r.pct / 100 * max),
    isCurrent: rank.value === r.name,
  }))
})

const sortedFoundWords = computed(() => [...foundWords.value].sort())

async function fetchPuzzle(overrideIndex) {
  loading.value = true
  fetchError.value = ''
  try {
    const url = overrideIndex != null ? `/api/bee?puzzle=${overrideIndex}` : '/api/bee'
    const res = await fetch(url)
    if (!res.ok) throw new Error('Verkkovirhe')
    const data = await res.json()
    puzzle.value = data
    outerLetters.value = [...data.letters]
    puzzleNumber.value = data.puzzle_number
    totalPuzzles.value = data.total_puzzles
  } catch {
    fetchError.value = 'Pelin lataaminen epäonnistui.'
  } finally {
    loading.value = false
  }
}

function switchPuzzle(delta) {
  if (!confirm('Vaihda peli? Edistyminen nollataan.')) return
  const next = ((puzzleNumber.value + delta) % totalPuzzles.value + totalPuzzles.value) % totalPuzzles.value
  currentWord.value = ''
  foundWords.value = new Set()
  score.value = 0
  message.value = ''
  showRanks.value = false
  fetchPuzzle(next)
}

// --- Honeycomb geometry ---
// Pointy-top hexagons, circumradius 50, centers on a 300×300 viewBox
const hexes = computed(() => {
  const R = 50                        // circumradius
  const dx = R * Math.sqrt(3)        // horizontal center-to-center distance  ≈ 86.6
  const dy = R * 1.5                  // vertical center-to-center distance   = 75
  const cx = 150, cy = 150           // center of the grid
  const ol = outerLetters.value
  return [
    { x: cx - dx / 2, y: cy - dy, letter: ol[0] ?? '', isCenter: false }, // top-left
    { x: cx + dx / 2, y: cy - dy, letter: ol[1] ?? '', isCenter: false }, // top-right
    { x: cx - dx,     y: cy,      letter: ol[2] ?? '', isCenter: false }, // mid-left
    { x: cx,          y: cy,      letter: center.value,isCenter: true  }, // center
    { x: cx + dx,     y: cy,      letter: ol[3] ?? '', isCenter: false }, // mid-right
    { x: cx - dx / 2, y: cy + dy, letter: ol[4] ?? '', isCenter: false }, // bot-left
    { x: cx + dx / 2, y: cy + dy, letter: ol[5] ?? '', isCenter: false }, // bot-right
  ]
})

function hexPoints(cx, cy, r) {
  const pts = []
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 180) * (60 * i - 30)
    pts.push(`${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`)
  }
  return pts.join(' ')
}

// --- Actions ---
function addLetter(letter) {
  currentWord.value += letter
}

function deleteLetter() {
  currentWord.value = currentWord.value.slice(0, -1)
}

function shuffleLetters() {
  const arr = [...outerLetters.value]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  outerLetters.value = arr
}

function submitWord() {
  const word = currentWord.value.toLowerCase()
  currentWord.value = ''

  if (word.length < 4) {
    showMessage('Liian lyhyt!', 'error')
    return
  }
  if (!word.includes(center.value)) {
    showMessage(`Kirjain '${center.value.toUpperCase()}' puuttuu!`, 'error')
    return
  }
  if ([...word].some(c => !allLetters.value.has(c))) {
    showMessage('Käytä vain annettuja kirjaimia!', 'error')
    return
  }
  if (foundWords.value.has(word)) {
    showMessage('Löysit jo tämän!', 'error')
    return
  }
  if (!wordsSet.value.has(word)) {
    showMessage('Ei sanakirjassa', 'error')
    return
  }

  // Valid word — calculate score
  const letterSet = new Set([center.value, ...outerLetters.value])
  const isPangram = [...letterSet].every(c => word.includes(c))
  const pts = word.length === 4 ? 1 : word.length
  const bonus = isPangram ? 7 : 0

  foundWords.value = new Set([...foundWords.value, word])
  score.value += pts + bonus

  if (isPangram) {
    showMessage('Pangrammi! \uD83D\uDC1D', 'special')
  } else {
    showMessage(`+${pts + bonus}`, 'ok')
  }
}

let msgTimer = null
function showMessage(msg, type) {
  message.value = msg
  messageType.value = type
  if (msgTimer) clearTimeout(msgTimer)
  msgTimer = setTimeout(() => { message.value = '' }, 2000)
}

function handleKeydown(e) {
  if (e.ctrlKey || e.altKey || e.metaKey) return
  if (!puzzle.value) return

  const key = e.key.toLowerCase()
  if (key === 'enter') {
    e.preventDefault()
    submitWord()
  } else if (key === 'backspace') {
    e.preventDefault()
    deleteLetter()
  } else if (/^[a-zäö]$/.test(key)) {
    addLetter(key)
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  fetchPuzzle()
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  if (msgTimer) clearTimeout(msgTimer)
})
</script>

<template>
  <div class="max-w-sm mx-auto">
    <!-- Loading / error -->
    <div v-if="loading" class="text-center py-16" style="color: var(--color-text-secondary)">
      Ladataan...
    </div>
    <div v-else-if="fetchError" class="text-center py-16 text-red-400" role="alert">
      {{ fetchError }}
    </div>

    <template v-else-if="puzzle">
      <!-- Score & rank -->
      <div class="flex items-center gap-3 mb-1">
        <span class="text-base font-medium" style="color: var(--color-text-primary)">
          Pisteet: {{ score }}
        </span>
        <button
          class="px-3 py-0.5 rounded-full text-sm font-medium"
          style="background: var(--color-accent); color: white; border: none; cursor: pointer;"
          @click="showRanks = !showRanks"
          :aria-expanded="showRanks"
          aria-label="Näytä tasorajat"
        >
          {{ rank }}
        </button>
      </div>

      <!-- Admin puzzle switcher -->
      <div v-if="isAdmin && totalPuzzles" class="flex items-center gap-2 mb-1 text-xs" style="color: var(--color-text-tertiary);">
        Peli {{ puzzleNumber + 1 }}/{{ totalPuzzles }}
        <button
          class="px-1.5 py-0.5 rounded"
          style="background: var(--color-bg-secondary); color: var(--color-text-secondary); border: 1px solid var(--color-border); cursor: pointer;"
          @click="switchPuzzle(-1)"
          aria-label="Edellinen peli"
        >◀</button>
        <button
          class="px-1.5 py-0.5 rounded"
          style="background: var(--color-bg-secondary); color: var(--color-text-secondary); border: 1px solid var(--color-border); cursor: pointer;"
          @click="switchPuzzle(1)"
          aria-label="Seuraava peli"
        >▶</button>
      </div>

      <!-- Rank thresholds -->
      <div v-if="showRanks" class="mb-3 p-3 rounded-lg text-sm" style="background: var(--color-bg-secondary); border: 1px solid var(--color-border);">
        <div
          v-for="r in rankThresholds"
          :key="r.name"
          class="flex justify-between py-0.5"
          :style="{ color: r.isCurrent ? 'var(--color-accent)' : 'var(--color-text-secondary)', fontWeight: r.isCurrent ? '600' : '400' }"
        >
          <span>{{ r.name }}</span>
          <span>{{ r.points }}</span>
        </div>
      </div>

      <div v-else class="mb-4"></div>

      <!-- Current word display -->
      <div
        class="text-center text-2xl tracking-widest mb-2 min-h-[2.5rem] font-light"
        style="color: var(--color-text-primary); font-family: var(--font-mono);"
      >
        <span v-if="currentWord">{{ currentWord.toUpperCase().split('').join(' ') }}</span>
        <span v-else style="color: var(--color-text-tertiary);">—</span>
      </div>

      <!-- Feedback message -->
      <div
        class="text-center text-sm font-medium mb-3 min-h-[1.25rem]"
        :style="{
          color: messageType === 'error'   ? '#ef4444'
               : messageType === 'special' ? 'var(--color-accent)'
               : 'var(--color-text-secondary)',
          opacity: message ? 1 : 0,
          transition: 'opacity 0.2s',
        }"
        role="status"
        aria-live="polite"
      >
        {{ message || '&nbsp;' }}
      </div>

      <!-- Honeycomb -->
      <div class="flex justify-center mb-5">
        <svg
          viewBox="18 18 264 264"
          width="264"
          height="264"
          aria-hidden="true"
          class="select-none"
        >
          <g
            v-for="(hex, i) in hexes"
            :key="i"
            style="cursor: pointer;"
            @click="addLetter(hex.letter)"
          >
            <polygon
              :points="hexPoints(hex.x, hex.y, 47)"
              :style="{
                fill:        hex.isCenter ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
                stroke:      hex.isCenter ? 'var(--color-accent)' : 'var(--color-border)',
                strokeWidth: '1.5',
              }"
            />
            <text
              :x="hex.x"
              :y="hex.y"
              text-anchor="middle"
              dominant-baseline="central"
              :style="{
                fill:           hex.isCenter ? '#ffffff' : 'var(--color-text-primary)',
                fontSize:       '20px',
                fontWeight:     hex.isCenter ? '700' : '500',
                fontFamily:     'var(--font-sans)',
                pointerEvents:  'none',
                userSelect:     'none',
              }"
            >
              {{ hex.letter.toUpperCase() }}
            </text>
          </g>
        </svg>
      </div>

      <!-- Controls -->
      <div class="flex justify-center gap-3 mb-8">
        <button
          class="px-4 py-2 rounded-lg text-sm font-medium"
          style="background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border);"
          @click="deleteLetter"
        >
          Poista
        </button>
        <button
          class="px-4 py-2 rounded-lg text-sm font-medium"
          style="background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border);"
          @click="shuffleLetters"
        >
          Sekoita
        </button>
        <button
          class="px-4 py-2 rounded-lg text-sm font-medium"
          style="background: var(--color-accent); color: white; border: 1px solid var(--color-accent);"
          @click="submitWord"
        >
          OK
        </button>
      </div>

      <!-- Found words -->
      <div v-if="foundWords.size > 0">
        <p class="text-sm mb-2" style="color: var(--color-text-secondary);">
          Löydetyt sanat ({{ foundWords.size }}):
        </p>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="word in sortedFoundWords"
            :key="word"
            class="px-3 py-0.5 rounded-full text-sm"
            style="background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border);"
          >
            {{ word }}
          </span>
        </div>
      </div>
    </template>
  </div>
</template>
