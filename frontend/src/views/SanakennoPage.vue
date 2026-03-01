<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useAuth } from '../composables/useAuth'
import { trackPageView } from '../composables/usePageView'
import ThemeToggle from '../components/ThemeToggle.vue'

const { isAdmin } = useAuth()

// --- Persistence keys ---
function stateKey(n) { return `sanakenno_state_${n}` }
const LEGACY_STATE_KEY = 'sanakenno_state'  // migration from single-key format

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
const puzzleInputDisplay = ref(1)   // 1-indexed for the admin number input
const showHints = ref(false)
const showRules = ref(false)
const showRemainingWords = ref(false)
const hintsUnlocked = ref(new Set())  // 'summary' | 'letters' | 'distribution'

// --- Center variation selector (admin) ---
const variations = ref([])
const variationsLoading = ref(false)
const centerSaving = ref(false)

async function fetchVariations() {
  if (!isAdmin.value || puzzleNumber.value == null) return
  variationsLoading.value = true
  try {
    const res = await fetch(`/api/bee/variations?puzzle=${puzzleNumber.value}`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    variations.value = data.variations
  } catch {
    variations.value = []
  } finally {
    variationsLoading.value = false
  }
}

async function setCenter(letter) {
  if (centerSaving.value) return
  centerSaving.value = true
  try {
    const res = await fetch('/api/bee/center', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ puzzle: puzzleNumber.value, center: letter }),
    })
    if (!res.ok) throw new Error()
    // Reload the puzzle with the new center + refresh variations
    resetGameState()
    await fetchPuzzle(puzzleNumber.value)
    await fetchVariations()
  } catch {
    showMessage('Could not change center letter', 'error')
  } finally {
    centerSaving.value = false
  }
}

// --- Animation state ---
const wordShake = ref(false)
const wordRejected = ref(false)   // keeps the typed word visible after a failed submit
const pressedHexIndex = ref(null)
const lastResubmittedWord = ref(null)
let resubTimer = null
let rejectTimer = null
const shareCopied = ref(false)
let shareCopiedTimer = null
const startedAt = ref(null)           // epoch ms, set on first load of each puzzle
const totalPausedMs = ref(0)          // accumulated ms the tab was hidden
let hiddenAt = null                   // non-reactive: when the tab was last hidden

// --- Computed ---
const center = computed(() => puzzle.value?.center ?? '')
const wordsSet = computed(() => new Set(puzzle.value?.words ?? []))
const allLetters = computed(() => new Set([center.value, ...outerLetters.value]))
const allWords = computed(() => puzzle.value?.words ?? [])

const RANKS = [
  { pct: 100, name: 'Täysi kenno' },
  { pct: 70,  name: 'Ällistyttävä' },
  { pct: 40,  name: 'Sanavalmis' },
  { pct: 20,  name: 'Onnistuja' },
  { pct: 10,  name: 'Nyt mennään!' },
  { pct: 2,   name: 'Hyvä alku' },
  { pct: 0,   name: 'Etsi sanoja!' },
]

const HINT_ICONS = { summary: '📊', letters: '🔤', distribution: '📏', pairs: '🔠' }

