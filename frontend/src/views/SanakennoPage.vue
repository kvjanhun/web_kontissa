<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import ThemeToggle from '../components/ThemeToggle.vue'

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
const showRanks = ref(false)
const showHints = ref(false)
const showRules = ref(false)
const hintsUnlocked = ref(new Set())  // 'summary' | 'letters' | 'distribution' | 'pairs'
const celebration = ref(null)  // null | 'alistyttava' | 'taysikenno'
let celebrationTimer = null

// --- Hint collapse state (session-only, no persistence) ---
const hintsCollapsed = ref(new Set())

const showAllFoundWords = ref(false)

const recentFoundWords = computed(() => [...foundWords.value].slice(-6))

function toggleHintCollapse(id) {
  const s = new Set(hintsCollapsed.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  hintsCollapsed.value = s
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
const wordHashSet = computed(() => new Set(puzzle.value?.word_hashes ?? []))
const allLetters = computed(() => new Set([center.value, ...outerLetters.value]))

async function hashWord(word) {
  const data = new TextEncoder().encode(word)
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}

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
  summary: '<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 512 512" fill="currentColor" stroke="none" aria-hidden="true"><path d="M332.998,291.918c52.2-71.895,45.941-173.338-18.834-238.123c-71.736-71.728-188.468-71.728-260.195,0c-71.746,71.745-71.746,188.458,0,260.204c64.775,64.775,166.218,71.034,238.104,18.844l14.222,14.203l40.916-40.916L332.998,291.918z M278.488,278.333c-52.144,52.134-136.699,52.144-188.852,0c-52.152-52.153-52.152-136.717,0-188.861c52.154-52.144,136.708-52.144,188.852,0C330.64,141.616,330.64,226.18,278.488,278.333z"/><path d="M109.303,119.216c-27.078,34.788-29.324,82.646-6.756,119.614c2.142,3.489,6.709,4.603,10.208,2.46c3.49-2.142,4.594-6.709,2.462-10.198v0.008c-19.387-31.7-17.45-72.962,5.782-102.771c2.526-3.228,1.946-7.898-1.292-10.405C116.48,115.399,111.811,115.979,109.303,119.216z"/><path d="M501.499,438.591L363.341,315.178l-47.98,47.98l123.403,138.168c12.548,16.234,35.144,13.848,55.447-6.456C514.505,474.576,517.743,451.138,501.499,438.591z"/></svg>',
  letters: '<span aria-hidden="true" style="font-weight:450;font-size:1.1em;line-height:1;">A</span>',
  distribution: '<svg xmlns="http://www.w3.org/2000/svg" width="1.15em" height="1em" viewBox="0 0 20 14" fill="currentColor" stroke="currentColor" aria-hidden="true"><rect x="0.5" y="0.5" width="19" height="13" rx="1" fill="none" stroke-width="1.3"/><line x1="4" y1="0.5" x2="4" y2="5" stroke-width="1"/><line x1="8" y1="0.5" x2="8" y2="7.5" stroke-width="1"/><line x1="12" y1="0.5" x2="12" y2="5" stroke-width="1"/><line x1="16" y1="0.5" x2="16" y2="7.5" stroke-width="1"/></svg>',
  pairs: '<span aria-hidden="true" style="font-weight:450;font-size:1.1em;line-height:1;">AB</span>',
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
  // Hide Täysi kenno from the visible list — it's a surprise reveal
  const visible = rank.value === 'Täysi kenno'
    ? RANKS
    : RANKS.filter(r => r.name !== 'Täysi kenno')
  return [...visible].reverse().map(r => ({
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

const allFound = computed(() => {
  if (!puzzle.value?.hint_data) return false
  return foundWords.value.size === puzzle.value.hint_data.word_count
})

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

// --- Hint computeds (using hint_data from API) ---

// Track found word stats for subtracting from hint_data totals
const foundByLetter = computed(() => {
  const map = {}
  for (const word of foundWords.value) {
    const l = word[0]
    map[l] = (map[l] || 0) + 1
  }
  return map
})

const foundByLength = computed(() => {
  const map = {}
  for (const word of foundWords.value) {
    const k = String(word.length)
    map[k] = (map[k] || 0) + 1
  }
  return map
})

const foundByPair = computed(() => {
  const map = {}
  for (const word of foundWords.value) {
    const pair = word.slice(0, 2)
    map[pair] = (map[pair] || 0) + 1
  }
  return map
})

// Hint 2: remaining words per starting letter
const letterMap = computed(() => {
  const hd = puzzle.value?.hint_data
  if (!hd) return []
  return Object.entries(hd.by_letter)
    .map(([letter, total]) => ({ letter, remaining: total - (foundByLetter.value[letter] || 0) }))
    .sort((a, b) => a.letter.localeCompare(b.letter))
})

// Hint 1 (summary): remaining word stats
const unfoundLengths = computed(() => {
  const hd = puzzle.value?.hint_data
  if (!hd) return null
  const remaining = hd.word_count - foundWords.value.size
  if (remaining === 0) return null
  let longest = 0
  const uniqueLengths = new Set()
  for (const [len, total] of Object.entries(hd.by_length)) {
    const found = foundByLength.value[len] || 0
    if (total - found > 0) {
      uniqueLengths.add(parseInt(len))
      if (parseInt(len) > longest) longest = parseInt(len)
    }
  }
  return { longest, uniqueLengths: uniqueLengths.size }
})

const pangramStats = computed(() => {
  const hd = puzzle.value?.hint_data
  if (!hd) return { total: 0, found: 0, remaining: 0 }
  const letterSet = new Set([center.value, ...outerLetters.value])
  const foundPangrams = [...foundWords.value].filter(w => [...letterSet].every(c => w.includes(c))).length
  return { total: hd.pangram_count, found: foundPangrams, remaining: hd.pangram_count - foundPangrams }
})

// Hint 3: word count per length (remaining)
const lengthDistribution = computed(() => {
  const hd = puzzle.value?.hint_data
  if (!hd) return []
  return Object.entries(hd.by_length)
    .map(([len, total]) => ({ len: parseInt(len), total, remaining: total - (foundByLength.value[len] || 0) }))
    .sort((a, b) => a.len - b.len)
})

// Hint 4: remaining words per two-letter pair
const pairMap = computed(() => {
  const hd = puzzle.value?.hint_data
  if (!hd) return []
  return Object.entries(hd.by_pair)
    .map(([pair, total]) => ({ pair, remaining: total - (foundByPair.value[pair] || 0) }))
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

// --- Theme-color meta (iOS Safari status bar) + html background ---
let _originalThemeColor = null
let _themeColorMeta = null
let _originalHtmlBg = null

function _setThemeColor() {
  const color = getComputedStyle(document.documentElement).getPropertyValue('--color-bg-primary').trim()
  _themeColorMeta = document.querySelector('meta[name="theme-color"]')
  if (!_themeColorMeta) {
    _themeColorMeta = document.createElement('meta')
    _themeColorMeta.name = 'theme-color'
    document.head.appendChild(_themeColorMeta)
  }
  _originalThemeColor = _themeColorMeta.content
  _themeColorMeta.content = color
  // Make html background match page bg so sides don't show --color-bg-page on wide screens
  _originalHtmlBg = document.documentElement.style.backgroundColor
  document.documentElement.style.backgroundColor = color
}

function _updateThemeColor() {
  if (!_themeColorMeta) return
  const color = getComputedStyle(document.documentElement).getPropertyValue('--color-bg-primary').trim()
  _themeColorMeta.content = color
  document.documentElement.style.backgroundColor = color
}

function _restoreThemeColor() {
  if (!_themeColorMeta) return
  if (_originalThemeColor != null) {
    _themeColorMeta.content = _originalThemeColor
  } else {
    _themeColorMeta.remove()
  }
  document.documentElement.style.backgroundColor = _originalHtmlBg
}

let _themeObserver = null

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

async function loadState() {
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
    // Validate saved words against current word hashes
    const validWords = []
    for (const w of (saved.foundWords || [])) {
      const h = await hashWord(w)
      if (wordHashSet.value.has(h)) validWords.push(w)
    }
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
    const url = overrideIndex != null ? `/api/kenno?puzzle=${overrideIndex}` : '/api/kenno'
    const res = await fetch(url)
    if (!res.ok) throw new Error('Verkkovirhe')
    const data = await res.json()
    puzzle.value = data
    outerLetters.value = [...data.letters]
    puzzleNumber.value = data.puzzle_number
    await loadState()
    if (startedAt.value === null) startedAt.value = Date.now()
  } catch {
    fetchError.value = 'Lataus epäonnistui.'
  } finally {
    loading.value = false
  }
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

  const max = puzzle.value?.max_score ?? 0
  const alistyttavaTarget = Math.ceil(0.7 * max)
  const isTaysiKenno = rank.value === 'Täysi kenno'
  const scoreDisplay = isTaysiKenno
    ? `${max}/${max}`
    : `${score.value}/${alistyttavaTarget}`

  const lines = [
    `Sanakenno — Peli ${(puzzleNumber.value ?? 0) + 1}`,
    rank.value,
    `${scoreDisplay} pistettä`,
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

async function submitWord() {
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

  const wordHash = await hashWord(word)
  if (!wordHashSet.value.has(wordHash)) {
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
    // Fire-and-forget achievement tracking
    fetch('/api/kenno/achievement', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        puzzle_number: puzzleNumber.value,
        rank: rankAfter,
        score: score.value,
        max_score: puzzle.value.max_score,
        words_found: foundWords.value.size,
        elapsed_ms: Math.round(getElapsedMs()),
      }),
    }).catch(() => {})

    if (rankAfter === 'Ällistyttävä') {
      celebration.value = 'alistyttava'
      if (celebrationTimer) clearTimeout(celebrationTimer)
      celebrationTimer = setTimeout(() => { celebration.value = null }, 5000)
    } else if (rankAfter === 'Täysi kenno') {
      celebration.value = 'taysikenno'
      if (celebrationTimer) clearTimeout(celebrationTimer)
      celebrationTimer = setTimeout(() => { celebration.value = null }, 8000)
    } else {
      showMessage('Uusi taso: ' + rankAfter + '!', 'special', 3000)
    }
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
  _swapFavicon(BEE_FAVICON)
  _setThemeColor()
  // Update theme-color when dark/light mode toggles (class change on <html>)
  _themeObserver = new MutationObserver(_updateThemeColor)
  _themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('blur', handleVisibilityChange)
  window.addEventListener('pagehide', handlePageHide)
  fetchPuzzle()
})

onUnmounted(() => {
  _restoreFavicon()
  _restoreThemeColor()
  if (_themeObserver) { _themeObserver.disconnect(); _themeObserver = null }
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('blur', handleVisibilityChange)
  window.removeEventListener('pagehide', handlePageHide)
  if (msgTimer) clearTimeout(msgTimer)
  if (resubTimer) clearTimeout(resubTimer)
  if (rejectTimer) clearTimeout(rejectTimer)
  if (shareCopiedTimer) clearTimeout(shareCopiedTimer)
  if (celebrationTimer) clearTimeout(celebrationTimer)
})
</script>

<template>
  <!-- Fixed title bar: full viewport width, position:fixed so Safari 26 samples its background-color
       for the liquid glass status bar. padding-top covers the safe-area-inset-top region. -->
  <div style="position: fixed; top: 0; left: 0; right: 0; z-index: 50; background-color: var(--color-bg-primary); padding-top: env(safe-area-inset-top);">
    <div class="max-w-sm mx-auto px-6 h-12 flex justify-between items-center">
      <router-link to="/" class="text-sm" style="color: var(--color-text-tertiary);">← erez.ac</router-link>
      <h1 class="text-lg font-semibold" style="color: var(--color-text-primary);">Sanakenno<span v-if="puzzleNumber != null" style="color: var(--color-text-tertiary);"> — #{{ puzzleNumber + 1 }}</span></h1>
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
            <p>Pisteesi määrittävät tason. Tavoittele tasoa <span style="color: var(--color-accent);">Ällistyttävä</span>!</p>
          </div>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">💡 Avut:</p>
            <p>Neljä vihjettä, jotka jäävät auki koko pelin ajaksi.</p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- touch-action: manipulation prevents double-tap zoom on iOS Safari -->
  <div class="max-w-sm mx-auto" style="touch-action: manipulation;">
    <!-- Spacer: natural position of sticky bar = stick position (env + 3rem from viewport top).
         main has p-6 = 1.5rem padding-top, so spacer = env(safe-area-inset-top) + 1.5rem. -->
    <div style="height: calc(env(safe-area-inset-top) + 1.5rem);" aria-hidden="true"></div>
    <!-- Loading / error -->
    <div v-if="loading" class="text-center py-16" style="color: var(--color-text-secondary)">
      Ladataan...
    </div>
    <div v-else-if="fetchError" class="text-center py-16 text-red-400" role="alert">
      {{ fetchError }}
    </div>

    <template v-else-if="puzzle">
      <!-- Sticky score / hints bar — stays visible when top nav scrolls away -->
      <div class="sticky-score-bar" style="position: sticky; top: calc(env(safe-area-inset-top) + 3rem); z-index: 10; background-color: var(--color-bg-primary); padding-top: 0.5rem; padding-bottom: 0.25rem;">
        <!-- Score + rank pill + share button -->
        <div class="flex items-center gap-2 mb-1">
          <span class="text-base font-medium" style="color: var(--color-text-primary)">
            Pisteet: {{ score }}
          </span>
          <button
            class="px-2 py-0.5 rounded-full text-xs font-medium"
            style="background: var(--color-accent); color: white; border: none; cursor: pointer;"
            @click="showRanks = !showRanks"
            :aria-expanded="showRanks"
            aria-label="Näytä tasorajat"
          >{{ rank }}</button>
          <div class="flex items-center gap-2 ml-auto">
            <span
              v-if="shareCopied"
              class="text-xs"
              style="color: var(--color-text-secondary);"
            >Kopioitu leikepöydälle!</span>
            <button
              class="text-xs px-2 py-1 rounded"
              style="background: var(--color-bg-secondary); color: var(--color-text-secondary); border: 1px solid var(--color-border); cursor: pointer;"
              @click="copyStatus"
            >Jaa tulos</button>
          </div>
        </div>

        <!-- Progress bar toward next rank -->
        <div class="w-full h-1 rounded-full mb-1" :style="{ background: 'var(--color-bg-secondary)' }">
          <div
            class="h-full rounded-full"
            :style="{ background: 'var(--color-accent)', width: progressToNextRank + '%', transition: 'width 0.5s ease' }"
          ></div>
        </div>
      </div>

      <!-- Rank thresholds (expandable, outside sticky) -->
      <div v-if="showRanks" class="mb-2 p-3 rounded-lg text-sm" style="background: var(--color-bg-secondary); border: 1px solid var(--color-border);">
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

      <!-- Avut (hints) -->
      <div class="mb-2">
        <button
          class="text-sm font-medium"
          style="color: var(--color-text-secondary); background: none; border: none; cursor: pointer; padding: 0;"
          @click="showHints = !showHints"
          :aria-expanded="showHints"
        >
          <span v-html="HINT_SVG.bulb" class="inline-block" style="vertical-align: -0.15em;" /> Avut {{ showHints ? '▲' : '▼' }}
        </button>
        <div v-if="showHints" class="mt-2 p-3 rounded-lg text-sm space-y-3" style="background: var(--color-bg-secondary); border: 1px solid var(--color-border);">

          <!-- Hint 1: overview -->
          <div>
            <div
              class="flex items-center justify-between mb-1"
              :style="hintsUnlocked.has('summary') ? 'cursor:pointer' : ''"
              @click="hintsUnlocked.has('summary') && toggleHintCollapse('summary')"
            >
              <span style="color: var(--color-text-secondary);">Yleiskuva <span v-html="HINT_SVG.summary" class="inline-block align-middle ml-1" /></span>
              <button v-if="!hintsUnlocked.has('summary')" class="text-xs px-2 py-0.5 rounded" style="background: var(--color-accent); color: white; border: none; cursor: pointer;" @click.stop="unlockHint('summary')">Aktivoi</button>
              <span v-else class="text-xs" style="color: var(--color-text-tertiary);">{{ hintsCollapsed.has('summary') ? '▼' : '▲' }}</span>
            </div>
            <div v-if="hintsUnlocked.has('summary') && !hintsCollapsed.has('summary')" style="font-family: var(--font-mono);">
              <div v-if="unfoundLengths">
                <span style="color: var(--color-text-primary);">{{ puzzle.hint_data.word_count - foundWords.size }}/{{ puzzle.hint_data.word_count }} sanaa jäljellä </span><span style="color: var(--color-text-secondary);">({{ Math.round((foundWords.size / puzzle.hint_data.word_count) * 100) }}%) · {{ pangramStats.remaining }}/{{ pangramStats.total }} {{ pangramStats.total === 1 ? 'pangrammi' : 'pangrammia' }}</span>
              </div>
              <div v-if="unfoundLengths" style="color: var(--color-text-secondary);">{{ unfoundLengths.uniqueLengths }} eri {{ unfoundLengths.uniqueLengths === 1 ? 'sanapituus' : 'sanapituutta' }} · Pisin sana {{ unfoundLengths.longest }}&nbsp;merkkiä</div>
              <div v-else style="color: var(--color-accent);">kaikki löydetty</div>
            </div>
          </div>

          <!-- Hint 2: words left per first letter -->
          <div>
            <div
              class="flex items-center justify-between mb-1"
              :style="hintsUnlocked.has('letters') ? 'cursor:pointer' : ''"
              @click="hintsUnlocked.has('letters') && toggleHintCollapse('letters')"
            >
              <span style="color: var(--color-text-secondary);">Alkukirjaimet <span v-html="HINT_SVG.letters" class="inline-block align-middle ml-1" /></span>
              <button v-if="!hintsUnlocked.has('letters')" class="text-xs px-2 py-0.5 rounded" style="background: var(--color-accent); color: white; border: none; cursor: pointer;" @click.stop="unlockHint('letters')">Aktivoi</button>
              <span v-else class="text-xs" style="color: var(--color-text-tertiary);">{{ hintsCollapsed.has('letters') ? '▼' : '▲' }}</span>
            </div>
            <div v-if="hintsUnlocked.has('letters') && !hintsCollapsed.has('letters')" class="flex flex-wrap gap-x-3 gap-y-0.5" style="font-family: var(--font-mono);">
              <span v-for="item in letterMap" :key="item.letter" class="text-sm" :style="{ color: item.remaining === 0 ? 'var(--color-text-tertiary)' : 'var(--color-text-primary)' }">{{ item.letter.toUpperCase() }}&nbsp;{{ item.remaining }}</span>
            </div>
          </div>

          <!-- Hint 3: word count per length -->
          <div>
            <div
              class="flex items-center justify-between mb-1"
              :style="hintsUnlocked.has('distribution') ? 'cursor:pointer' : ''"
              @click="hintsUnlocked.has('distribution') && toggleHintCollapse('distribution')"
            >
              <span style="color: var(--color-text-secondary);">Pituusjakauma <span v-html="HINT_SVG.distribution" class="inline-block align-middle ml-1" /></span>
              <button v-if="!hintsUnlocked.has('distribution')" class="text-xs px-2 py-0.5 rounded" style="background: var(--color-accent); color: white; border: none; cursor: pointer;" @click.stop="unlockHint('distribution')">Aktivoi</button>
              <span v-else class="text-xs" style="color: var(--color-text-tertiary);">{{ hintsCollapsed.has('distribution') ? '▼' : '▲' }}</span>
            </div>
            <div v-if="hintsUnlocked.has('distribution') && !hintsCollapsed.has('distribution')" class="flex flex-wrap gap-x-4 gap-y-0.5" style="font-family: var(--font-mono);">
              <span v-for="item in lengthDistribution" :key="item.len" class="text-sm" :style="{ color: item.remaining === 0 ? 'var(--color-text-tertiary)' : 'var(--color-text-primary)' }">{{ item.len }}: {{ item.remaining }}</span>
            </div>
          </div>

          <!-- Hint 4: remaining words per two-letter pair -->
          <div>
            <div
              class="flex items-center justify-between mb-1"
              :style="hintsUnlocked.has('pairs') ? 'cursor:pointer' : ''"
              @click="hintsUnlocked.has('pairs') && toggleHintCollapse('pairs')"
            >
              <span style="color: var(--color-text-secondary);">Alkuparit <span v-html="HINT_SVG.pairs" class="inline-block align-middle ml-1" /></span>
              <button v-if="!hintsUnlocked.has('pairs')" class="text-xs px-2 py-0.5 rounded" style="background: var(--color-accent); color: white; border: none; cursor: pointer;" @click.stop="unlockHint('pairs')">Aktivoi</button>
              <span v-else class="text-xs" style="color: var(--color-text-tertiary);">{{ hintsCollapsed.has('pairs') ? '▼' : '▲' }}</span>
            </div>
            <div v-if="hintsUnlocked.has('pairs') && !hintsCollapsed.has('pairs')" class="flex flex-wrap gap-x-3 gap-y-0.5" style="font-family: var(--font-mono);">
              <span v-for="item in pairMap" :key="item.pair" class="text-sm" :style="{ color: item.remaining === 0 ? 'var(--color-text-tertiary)' : 'var(--color-text-primary)' }">{{ item.pair.toUpperCase() }}&nbsp;{{ item.remaining }}</span>
            </div>
          </div>

        </div>
      </div>

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
        class="text-center text-sm font-medium mb-2 min-h-[1.25rem]"
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
      <div class="flex justify-center mb-3">
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
            @pointerdown="pressedHexIndex = i; addLetter(hex.letter)"
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
      <div class="flex justify-center gap-3 mb-3">
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

      <!-- All found celebration -->
      <div v-if="allFound" class="text-center py-3 rounded-lg mb-3" style="background: var(--color-bg-secondary); border: 1px solid var(--color-border);">
        <p class="text-2xl mb-1">🎉</p>
        <p class="font-semibold" style="color: var(--color-text-primary);">Kaikki {{ puzzle.hint_data.word_count }} sanaa löydetty!</p>
      </div>

      <!-- Found words -->
      <div v-if="foundWords.size > 0">
        <!-- header row with label + expand toggle -->
        <div class="flex items-center justify-between mb-1">
          <p class="text-sm" style="color: var(--color-text-secondary);">
            Löydetyt sanat ({{ foundWords.size }}):
          </p>
          <button
            v-if="foundWords.size > 6 || showAllFoundWords"
            @click="showAllFoundWords = !showAllFoundWords"
            class="text-xs"
            style="color: var(--color-text-tertiary); background: none; border: none; cursor: pointer; padding: 0;"
          >
            {{ showAllFoundWords ? 'Vähemmän ▲' : 'Kaikki ▼' }}
          </button>
        </div>

        <!-- compact: last 6 words, single row, overflow-clipped -->
        <div
          v-if="!showAllFoundWords"
          class="flex gap-x-4"
          :style="{
            overflow: 'hidden',
            flexWrap: 'nowrap',
            cursor: foundWords.size > 6 ? 'pointer' : 'default',
          }"
          @click="foundWords.size > 6 && (showAllFoundWords = true)"
        >
          <span
            v-for="word in recentFoundWords"
            :key="word"
            class="text-sm"
            :style="{
              color: lastResubmittedWord === word ? 'var(--color-accent)' : 'var(--color-text-primary)',
              fontFamily: 'var(--font-mono)',
              transition: 'color 0.3s',
            }"
          >{{ word }}</span>
        </div>

        <!-- expanded: full alphabetical-size multi-column (existing layout) -->
        <div v-else class="flex flex-wrap gap-x-6 gap-y-2">
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
            >{{ word }}</li>
          </ul>
        </div>
      </div>

    </template>
  </div>

  <!-- Celebration overlay -->
  <Teleport to="body">
    <div
      v-if="celebration"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      style="background: rgba(0,0,0,0.5);"
      @click="celebration = null"
    >
      <div
        class="w-full max-w-sm rounded-xl p-8 text-center"
        :class="celebration === 'taysikenno' ? 'celebration-card-intense' : 'celebration-card'"
        style="background: var(--color-bg-primary);"
        @click.stop
      >
        <p class="text-4xl mb-3" v-if="celebration === 'taysikenno'">🏆</p>
        <p class="text-3xl mb-3" v-else>🎉</p>
        <h2
          class="font-bold mb-2"
          :class="celebration === 'taysikenno' ? 'text-2xl' : 'text-xl'"
          style="color: var(--color-accent);"
        >
          {{ celebration === 'taysikenno' ? 'Täysi kenno!' : 'Ällistyttävä!' }}
        </h2>
        <p class="text-sm mb-4" style="color: var(--color-text-secondary);">
          <template v-if="celebration === 'taysikenno'">
            Täydellinen tulos! Löysit kaikki sanat.
          </template>
          <template v-else>
            Huikea suoritus! Olet saavuttanut huipputason.
          </template>
        </p>
        <p class="text-lg font-semibold" style="color: var(--color-text-primary);">
          <template v-if="celebration === 'taysikenno'">
            {{ puzzle?.max_score }} / {{ puzzle?.max_score }} pistettä
          </template>
          <template v-else>
            {{ score }} / {{ Math.ceil(0.7 * (puzzle?.max_score ?? 0)) }} pistettä
          </template>
        </p>
        <div class="flex justify-center gap-2 mt-4">
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium"
            style="background: var(--color-bg-secondary); color: var(--color-text-secondary); border: 1px solid var(--color-border); cursor: pointer;"
            @click="copyStatus(); celebration = null"
          >
            📋 Jaa tulos
          </button>
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium"
            style="background: var(--color-accent); color: white; border: none; cursor: pointer;"
            @click="celebration = null"
          >
            {{ celebration === 'taysikenno' ? 'OK' : 'Jatka pelaamista' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
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

@keyframes glow {
  0%, 100% { box-shadow: 0 0 8px rgba(255, 100, 62, 0.3); }
  50%      { box-shadow: 0 0 20px rgba(255, 100, 62, 0.6); }
}
.celebration-card {
  border: 2px solid var(--color-accent);
  animation: glow 2s ease-in-out infinite;
}

@keyframes glow-intense {
  0%, 100% { box-shadow: 0 0 12px rgba(255, 100, 62, 0.4), 0 0 24px rgba(255, 180, 60, 0.2); }
  50%      { box-shadow: 0 0 28px rgba(255, 100, 62, 0.7), 0 0 48px rgba(255, 180, 60, 0.4); }
}
.celebration-card-intense {
  border: 3px solid transparent;
  background-clip: padding-box;
  border-image: linear-gradient(135deg, var(--color-accent), #ffb43c, var(--color-accent)) 1;
  animation: glow-intense 2s ease-in-out infinite;
}
</style>