const HINT_SVG = {
  bulb: '<svg xmlns="http://www.w3.org/2000/svg" width="1.15em" height="1.15em" viewBox="-1 -1 40 64" fill="none" stroke="currentColor" aria-hidden="true" style="vertical-align: -0.3em;" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.6,48l20.6-3c0-6.5,8.8-14.6,8.8-25.6C38,8.7,29.5,0,19,0S0,8.7,0,19.4c0,10.9,8.6,19,8.6,25.5V48z"/><path d="M10,52.3l18.8-2.9"/><path d="M10,56.2l18.8-2.9"/><path d="M26.3,59.1c0,1.6-3.1,2.9-7,2.9s-7-1.3-7-2.9"/><path d="M16.4,40.8c0-12.4-3.5-16.8-3.5-16.8s1.4,3.1,3,3.1c1.7,0,3-1.4,3-3.1c0,1.7,1.4,3.1,3,3.1c1.7,0,3-3.1,3-3.1s-2.8,6.7-2.8,16.8"/></svg>',
  summary: '<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 64 64" fill="none" stroke="currentColor" aria-hidden="true"><circle cx="28" cy="28" r="26" stroke-width="5"/><circle cx="28" cy="28" r="22" stroke-width="1.5"/><path d="M60.828,60.828c-1.562,1.562-4.095,1.562-5.656,0L44.769,50.425c2.145-1.606,4.051-3.513,5.657-5.656l10.402,10.402C62.391,56.732,62.391,59.266,60.828,60.828z" fill="currentColor" stroke="none"/><line x1="46" y1="46" x2="52" y2="52" stroke-width="5" stroke-linecap="round"/></svg>',
  letters: '<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 180 300" fill="currentColor" stroke="currentColor" stroke-width="8" stroke-linejoin="round" aria-hidden="true"><path d="M92.5,15.7c-0.4-1.3-1.2-2.4-2.2-3.3l-0.1-0.1c-0.5-0.4-1-0.7-1.5-1c-0.3-0.2-0.6-0.3-0.9-0.4c-0.5-0.2-1-0.3-1.5-0.4c-1.2-0.3-2.5-0.3-3.8,0.1l-0.1,0c-0.5,0.2-0.9,0.3-1.3,0.5c-0.4,0.2-0.8,0.5-1.2,0.7c-0.3,0.2-0.7,0.5-1,0.8c-0.3,0.3-0.6,0.6-0.9,1c-0.2,0.3-0.5,0.7-0.7,1c-0.2,0.3-0.4,0.7-0.6,1.1c-0.2,0.4-0.3,0.7-0.4,1.1L0.8,280.5c-1.1,3.8,1,7.8,4.8,8.9c0.7,0.2,1.4,0.3,2,0.3c3.1,0,5.9-2,6.8-5.1l17.6-59.2h113.8l19.2,59.3c1,3,3.8,4.9,6.8,4.9c0.7,0,1.5-0.1,2.2-0.3c3.8-1.2,5.8-5.3,4.6-9L92.5,15.7zM35.8,210.6L86,41.9l54.7,168.7H35.8z"/></svg>',
  distribution: '<svg xmlns="http://www.w3.org/2000/svg" width="1.15em" height="1em" viewBox="0 0 20 14" fill="currentColor" stroke="currentColor" aria-hidden="true"><rect x="0.5" y="0.5" width="19" height="13" rx="1" fill="none" stroke-width="1.3"/><line x1="4" y1="0.5" x2="4" y2="5" stroke-width="1"/><line x1="8" y1="0.5" x2="8" y2="7.5" stroke-width="1"/><line x1="12" y1="0.5" x2="12" y2="5" stroke-width="1"/><line x1="16" y1="0.5" x2="16" y2="7.5" stroke-width="1"/></svg>',
  pairs: '<svg xmlns="http://www.w3.org/2000/svg" width="1.15em" height="1em" viewBox="0 0 300 300" fill="currentColor" stroke="currentColor" stroke-width="8" stroke-linejoin="round" aria-hidden="true"><path d="M92.5,15.7c-0.4-1.3-1.2-2.4-2.2-3.3l-0.1-0.1c-0.5-0.4-1-0.7-1.5-1c-0.3-0.2-0.6-0.3-0.9-0.4c-0.5-0.2-1-0.3-1.5-0.4c-1.2-0.3-2.5-0.3-3.8,0.1l-0.1,0c-0.5,0.2-0.9,0.3-1.3,0.5c-0.4,0.2-0.8,0.5-1.2,0.7c-0.3,0.2-0.7,0.5-1,0.8c-0.3,0.3-0.6,0.6-0.9,1c-0.2,0.3-0.5,0.7-0.7,1c-0.2,0.3-0.4,0.7-0.6,1.1c-0.2,0.4-0.3,0.7-0.4,1.1L0.8,280.5c-1.1,3.8,1,7.8,4.8,8.9c0.7,0.2,1.4,0.3,2,0.3c3.1,0,5.9-2,6.8-5.1l17.6-59.2h113.8l19.2,59.3c1,3,3.8,4.9,6.8,4.9c0.7,0,1.5-0.1,2.2-0.3c3.8-1.2,5.8-5.3,4.6-9L92.5,15.7zM35.8,210.6L86,41.9l54.7,168.7H35.8z"/><path d="M298.8,166.5c-7.7-12-18.2-19.3-31.4-21.8c-32.5-6.2-69.5,20.2-71.1,21.3c-3.2,2.3-3.9,6.8-1.6,10s6.8,3.9,10,1.6c0.3-0.2,33.4-23.9,60.1-18.9c8.7,1.6,15.5,6.2,20.9,13.8v24.6c-16.5-0.9-61-1.1-82.9,19.1c-8.7,8-13,18.1-12.8,30.1c0.2,16.6,9.2,29.6,25.2,36.7c9.1,4,20.1,6,31.4,6c13.8,0,27.9-2.9,39.1-8.3v1.3c0,3.9,3.2,7.1,7.1,7.1s7.1-3.2,7.2-7.1V170.4C299.9,169,299.5,167.6,298.8,166.5zM220.9,270c-11-4.9-16.6-12.9-16.8-23.9c-0.1-7.9,2.6-14.2,8.2-19.4c18.1-16.6,59.1-16,73.2-15.3v52.9C271.5,274.3,241.2,279,220.9,270z"/></svg>',
}

const rank = computed(() => {
  if (!puzzle.value || puzzle.value.max_score === 0) return RANKS[RANKS.length - 1].name
  const pct = (score.value / puzzle.value.max_score) * 100
  for (const r of RANKS) {
    if (pct >= r.pct) return r.name
  }
  return RANKS[RANKS.length - 1].name
})

const rankThresholds = computed(() => {
  const max = puzzle.value?.max_score ?? 0
  return [...RANKS].reverse().map(r => ({
    name: r.name,
    points: Math.ceil(r.pct / 100 * max),
    isCurrent: rank.value === r.name,
  }))
})

const progressToNextRank = computed(() => {
  if (!puzzle.value || puzzle.value.max_score === 0) return 0
  const max = puzzle.value.max_score
  const scorePct = (score.value / max) * 100
  const currentIdx = RANKS.findIndex(r => scorePct >= r.pct)
  if (currentIdx === -1) return 0
  if (currentIdx === 0) return 100
  const currentRankPts = Math.ceil(RANKS[currentIdx].pct / 100 * max)
  const nextRankPts = Math.ceil(RANKS[currentIdx - 1].pct / 100 * max)
  if (nextRankPts <= currentRankPts) return 100
  return Math.min(100, ((score.value - currentRankPts) / (nextRankPts - currentRankPts)) * 100)
})

const allFound = computed(() =>
  puzzle.value !== null && allWords.value.length > 0 && foundWords.value.size === allWords.value.length
)

// Colour each character of the word being typed:
//   center letter  → accent (orange)
//   other puzzle letter → text-primary
//   dash           → text-tertiary (structural, not a letter)
//   anything else  → text-tertiary (invalid, will fail validation)
const currentWordChars = computed(() =>
  [...currentWord.value].map(char => {
    if (char === '-')              return { char, color: 'var(--color-text-tertiary)' }
    if (char === center.value)     return { char, color: 'var(--color-accent)' }
    if (allLetters.value.has(char)) return { char, color: 'var(--color-text-primary)' }
    return { char, color: 'var(--color-text-tertiary)' }
  })
)

// Admin: all words not yet found, same sort as found words
const remainingWords = computed(() =>
  allWords.value.filter(w => !foundWords.value.has(w)).sort((a, b) => a.localeCompare(b) || a.length - b.length)
)

async function blockWord(word) {
  if (!confirm(`Remove "${word}" from the word list permanently?`)) return
  try {
    const res = await fetch('/api/bee/block', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word }),
    })
    if (!res.ok) throw new Error()
    // Update local state immediately without a full refetch
    const letterSet = new Set([center.value, ...outerLetters.value])
    const isPangram = [...letterSet].every(c => word.includes(c))
    const pts = word.length === 4 ? 1 : word.length
    const bonus = isPangram ? 7 : 0
    puzzle.value = {
      ...puzzle.value,
      words: puzzle.value.words.filter(w => w !== word),
      max_score: puzzle.value.max_score - pts - bonus,
    }
  } catch {
    showMessage('Could not remove word', 'error')
  }
}

// Primary sort: alphabetical. Secondary: length (shortest first) as tiebreaker.
const sortedFoundWords = computed(() =>
  [...foundWords.value].sort((a, b) => a.localeCompare(b) || a.length - b.length)
)

const WORDS_PER_COLUMN = 10
function toColumns(words) {
  const cols = []
  for (let i = 0; i < words.length; i += WORDS_PER_COLUMN) {
    cols.push(words.slice(i, i + WORDS_PER_COLUMN))
  }
  return cols
}
const wordColumns = computed(() => toColumns(sortedFoundWords.value))
const remainingWordColumns = computed(() => toColumns(remainingWords.value))

// --- Hint computeds ---
// Hint 2: remaining words per starting letter, sorted alphabetically
const letterMap = computed(() => {
  const map = {}
  for (const word of allWords.value) {
    const l = word[0]
    if (!map[l]) map[l] = { total: 0, found: 0 }
    map[l].total++
    if (foundWords.value.has(word)) map[l].found++
  }
  return Object.entries(map)
    .map(([letter, { total, found }]) => ({ letter, remaining: total - found }))
    .sort((a, b) => a.letter.localeCompare(b.letter))
})

// Hint 1 (summary): longest unfound word + unique unfound lengths
const unfoundLengths = computed(() => {
  const unfound = allWords.value.filter(w => !foundWords.value.has(w))
  if (unfound.length === 0) return null
  const lengths = new Set()
  let longest = 0
  for (const w of unfound) {
    lengths.add(w.length)
    if (w.length > longest) longest = w.length
  }
  return { longest, uniqueLengths: lengths.size }
})

const pangramStats = computed(() => {
  if (!puzzle.value) return { total: 0, found: 0, remaining: 0 }
  const letterSet = new Set([center.value, ...outerLetters.value])
  const pangrams = allWords.value.filter(w => [...letterSet].every(c => w.includes(c)))
  const found = pangrams.filter(w => foundWords.value.has(w)).length
  return { total: pangrams.length, found, remaining: pangrams.length - found }
})

// Hint 3: word count per length (remaining)
const lengthDistribution = computed(() => {
  const dist = {}
  for (const word of allWords.value) {
    const len = word.length
    if (!dist[len]) dist[len] = { total: 0, found: 0 }
    dist[len].total++
    if (foundWords.value.has(word)) dist[len].found++
  }
  return Object.entries(dist)
    .map(([len, { total, found }]) => ({ len: parseInt(len), total, remaining: total - found }))
    .sort((a, b) => a.len - b.len)
})

// Hint 4: remaining words per two-letter pair, sorted alphabetically
const pairMap = computed(() => {
  const map = {}
  for (const word of allWords.value) {
    const pair = word.slice(0, 2)
    if (!map[pair]) map[pair] = { total: 0, found: 0 }
    map[pair].total++
    if (foundWords.value.has(word)) map[pair].found++
  }
  return Object.entries(map)
    .map(([pair, { total, found }]) => ({ pair, remaining: total - found }))
    .sort((a, b) => a.pair.localeCompare(b.pair))
})

// --- Favicon swap ---
// Pointy-top hexagon matching the game's honeycomb geometry, orange accent color
const BEE_FAVICON = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><polygon points='90.7,26.5 90.7,73.5 50,97 9.3,73.5 9.3,26.5 50,3' fill='%23ff643e'/></svg>"
let _originalFavicon = null

function _swapFavicon(href) {
  const el = document.querySelector("link[rel='icon']")
  if (el) { _originalFavicon = el.href; el.href = href }
}
function _restoreFavicon() {
  const el = document.querySelector("link[rel='icon']")
  if (el && _originalFavicon) el.href = _originalFavicon
}

// --- Timer helpers ---
function getElapsedMs() {
  if (!startedAt.value) return 0
  return Date.now() - startedAt.value - totalPausedMs.value
}

function handleVisibilityChange() {
  if (document.hidden) {
    hiddenAt = Date.now()
  } else {
    if (hiddenAt !== null) {
      totalPausedMs.value += Date.now() - hiddenAt
      hiddenAt = null
    }
  }
}

function handlePageHide() {
  // Fired when page may be unloaded/backgrounded (more reliable on mobile)
  if (hiddenAt === null) {
    hiddenAt = Date.now()
  }
}

// --- State persistence (per-puzzle localStorage) ---
function saveState() {
  if (puzzleNumber.value == null) return
  localStorage.setItem(stateKey(puzzleNumber.value), JSON.stringify({
    foundWords: [...foundWords.value],
    score: score.value,
    hintsUnlocked: [...hintsUnlocked.value],
    startedAt: startedAt.value,
    totalPausedMs: totalPausedMs.value,
  }))
}

function recalcScore(words) {
  const letterSet = new Set([center.value, ...outerLetters.value])
  let total = 0
  for (const w of words) {
    const pts = w.length === 4 ? 1 : w.length
    const isPangram = [...letterSet].every(c => w.includes(c))
    total += pts + (isPangram ? 7 : 0)
  }
  return total
}

function loadState() {
  try {
    // Try per-puzzle key first
    let raw = localStorage.getItem(stateKey(puzzleNumber.value))

    // Migrate from legacy single-key format
    if (!raw) {
      const legacy = localStorage.getItem(LEGACY_STATE_KEY)
      if (legacy) {
        const legacyData = JSON.parse(legacy)
        if (legacyData.puzzleNumber === puzzleNumber.value) {
          raw = legacy
        }
        localStorage.removeItem(LEGACY_STATE_KEY)
      }
    }

    if (!raw) return
    const saved = JSON.parse(raw)
    const validWords = (saved.foundWords || []).filter(w => wordsSet.value.has(w))
    foundWords.value = new Set(validWords)
    score.value = validWords.length === (saved.foundWords || []).length ? saved.score : recalcScore(validWords)
    hintsUnlocked.value = new Set(saved.hintsUnlocked ?? [])
    startedAt.value = saved.startedAt ?? null
    totalPausedMs.value = saved.totalPausedMs ?? 0
  } catch { /* ignore corrupt data */ }
}

// --- Puzzle fetching ---
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
    puzzleInputDisplay.value = data.puzzle_number + 1
    loadState()
    if (startedAt.value === null) startedAt.value = Date.now()
    if (isAdmin.value) fetchVariations()
  } catch {
    fetchError.value = 'Lataus epäonnistui.'
  } finally {
    loading.value = false
  }
}

// --- Admin puzzle switcher ---
function resetGameState() {
  currentWord.value = ''
  foundWords.value = new Set()
  score.value = 0
  message.value = ''
  showRanks.value = false
  showRemainingWords.value = false
  hintsUnlocked.value = new Set()
  startedAt.value = null
  totalPausedMs.value = 0
  hiddenAt = null
}

function choosePuzzle(idx) {
  const target = ((idx % totalPuzzles.value) + totalPuzzles.value) % totalPuzzles.value
  saveState()  // persist current puzzle progress before switching
  resetGameState()
  fetchPuzzle(target)
}

function randomPuzzle() {
  choosePuzzle(Math.floor(Math.random() * totalPuzzles.value))
}

// --- Hints ---
function unlockHint(id) {
  hintsUnlocked.value = new Set([...hintsUnlocked.value, id])
  saveState()
}

// --- Share / copy status ---
function formatElapsed(ms) {
  const mins = Math.floor(ms / 60000)
  if (mins < 60) return `${mins} min`
  return `${Math.floor(mins / 60)} h ${mins % 60} min`
}

async function copyStatus() {
  const hintEmojis = [...hintsUnlocked.value].map(id => HINT_ICONS[id] || '').join('') || '–'

  const lines = [
    `Sanakenno — Peli ${(puzzleNumber.value ?? 0) + 1}`,
    rank.value,
    `${score.value}/${puzzle.value?.max_score ?? '?'} pistettä`,
    `Avut: ${hintEmojis}`,
    `https://erez.ac/sanakenno`,
  ]

  try {
    await navigator.clipboard.writeText(lines.join('\n'))
    shareCopied.value = true
    if (shareCopiedTimer) clearTimeout(shareCopiedTimer)
    shareCopiedTimer = setTimeout(() => { shareCopied.value = false }, 3000)
  } catch {
    showMessage('Kopiointi ei onnistunut', 'error')
  }
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
  if (wordRejected.value) {
    currentWord.value = ''
    wordRejected.value = false
    if (rejectTimer) { clearTimeout(rejectTimer); rejectTimer = null }
  }
  currentWord.value += letter
}

function deleteLetter() {
  if (wordRejected.value) {
    currentWord.value = ''
    wordRejected.value = false
    if (rejectTimer) { clearTimeout(rejectTimer); rejectTimer = null }
    return
  }
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

function triggerShake() {
  wordShake.value = false
  nextTick(() => {
    wordShake.value = true
    setTimeout(() => { wordShake.value = false }, 400)
  })
}

function rejectWord(msg) {
  wordRejected.value = true
  showMessage(msg, 'error')
  triggerShake()
  if (rejectTimer) clearTimeout(rejectTimer)
  rejectTimer = setTimeout(() => {
    currentWord.value = ''
    wordRejected.value = false
  }, 2000)
}

function submitWord() {
  // Normalise: strip dashes so lähi-itä and lähiitä both work
  const word = currentWord.value.toLowerCase().replace(/-/g, '')

  if (word.length < 4) {
    rejectWord('Liian lyhyt!'); return
  }
  if (!word.includes(center.value)) {
    rejectWord(`Kirjain '${center.value.toUpperCase()}' puuttuu!`); return
  }
  if ([...word].some(c => !allLetters.value.has(c))) {
    rejectWord('Käytä vain annettuja kirjaimia!'); return
  }
  if (foundWords.value.has(word)) {
    rejectWord('Löysit jo tämän!')
    lastResubmittedWord.value = word
    if (resubTimer) clearTimeout(resubTimer)
    resubTimer = setTimeout(() => { lastResubmittedWord.value = null }, 1500)
    return
  }
  if (!wordsSet.value.has(word)) {
    rejectWord('Ei sanakirjassa'); return
  }

  // Valid — clear the input
  currentWord.value = ''
  wordRejected.value = false

  // Valid word — calculate score
  const rankBefore = rank.value
  const letterSet = new Set([center.value, ...outerLetters.value])
  const isPangram = [...letterSet].every(c => word.includes(c))
  const pts = word.length === 4 ? 1 : word.length
  const bonus = isPangram ? 7 : 0

  foundWords.value = new Set([...foundWords.value, word])
  score.value += pts + bonus
  saveState()

  const rankAfter = rank.value
  if (rankAfter !== rankBefore) {
    showMessage('Uusi taso: ' + rankAfter + '!', 'special', 3000)
  } else if (isPangram) {
    showMessage('Pangrammi!', 'special')
  } else {
    showMessage(`+${pts + bonus}`, 'ok')
  }
}

let msgTimer = null
function showMessage(msg, type, duration = 2000) {
  message.value = msg
  messageType.value = type
  if (msgTimer) clearTimeout(msgTimer)
  msgTimer = setTimeout(() => { message.value = '' }, duration)
}

function handleKeydown(e) {
  if (e.key === 'Escape') { showRules.value = false; return }
  if (e.ctrlKey || e.altKey || e.metaKey) return
  if (e.target.tagName === 'INPUT') return
  if (showRules.value) return
  if (!puzzle.value) return

  const key = e.key.toLowerCase()
  if (key === 'enter') {
    e.preventDefault()
    submitWord()
  } else if (key === 'backspace') {
    e.preventDefault()
    deleteLetter()
  } else if (/^[a-zäö\-]$/.test(key)) {
    addLetter(key)
  }
}

onMounted(() => {
  trackPageView('/sanakenno')
  _swapFavicon(BEE_FAVICON)
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('blur', handleVisibilityChange)
  window.addEventListener('pagehide', handlePageHide)
  fetchPuzzle()
})

onUnmounted(() => {
  _restoreFavicon()
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('blur', handleVisibilityChange)
  window.removeEventListener('pagehide', handlePageHide)
  if (msgTimer) clearTimeout(msgTimer)
  if (resubTimer) clearTimeout(resubTimer)
  if (rejectTimer) clearTimeout(rejectTimer)
  if (shareCopiedTimer) clearTimeout(shareCopiedTimer)
})
</script>

<template>
  <!-- Minimal standalone top bar -->
  <div class="max-w-sm mx-auto flex justify-between items-center mb-4">
    <router-link to="/" class="text-sm" style="color: var(--color-text-tertiary);">← erez.ac</router-link>
    <div class="flex items-center gap-1">
      <button
        @click="showRules = true"
        class="p-2 rounded-lg transition-colors duration-200 hover:bg-white/10 text-sm font-semibold"
        style="color: var(--color-text-tertiary);"
        aria-label="Säännöt"
      >?</button>
      <ThemeToggle style="color: var(--color-text-tertiary);" />
    </div>
  </div>

  <!-- Rules modal -->
  <Teleport to="body">
    <div
      v-if="showRules"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      style="background: rgba(0,0,0,0.6);"
      @click.self="showRules = false"
    >
      <div
        class="w-full max-w-sm rounded-xl p-6 overflow-y-auto max-h-[90vh]"
        style="background: var(--color-bg-primary); border: 1px solid var(--color-border);"
        role="dialog"
        aria-modal="true"
        aria-label="Säännöt"
      >
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold" style="color: var(--color-text-primary);">Ohjeet</h2>
          <button
            @click="showRules = false"
            class="p-1 rounded hover:bg-white/10 text-xl leading-none"
            style="color: var(--color-text-tertiary);"
            aria-label="Sulje"
          >✕</button>
        </div>

        <div class="text-sm space-y-4" style="color: var(--color-text-secondary);">
          <p>Löydä mahdollisimman monta sanaa seitsemästä annetusta kirjaimesta.</p>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">Jokaisen sanan täytyy:</p>
            <ul class="space-y-1 list-none pl-0">
              <li>✦ Sisältää <span style="color: var(--color-accent);">oranssin keskikirjaimen</span></li>
              <li>✦ Olla vähintään 4 kirjainta pitkä</li>
              <li>✦ Koostua vain annetuista kirjaimista — samaa kirjainta voi käyttää useasti</li>
              <li>✦ Löytyä suomen kielen sanakirjasta (<a href="https://kaino.kotus.fi/sanat/nykysuomi/" target="_blank" rel="noopener" style="color: var(--color-accent); text-decoration: underline;">Kotus</a>)</li>
            </ul>
          </div>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">Pisteytys:</p>
            <ul class="space-y-1 list-none pl-0">
              <li>✦ 4-kirjaiminen sana = 1 piste</li>
              <li>✦ Pidempi sana = pisteitä sanan pituuden verran</li>
              <li>✦ Pangrammi (kaikki 7 kirjainta käytetty) = +7 lisäpistettä</li>
            </ul>
          </div>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">Yhdyssanat:</p>
            <p>Yhdysviivallisen sanan voi kirjoittaa myös ilman viivaa — esim. <span style="font-family: var(--font-mono);">palo-ovi</span> tai <span style="font-family: var(--font-mono);">paloovi</span>.</p>
          </div>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">Tasot:</p>
            <p>Pisteesi määrittävät tason. Huipulla odottaa <span style="color: var(--color-accent);">Täysi kenno</span>.</p>
          </div>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">💡 Avut:</p>
            <p>Neljä vihjettä, jotka jäävät auki koko pelin ajaksi.</p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
  <div class="max-w-sm mx-auto mb-5">
    <h1 class="text-2xl font-semibold" style="color: var(--color-text-primary);">Sanakenno<span v-if="puzzleNumber != null" style="color: var(--color-text-tertiary);"> — #{{ puzzleNumber + 1 }}</span></h1>
  </div>

  <!-- touch-action: manipulation prevents double-tap zoom on iOS Safari -->
  <div class="max-w-sm mx-auto" style="touch-action: manipulation;">
    <!-- Loading / error -->
    <div v-if="loading" class="text-center py-16" style="color: var(--color-text-secondary)">
      Ladataan...
    </div>
    <div v-else-if="fetchError" class="text-center py-16 text-red-400" role="alert">
      {{ fetchError }}
    </div>

    <template v-else-if="puzzle">
      <!-- Score & rank -->
      <div class="flex items-center gap-3 mb-2">
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

      <!-- Progress bar toward next rank -->
      <div class="w-full h-1 rounded-full mb-2" :style="{ background: 'var(--color-bg-secondary)' }">
        <div
          class="h-full rounded-full"
          :style="{ background: 'var(--color-accent)', width: progressToNextRank + '%', transition: 'width 0.5s ease' }"
        ></div>
      </div>

      <!-- Admin puzzle switcher -->
      <div v-if="isAdmin && totalPuzzles" class="flex items-center gap-2 mb-1 text-xs" style="color: var(--color-text-tertiary);">
        <span>Peli</span>
        <input
          type="number"
          min="1"
          :max="totalPuzzles"
          v-model.number="puzzleInputDisplay"
          @change="choosePuzzle(puzzleInputDisplay - 1)"
          class="rounded text-center"
          style="width: 3.5rem; background: var(--color-bg-secondary); color: var(--color-text-primary); border: 1px solid var(--color-border); padding: 1px 4px;"
          aria-label="Pelin numero"
        />
        <span>/{{ totalPuzzles }}</span>
        <button
          class="px-2 py-0.5 rounded"
          style="background: var(--color-bg-secondary); color: var(--color-text-secondary); border: 1px solid var(--color-border); cursor: pointer;"
          @click="randomPuzzle"
        >Satunnainen</button>
      </div>

      <!-- Center letter variation selector (admin) -->
      <div v-if="isAdmin && variations.length > 0" class="grid grid-cols-7 gap-1 mb-2">
        <button
          v-for="v in variations"
          :key="v.center"
          class="flex flex-col items-center py-1 px-0.5 rounded text-xs leading-tight"
          :style="{
            background: v.is_active ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
            color: v.is_active ? 'white' : 'var(--color-text-secondary)',
            border: '1px solid ' + (v.is_active ? 'var(--color-accent)' : 'var(--color-border)'),
            cursor: centerSaving ? 'wait' : 'pointer',
            opacity: centerSaving ? '0.6' : '1',
          }"
          :disabled="centerSaving"
          @click="!v.is_active && setCenter(v.center)"
        >
          <span class="font-semibold text-sm">{{ v.center.toUpperCase() }}</span>
          <span>{{ v.word_count }} w</span>
          <span>{{ v.max_score }} p</span>
          <span>{{ v.pangram_count }} pg</span>
        </button>
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
        class="text-center text-2xl mb-2 min-h-[2.5rem] font-light"
        :class="{ 'word-shake': wordShake }"
        style="font-family: var(--font-mono); letter-spacing: 0.15em;"
      >
        <template v-if="currentWord">
          <template v-for="(c, i) in currentWordChars" :key="i">
            <span :style="{ color: c.color }">{{ c.char.toUpperCase() }}</span>
          </template>
        </template>
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
          role="group"
          aria-label="Kirjainkenno"
          class="select-none"
          style="touch-action: none;"
        >
          <g
            v-for="(hex, i) in hexes"
            :key="i"
            role="button"
            :aria-label="`Lisää kirjain ${hex.letter.toUpperCase()}`"
            tabindex="-1"
            style="cursor: pointer;"
            @click="addLetter(hex.letter)"
            @pointerdown="pressedHexIndex = i"
            @pointerup="pressedHexIndex = null"
            @pointerleave="pressedHexIndex = null"
          >
            <polygon
              :points="hexPoints(hex.x, hex.y, 47)"
              :style="{
                fill:            hex.isCenter ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
                stroke:          hex.isCenter ? 'var(--color-accent)' : 'var(--color-border)',
                strokeWidth:     '1.5',
                transform:       pressedHexIndex === i ? 'scale(0.92)' : 'scale(1)',
                transformOrigin: `${hex.x}px ${hex.y}px`,
                transition:      'transform 0.08s ease',
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
      <div class="flex justify-center gap-3 mb-5">
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

      <!-- Avut (hints) + copy status row -->
      <div class="flex items-center justify-between mb-2">
        <button
          class="text-sm font-medium"
          style="color: var(--color-text-secondary); background: none; border: none; cursor: pointer; padding: 0;"
          @click="showHints = !showHints"
          :aria-expanded="showHints"
        >
          <span v-html="HINT_SVG.bulb" class="inline-block" style="vertical-align: -0.15em;" /> Avut {{ showHints ? '▲' : '▼' }}
        </button>
        <div class="flex items-center gap-2">
          <span
            v-if="shareCopied"
            class="text-xs"
            style="color: var(--color-text-secondary);"
          >Kopioitu leikepöydälle!</span>
          <button
            class="text-xs px-2 py-1 rounded"
            style="background: var(--color-bg-secondary); color: var(--color-text-secondary); border: 1px solid var(--color-border); cursor: pointer;"
            @click="copyStatus"
          >
            📋 Jaa tulos
          </button>
        </div>
      </div>

      <!-- Hints panel -->
      <div v-if="showHints" class="mb-4 p-3 rounded-lg text-sm space-y-3" style="background: var(--color-bg-secondary); border: 1px solid var(--color-border);">

        <!-- Hint 1: overview — remaining words, pangrams, length range -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <span style="color: var(--color-text-secondary);">Yleiskuva <span v-html="HINT_SVG.summary" class="inline-block align-middle ml-1" /></span>
            <button
              v-if="!hintsUnlocked.has('summary')"
              class="text-xs px-2 py-0.5 rounded"
              style="background: var(--color-accent); color: white; border: none; cursor: pointer;"
              @click="unlockHint('summary')"
            >Aktivoi</button>
          </div>
          <div v-if="hintsUnlocked.has('summary')" style="font-family: var(--font-mono);">
            <div v-if="unfoundLengths">
              <span style="color: var(--color-text-primary);">{{ allWords.length - foundWords.size }}/{{ allWords.length }} sanaa jäljellä </span><span style="color: var(--color-text-secondary);">({{ Math.round((foundWords.size / allWords.length) * 100) }}%) · {{ pangramStats.remaining }}/{{ pangramStats.total }} {{ pangramStats.total === 1 ? 'pangrammi' : 'pangrammia' }}</span>
            </div>
            <div v-if="unfoundLengths" style="color: var(--color-text-secondary);">
              {{ unfoundLengths.uniqueLengths }} eri {{ unfoundLengths.uniqueLengths === 1 ? 'sanapituus' : 'sanapituutta' }} · Pisin sana {{ unfoundLengths.longest }}&nbsp;merkkiä
            </div>
            <div v-else style="color: var(--color-accent);">kaikki löydetty</div>
          </div>
        </div>

        <!-- Hint 2: words left per first letter -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <span style="color: var(--color-text-secondary);">Alkukirjaimet <span v-html="HINT_SVG.letters" class="inline-block align-middle ml-1" /></span>
            <button
              v-if="!hintsUnlocked.has('letters')"
              class="text-xs px-2 py-0.5 rounded"
              style="background: var(--color-accent); color: white; border: none; cursor: pointer;"
              @click="unlockHint('letters')"
            >Aktivoi</button>
          </div>
          <div v-if="hintsUnlocked.has('letters')" class="flex flex-wrap gap-x-3 gap-y-0.5" style="font-family: var(--font-mono);">
            <span
              v-for="item in letterMap"
              :key="item.letter"
              class="text-sm"
              :style="{ color: item.remaining === 0 ? 'var(--color-text-tertiary)' : 'var(--color-text-primary)' }"
            >
              {{ item.letter.toUpperCase() }}&nbsp;{{ item.remaining }}
            </span>
          </div>
        </div>

        <!-- Hint 3: word count per length -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <span style="color: var(--color-text-secondary);">Pituusjakauma <span v-html="HINT_SVG.distribution" class="inline-block align-middle ml-1" /></span>
            <button
              v-if="!hintsUnlocked.has('distribution')"
              class="text-xs px-2 py-0.5 rounded"
              style="background: var(--color-accent); color: white; border: none; cursor: pointer;"
              @click="unlockHint('distribution')"
            >Aktivoi</button>
          </div>
          <div v-if="hintsUnlocked.has('distribution')" class="flex flex-wrap gap-x-4 gap-y-0.5" style="font-family: var(--font-mono);">
            <span
              v-for="item in lengthDistribution"
              :key="item.len"
              class="text-sm"
              :style="{ color: item.remaining === 0 ? 'var(--color-text-tertiary)' : 'var(--color-text-primary)' }"
            >{{ item.len }}: {{ item.remaining }}</span>
          </div>
        </div>

        <!-- Hint 4: remaining words per two-letter pair -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <span style="color: var(--color-text-secondary);">Alkuparit <span v-html="HINT_SVG.pairs" class="inline-block align-middle ml-1" /></span>
            <button
              v-if="!hintsUnlocked.has('pairs')"
              class="text-xs px-2 py-0.5 rounded"
              style="background: var(--color-accent); color: white; border: none; cursor: pointer;"
              @click="unlockHint('pairs')"
            >Aktivoi</button>
          </div>
          <div v-if="hintsUnlocked.has('pairs')" class="flex flex-wrap gap-x-3 gap-y-0.5" style="font-family: var(--font-mono);">
            <span
              v-for="item in pairMap"
              :key="item.pair"
              class="text-sm"
              :style="{ color: item.remaining === 0 ? 'var(--color-text-tertiary)' : 'var(--color-text-primary)' }"
            >
              {{ item.pair.toUpperCase() }}&nbsp;{{ item.remaining }}
            </span>
          </div>
        </div>

      </div>
      <div v-else class="mb-4"></div>

      <!-- All found celebration -->
      <div v-if="allFound" class="text-center py-4 rounded-lg mb-4" style="background: var(--color-bg-secondary); border: 1px solid var(--color-border);">
        <p class="text-2xl mb-1">🎉</p>
        <p class="font-semibold" style="color: var(--color-text-primary);">Kaikki {{ allWords.length }} sanaa löydetty!</p>
      </div>

      <!-- Found words -->
      <div v-if="foundWords.size > 0">
        <p class="text-sm mb-1" style="color: var(--color-text-secondary);">
          Löydetyt sanat ({{ foundWords.size }}):
        </p>
        <div class="flex flex-wrap gap-x-6 gap-y-2">
          <ul v-for="(col, ci) in wordColumns" :key="ci">
            <li
              v-for="word in col"
              :key="word"
              class="text-sm py-0.5"
              :style="{
                color: lastResubmittedWord === word ? 'var(--color-accent)' : 'var(--color-text-primary)',
                fontFamily: 'var(--font-mono)',
                transition: 'color 0.3s',
              }"
            >
              {{ word }}
            </li>
          </ul>
        </div>
      </div>
      <!-- Admin: remaining words -->
      <div v-if="isAdmin" class="mt-6">
        <button
          class="text-sm font-medium mb-2"
          style="color: var(--color-text-tertiary); background: none; border: none; cursor: pointer; padding: 0;"
          @click="showRemainingWords = !showRemainingWords"
          :aria-expanded="showRemainingWords"
        >
          Remaining words ({{ remainingWords.length }}) {{ showRemainingWords ? '▲' : '▼' }}
        </button>
        <div v-if="showRemainingWords" class="flex flex-wrap gap-x-6">
          <ul v-for="(col, ci) in remainingWordColumns" :key="ci">
            <li
              v-for="word in col"
              :key="word"
              class="flex items-center gap-1 py-0.5"
            >
              <span class="text-sm" style="color: var(--color-text-tertiary); font-family: var(--font-mono);">{{ word }}</span>
              <button
                @click="blockWord(word)"
                class="text-xs leading-none opacity-40 hover:opacity-100"
                style="color: #ef4444; background: none; border: none; cursor: pointer; padding: 0 2px;"
                aria-label="Remove word"
              >×</button>
            </li>
          </ul>
        </div>
      </div>

    </template>
  </div>
</template>

<style scoped>
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%       { transform: translateX(-8px); }
  40%       { transform: translateX(8px); }
  60%       { transform: translateX(-5px); }
  80%       { transform: translateX(5px); }
}
.word-shake {
  animation: shake 0.4s ease-in-out;
}
</style>
