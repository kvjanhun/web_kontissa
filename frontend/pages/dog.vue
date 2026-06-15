<script setup>
definePageMeta({
  layout: 'standalone',
})

useHead({
  title: 'Näyttelytulokset | erez.ac',
  meta: [
    { name: 'description', content: 'Selaa koiranäyttelyiden tuloksia. Hae rodun tai näyttelyn mukaan.' },
    { property: 'og:title', content: 'Näyttelytulokset | erez.ac' },
    { property: 'og:description', content: 'Selaa koiranäyttelyiden tuloksia.' },
    { property: 'og:url', content: 'https://erez.ac/dog' },
  ],
})

const route = useRoute()
const router = useRouter()

// ─── View state ──────────────────────────────────────────────
// 'list' | 'detail' | 'results'
const currentView = ref('list')

// ─── Data refs ───────────────────────────────────────────────
const shows = ref([])
const showsLoading = ref(true)
const showsError = ref('')
const indexStats = ref(null)

const selectedShow = ref(null)
const showDetail = ref(null)
const detailLoading = ref(false)
const detailError = ref('')

const selectedBreed = ref(null)
const breedResults = ref(null)
const resultsLoading = ref(false)
const resultsError = ref('')

// ─── Filters ─────────────────────────────────────────────────
const filterText = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
const searchError = ref('')
const showResultsOnly = ref(false)

// Breed list search query (within show detail view)
const breedSearchQuery = ref('')

// Breed results filters (within results view)
const dogSearchQuery = ref('')
const dogGradeFilter = ref('')
const dogClassFilter = ref('')
const dogAwardFilter = ref('')

// ─── Show-wide all-dogs results state (Show detail view) ─────
const showDetailTab = ref('breeds') // 'breeds' | 'dogs'
const allDogsLoading = ref(false)
const allDogsLoaded = ref(false)
const allDogsError = ref('')
const allDogsResults = ref([])
const allDogsProgress = ref(null)

function onSelectDogsTab() {
  showDetailTab.value = 'dogs'
  loadAllShowResults()
}

async function loadAllShowResults(options = {}) {
  const { poll = false } = options
  const showId = selectedShow.value?.id
  if (!showId) return
  if (allDogsLoaded.value || (allDogsLoading.value && !poll)) return
  clearAllDogsPoll()
  allDogsLoading.value = true
  allDogsError.value = ''
  let keepLoading = false
  try {
    const data = await $fetch(`/api/dog/shows/${showId}/all-results`)
    if (!selectedShow.value?.id || !sameId(selectedShow.value.id, showId)) return
    if (data.status === 'warming') {
      allDogsProgress.value = data.progress || null
      scheduleAllDogsPoll(data.retry_after)
      keepLoading = true
      return
    }
    allDogsResults.value = data.results || []
    allDogsProgress.value = data.cache || null
    allDogsLoaded.value = true
  } catch (e) {
    allDogsError.value = 'Tulosten hakeminen epäonnistui.'
  } finally {
    if (!keepLoading) {
      allDogsLoading.value = false
    }
  }
}

const allDogsProgressPercent = computed(() => {
  const percent = allDogsProgress.value?.percent
  return typeof percent === 'number' ? Math.max(0, Math.min(100, percent)) : null
})

const allDogsProgressText = computed(() => {
  const progress = allDogsProgress.value
  if (!progress) return 'Tarkistetaan välimuistia...'
  const fetched = progress.fetched_breeds ?? 0
  const total = progress.total_breeds
  const dogs = progress.total_dogs ?? 0
  const state = progress.state === 'running' ? 'Haetaan tuloksia' : 'Tulokset jonossa'
  if (total) {
    return `${state}: ${fetched}/${total} rotua, ${dogs} koiraa välimuistissa.`
  }
  return `${state}. Taustaprosessi hakee tiedot rauhallisesti.`
})

function normalizeGrade(grade) {
  return (grade || '').toLowerCase().trim()
}

function gradeMatchesFilter(dogGrade, filter) {
  const grade = normalizeGrade(dogGrade)
  if (!filter) return true
  if (filter === 'hyl') return grade === 'hyl' || grade === 'hylätty'
  if (filter === 'eva') return grade === 'eva' || grade === 'ei voida arvostella'
  if (filter === 'poissa') return grade === 'poissa'
  return grade === filter
}


const filteredAllDogs = computed(() => {
  if (!allDogsLoaded.value) return []
  let res = allDogsResults.value
  
  // Apply search text (dog name, catalog number, breed name, class)
  const q = dogSearchQuery.value.toLowerCase().trim()
  if (q) {
    res = res.filter(d => 
      (d.name || '').toLowerCase().includes(q) ||
      String(d.number || '').includes(q) ||
      (d.breedName || '').toLowerCase().includes(q) ||
      (d.class_name || '').toLowerCase().includes(q)
    )
  }
  
  // Apply grade filter
  const grade = dogGradeFilter.value.toLowerCase().trim()
  if (grade) {
    res = res.filter(d => gradeMatchesFilter(d.grade, grade))
  }
  
  // Apply class filter
  const cls = dogClassFilter.value.toLowerCase().trim()
  if (cls) {
    res = res.filter(d => (d.class_name || '').toLowerCase() === cls)
  }
  
  // Apply award filter
  const award = dogAwardFilter.value.toLowerCase().trim()
  if (award) {
    res = res.filter(d => (d.awards || '').toLowerCase().includes(award))
  }
  
  return res
})

const allDogsGroupedByBreed = computed(() => {
  const list = filteredAllDogs.value
  const groups = {}
  for (const d of list) {
    const bName = d.breedName
    if (!groups[bName]) {
      groups[bName] = {
        breedName: bName,
        breedObj: d.breedObj,
        dogs: []
      }
    }
    groups[bName].dogs.push(d)
  }
  return Object.values(groups)
})

const availableShowClasses = computed(() => {
  if (!allDogsResults.value) return []
  const classes = allDogsResults.value.map(r => r.class_name).filter(Boolean)
  return [...new Set(classes)].sort()
})

const availableShowAwards = computed(() => {
  if (!allDogsResults.value) return []
  const awardsSet = new Set()
  allDogsResults.value.forEach(r => {
    if (r.awards) {
      r.awards.split(',').forEach(a => {
        const trimmed = a.trim()
        if (trimmed) awardsSet.add(trimmed)
      })
    }
  })
  return [...awardsSet].sort()
})

// ─── Collapsible months ──────────────────────────────────────
const collapsedMonths = ref(new Set())

// ─── Expanded critiques ──────────────────────────────────────
const expandedCritiques = ref(new Set())

// ─── Debounce timer ──────────────────────────────────────────
let searchTimer = null
let searchRequestId = 0
let indexPollTimer = null
let allDogsPollTimer = null
let routeSyncToken = 0
let pendingLinkScrollToTop = false

function clearAllDogsPoll() {
  if (allDogsPollTimer) {
    clearTimeout(allDogsPollTimer)
    allDogsPollTimer = null
  }
}

function scheduleAllDogsPoll(retryAfterSeconds) {
  clearAllDogsPoll()
  const delay = Math.max(5, Number(retryAfterSeconds) || 8)
  allDogsPollTimer = setTimeout(() => {
    allDogsPollTimer = null
    loadAllShowResults({ poll: true })
  }, delay * 1000)
}

function firstQueryValue(value) {
  return Array.isArray(value) ? value[0] : value
}

function buildDogQuery(query) {
  const clean = {}
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') clean[key] = String(value)
  }
  return clean
}

function scrollDogPageToTop() {
  if (!import.meta.client || !pendingLinkScrollToTop) return
  pendingLinkScrollToTop = false
  nextTick(() => {
    requestAnimationFrame(() => {
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
    })
  })
}

function pushDogQuery(query, options = {}) {
  const shouldScrollToTop = Boolean(options.scrollToTop)
  if (shouldScrollToTop) pendingLinkScrollToTop = true
  return router.push({ path: '/dog', query: buildDogQuery(query) })
    .then((failure) => {
      if (failure && shouldScrollToTop) scrollDogPageToTop()
      return failure
    })
    .catch(() => {
      if (shouldScrollToTop) pendingLinkScrollToTop = false
    })
}

function sameId(left, right) {
  return String(left) === String(right)
}

function isNumericString(value) {
  return /^\d+$/.test(String(value))
}

function getRouteSelection() {
  return {
    showId: firstQueryValue(route.query.show),
    groupId: firstQueryValue(route.query.group),
    breedId: firstQueryValue(route.query.breed),
  }
}

function parseShowDate(dateStr) {
  if (!dateStr) return null
  const parts = dateStr.split('.')
  if (parts.length !== 3) return null
  const day = parseInt(parts[0], 10)
  const month = parseInt(parts[1], 10) - 1
  const year = parseInt(parts[2], 10)
  return new Date(year, month, day)
}

function isThisWeekLeft(showDate) {
  if (!showDate) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const currentDayOfWeek = today.getDay()
  const daysToSunday = currentDayOfWeek === 0 ? 0 : 7 - currentDayOfWeek
  const sunday = new Date(today)
  sunday.setDate(today.getDate() + daysToSunday)
  sunday.setHours(23, 59, 59, 999)
  return showDate >= today && showDate <= sunday
}

function getCurrentMonthLabel() {
  const FINNISH_MONTHS = [
    "tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu",
    "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"
  ]
  const now = new Date()
  return `${FINNISH_MONTHS[now.getMonth()]} ${now.getFullYear()}`
}

function shouldCollapseMonth(monthLabel) {
  if (!monthLabel) return false
  const m = monthLabel.toLowerCase().trim()
  if (m === 'tänään' || m === 'tällä viikolla') return false
  
  const currentMonthLabel = getCurrentMonthLabel().toLowerCase().trim()
  if (m === currentMonthLabel) return false
  
  return true
}

function resetDogSelection() {
  clearAllDogsPoll()
  currentView.value = 'list'
  selectedShow.value = null
  showDetail.value = null
  selectedBreed.value = null
  breedResults.value = null
  detailLoading.value = false
  detailError.value = ''
  resultsLoading.value = false
  resultsError.value = ''
  expandedCritiques.value = new Set()
  breedSearchQuery.value = ''
  dogSearchQuery.value = ''
  dogGradeFilter.value = ''
  dogClassFilter.value = ''
  dogAwardFilter.value = ''
  
  showDetailTab.value = 'breeds'
  allDogsLoading.value = false
  allDogsLoaded.value = false
  allDogsError.value = ''
  allDogsResults.value = []
  allDogsProgress.value = null
}

function formatTimestamp(value) {
  if (!value) return ''
  const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('fi-FI', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

function formatStatNumber(value) {
  if (typeof value !== 'number') return ''
  return new Intl.NumberFormat('fi-FI').format(value)
}

function hasShowStats(show) {
  return showStatItems(show).length > 0
}

function showStatItems(show) {
  const stats = show?.stats || {}
  const items = []
  if (stats.is_live) {
    items.push({
      key: 'live',
      label: 'Käynnissä',
      live: true,
    })
  }
  if (typeof stats.breed_count === 'number') {
    items.push({
      key: 'breeds',
      label: `${formatStatNumber(stats.breed_count)} rotua`,
    })
  }
  if (typeof stats.entry_count === 'number') {
    if (stats.is_live && typeof stats.result_count === 'number') {
      items.push({
        key: 'entries',
        label: `${formatStatNumber(stats.result_count)}/${formatStatNumber(stats.entry_count)} tulosta`,
        title: `${formatStatNumber(stats.result_count)}/${formatStatNumber(stats.entry_count)} arvosteltua ilmoittautuneesta`,
      })
      return items
    }
    items.push({
      key: 'entries',
      label: `${formatStatNumber(stats.entry_count)} koiraa`,
      title: `${formatStatNumber(stats.entry_count)} ilmoittautunutta`,
    })
  }
  return items
}

function showStatsLabel(show) {
  const stats = show?.stats || {}
  const parts = []
  if (stats.is_live) {
    parts.push('käynnissä')
  }
  if (typeof stats.breed_count === 'number') {
    parts.push(`${formatStatNumber(stats.breed_count)} rotua`)
  }
  if (typeof stats.entry_count === 'number') {
    if (stats.is_live && typeof stats.result_count === 'number') {
      parts.push(`${formatStatNumber(stats.result_count)}/${formatStatNumber(stats.entry_count)} tulosta`)
    } else {
      parts.push(`${formatStatNumber(stats.entry_count)} ilmoittautunutta`)
    }
  }
  return parts.join(', ')
}

function sourceForShow(show) {
  return show?.source_url || (show?.id ? `https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=${show.id}` : '')
}

async function refreshIndexStats() {
  try {
    const data = await $fetch('/api/dog/shows')
    shows.value = data.shows || shows.value
    indexStats.value = data.index || indexStats.value
    if (!showListShouldPoll.value && indexPollTimer) {
      clearInterval(indexPollTimer)
      indexPollTimer = null
    }
  } catch {
    // Keep existing page data; this is only a background freshness check.
  }
}

function startIndexPolling() {
  if (indexPollTimer || !showListShouldPoll.value) return
  indexPollTimer = setInterval(refreshIndexStats, 15000)
}

// ─── Fetch shows ─────────────────────────────────────────────
async function fetchShows() {
  showsLoading.value = true
  showsError.value = ''
  try {
    const data = await $fetch('/api/dog/shows')
    shows.value = data.shows || []
    indexStats.value = data.index || null

    // Default collapse other months (except current, Tänään, Tällä viikolla)
    const monthsToCollapse = new Set()
    for (const show of shows.value) {
      if (show.month && shouldCollapseMonth(show.month)) {
        monthsToCollapse.add(show.month)
      }
    }
    collapsedMonths.value = monthsToCollapse

    const { showId } = getRouteSelection()
    if (showId) {
      const activeShow = shows.value.find(show => sameId(show.id, showId))
      if (activeShow && sameId(selectedShow.value?.id, showId)) {
        selectedShow.value = activeShow
      }
    }
  } catch (e) {
    showsError.value = 'Näyttelyiden lataaminen epäonnistui.'
  } finally {
    showsLoading.value = false
  }
}

// ─── Fetch show detail ───────────────────────────────────────
async function fetchShowDetail(show, options = {}) {
  if (!show) return
  const { updateRoute = false, syncToken = null } = options
  if (syncToken !== null && syncToken !== routeSyncToken) return
  selectedShow.value = show
  currentView.value = 'detail'
  scrollDogPageToTop()
  detailLoading.value = true
  detailError.value = ''
  showDetail.value = null
  selectedBreed.value = null
  breedResults.value = null
  
  showDetailTab.value = 'breeds'
  clearAllDogsPoll()
  allDogsLoading.value = false
  allDogsLoaded.value = false
  allDogsError.value = ''
  allDogsResults.value = []
  allDogsProgress.value = null
  
  try {
    const data = await $fetch(`/api/dog/shows/${show.id}`)
    if (syncToken !== null && syncToken !== routeSyncToken) return
    showDetail.value = data
  } catch (e) {
    if (syncToken !== null && syncToken !== routeSyncToken) return
    detailError.value = 'Näyttelyn tietojen lataaminen epäonnistui.'
  } finally {
    if (syncToken === null || syncToken === routeSyncToken) {
      detailLoading.value = false
    }
  }
  if (updateRoute) pushDogQuery({ show: show.id })
}

// ─── Fetch breed results ─────────────────────────────────────
async function fetchBreedResults(breed, options = {}) {
  if (!breed.has_results) return
  const { updateRoute = false, syncToken = null } = options
  if (syncToken !== null && syncToken !== routeSyncToken) return
  selectedBreed.value = breed
  currentView.value = 'results'
  scrollDogPageToTop()
  resultsLoading.value = true
  resultsError.value = ''
  breedResults.value = null
  expandedCritiques.value = new Set()
  try {
    const params = new URLSearchParams()
    if (breed.group) params.set('group', breed.group)
    if (breed.breed_id) params.set('breed', breed.breed_id)
    const url = `/api/dog/shows/${selectedShow.value.id}/results?${params}`
    const data = await $fetch(url)
    if (syncToken !== null && syncToken !== routeSyncToken) return
    breedResults.value = data
  } catch (e) {
    if (syncToken !== null && syncToken !== routeSyncToken) return
    resultsError.value = 'Tulosten lataaminen epäonnistui.'
  } finally {
    if (syncToken === null || syncToken === routeSyncToken) {
      resultsLoading.value = false
    }
  }
  if (updateRoute) {
    pushDogQuery({
      show: selectedShow.value.id,
      group: breed.group,
      breed: breed.breed_id,
    })
  }
}

// ─── Search breeds ───────────────────────────────────────────
function onSearchInput() {
  clearTimeout(searchTimer)
  const q = filterText.value.trim()
  searchRequestId += 1
  const requestId = searchRequestId
  if (q.length < 2) {
    searchResults.value = []
    searchLoading.value = false
    searchError.value = ''
    return
  }
  searchLoading.value = true
  searchError.value = ''
  searchTimer = setTimeout(async () => {
    try {
      const data = await $fetch(`/api/dog/search?q=${encodeURIComponent(q)}`)
      if (requestId !== searchRequestId) return
      searchResults.value = data.results || []
      indexStats.value = data.index || indexStats.value
    } catch (e) {
      if (requestId !== searchRequestId) return
      searchError.value = 'Haku epäonnistui.'
    } finally {
      if (requestId !== searchRequestId) return
      searchLoading.value = false
    }
  }, 300)
}

async function onSelectSearchResult(res) {
  if (!res?.show?.id) return
  if (res.breed && res.breed.has_results) {
    return pushDogQuery({
      show: res.show.id,
      group: res.breed.group,
      breed: res.breed.breed_id,
    }, { scrollToTop: true })
  }
  return pushDogQuery({ show: res.show.id }, { scrollToTop: true })
}

// ─── Navigation ──────────────────────────────────────────────
function goToList() {
  return pushDogQuery({}, { scrollToTop: true })
}

function goToDetail() {
  if (selectedShow.value) {
    return pushDogQuery({ show: selectedShow.value.id }, { scrollToTop: true })
  }
}

function openShow(show) {
  if (!show?.id) return
  pushDogQuery({ show: show.id }, { scrollToTop: true })
}

function openBreed(breed) {
  if (!breed?.has_results || !selectedShow.value?.id) return
  pushDogQuery({
    show: selectedShow.value.id,
    group: breed.group,
    breed: breed.breed_id,
  }, { scrollToTop: true })
}

// ─── Toggle helpers ──────────────────────────────────────────
function toggleMonth(month) {
  const s = new Set(collapsedMonths.value)
  if (s.has(month)) s.delete(month)
  else s.add(month)
  collapsedMonths.value = s
}

function toggleCritique(idx) {
  const s = new Set(expandedCritiques.value)
  if (s.has(idx)) s.delete(idx)
  else s.add(idx)
  expandedCritiques.value = s
}

// ─── Computed: grouped shows ─────────────────────────────────
const filteredShows = computed(() => {
  const q = filterText.value.toLowerCase().trim()
  if (!q) return shows.value
  return shows.value.filter(s =>
    s.name.toLowerCase().includes(q) || s.date?.toLowerCase().includes(q)
  )
})

const indexedSearchActive = computed(() => filterText.value.trim().length >= 2)

const groupedShows = computed(() => {
  const groups = {}
  for (const show of filteredShows.value) {
    const month = show.month || 'Muu'
    if (!groups[month]) groups[month] = []
    groups[month].push(show)
  }
  return groups
})

const thisWeekShows = computed(() => {
  return shows.value.filter(show => {
    const showDate = parseShowDate(show.date)
    return isThisWeekLeft(showDate)
  })
})

const filteredBreeds = computed(() => {
  let breeds = showDetail.value?.breeds || []
  if (showResultsOnly.value) {
    breeds = breeds.filter(b => b.has_results)
  }
  const q = breedSearchQuery.value.toLowerCase().trim()
  if (!q) return breeds
  return breeds.filter(b =>
    b.name.toLowerCase().includes(q) ||
    (b.judge && b.judge.toLowerCase().includes(q))
  )
})

const selectedShowSourceUrl = computed(() => (
  showDetail.value?.source_url || sourceForShow(selectedShow.value)
))

const selectedBreedSourceUrl = computed(() => (
  breedResults.value?.source_url || selectedBreed.value?.source_url || ''
))

const indexWarming = computed(() => (
  indexStats.value?.total_show_count
  && indexStats.value.indexed_show_count < indexStats.value.total_show_count
))

const liveShowsPresent = computed(() => (
  shows.value.some(show => show?.stats?.is_live)
))

const showListShouldPoll = computed(() => (
  Boolean(indexWarming.value || liveShowsPresent.value)
))

const routeSelectionKey = computed(() => [
  firstQueryValue(route.query.show) || '',
  firstQueryValue(route.query.group) || '',
  firstQueryValue(route.query.breed) || '',
].join('|'))

// ─── Computed: filtered breed results & classes/awards ───────
const filteredDogResults = computed(() => {
  if (!breedResults.value?.results) return []
  
  const search = dogSearchQuery.value.toLowerCase().trim()
  const grade = dogGradeFilter.value.toLowerCase().trim()
  const className = dogClassFilter.value.trim()
  const award = dogAwardFilter.value.trim()
  
  return breedResults.value.results.filter(dog => {
    if (search) {
      const nameMatch = dog.name?.toLowerCase().includes(search)
      const numMatch = String(dog.number).includes(search)
      if (!nameMatch && !numMatch) return false
    }
    
    if (grade) {
      if (!gradeMatchesFilter(dog.grade, grade)) return false
    }
    
    if (className) {
      if (dog.class_name !== className) return false
    }
    
    if (award) {
      if (!dog.awards) return false
      const hasAward = dog.awards.split(',').map(s => s.trim().toLowerCase()).includes(award.toLowerCase())
      if (!hasAward) return false
    }
    
    return true
  })
})

const availableClasses = computed(() => {
  if (!breedResults.value?.results) return []
  const classes = breedResults.value.results.map(r => r.class_name).filter(Boolean)
  return [...new Set(classes)].sort()
})

const availableAwards = computed(() => {
  if (!breedResults.value?.results) return []
  const awardsSet = new Set()
  breedResults.value.results.forEach(r => {
    if (r.awards) {
      r.awards.split(',').forEach(a => {
        const trimmed = a.trim()
        if (trimmed) awardsSet.add(trimmed)
      })
    }
  })
  return [...awardsSet].sort()
})

const resultsByGenderAndClass = computed(() => {
  const groups = {}
  for (const r of filteredDogResults.value) {
    const gender = r.gender || 'Muu'
    const className = r.class_name || 'Luokka'
    if (!groups[gender]) groups[gender] = {}
    if (!groups[gender][className]) groups[gender][className] = []
    groups[gender][className].push(r)
  }
  return groups
})

// ─── Grade color classes ─────────────────────────────────────
function gradeClasses(grade) {
  if (!grade) return 'dog-badge-default'
  const g = grade.toLowerCase().trim()
  if (g === 'eri' || g === 'erinomainen') return 'dog-badge-gold'
  if (g === 'eh' || g === 'erittäin hyvä') return 'dog-badge-silver'
  if (g === 'h' || g === 'hyvä') return 'dog-badge-bronze'
  if (g === 'kp') return 'dog-badge-info'
  if (g === 'poissa' || g === 'hyl' || g === 'hylätty' || g === 'eva' || g === 'ei voida arvostella') return 'dog-badge-muted'
  return 'dog-badge-default'
}

function gradeBorderClass(grade) {
  if (!grade) return 'dog-border-default'
  const g = grade.toLowerCase().trim()
  if (g === 'eri' || g === 'erinomainen') return 'dog-border-gold'
  if (g === 'eh' || g === 'erittäin hyvä') return 'dog-border-silver'
  if (g === 'h' || g === 'hyvä') return 'dog-border-bronze'
  if (g === 'kp') return 'dog-border-info'
  if (g === 'poissa' || g === 'hyl' || g === 'hylätty' || g === 'eva' || g === 'ei voida arvostella') return 'dog-border-muted'
  return 'dog-border-default'
}

async function syncRouteState() {
  const syncToken = ++routeSyncToken
  const { showId, groupId, breedId } = getRouteSelection()

  if (!showId || !isNumericString(showId)) {
    resetDogSelection()
    scrollDogPageToTop()
    return
  }

  const show = shows.value.find(item => sameId(item.id, showId)) || {
    id: Number(showId),
    name: `Näyttely ${showId}`,
    source_url: sourceForShow({ id: showId }),
  }

  const showMatches = showDetail.value && sameId(showDetail.value.id, showId)
  if (!showMatches) {
    await fetchShowDetail(show, { syncToken })
    if (syncToken !== routeSyncToken) return
    scrollDogPageToTop()
  } else {
    selectedShow.value = show
    currentView.value = 'detail'
    detailLoading.value = false
    detailError.value = ''
    scrollDogPageToTop()
  }

  if (!groupId || !breedId) {
    currentView.value = 'detail'
    selectedBreed.value = null
    breedResults.value = null
    resultsLoading.value = false
    resultsError.value = ''
    expandedCritiques.value = new Set()
    scrollDogPageToTop()
    return
  }

  if (!isNumericString(groupId) || !isNumericString(breedId) || !showDetail.value) {
    currentView.value = 'detail'
    selectedBreed.value = null
    breedResults.value = null
    resultsLoading.value = false
    resultsError.value = ''
    expandedCritiques.value = new Set()
    scrollDogPageToTop()
    return
  }

  const breed = showDetail.value?.breeds?.find(item => (
    sameId(item.group, groupId) && sameId(item.breed_id, breedId)
  ))
  if (!breed) {
    currentView.value = 'detail'
    selectedBreed.value = null
    breedResults.value = null
    resultsLoading.value = false
    resultsError.value = ''
    expandedCritiques.value = new Set()
    scrollDogPageToTop()
    return
  }

  const resultsMatch = selectedBreed.value
    && sameId(selectedBreed.value.group, groupId)
    && sameId(selectedBreed.value.breed_id, breedId)
    && sameId(selectedShow.value?.id, showId)
    && breedResults.value

  if (!resultsMatch) {
    await fetchBreedResults(breed, { syncToken })
    if (syncToken !== routeSyncToken) return
    scrollDogPageToTop()
  } else {
    currentView.value = 'results'
    resultsLoading.value = false
    resultsError.value = ''
    scrollDogPageToTop()
  }
}

// ─── Init ────────────────────────────────────────────────────
watch(routeSelectionKey, () => {
  syncRouteState().catch(() => {})
}, { immediate: true })

onMounted(async () => {
  await fetchShows()
  startIndexPolling()
})

onUnmounted(() => {
  clearTimeout(searchTimer)
  if (indexPollTimer) clearInterval(indexPollTimer)
  clearAllDogsPoll()
})
</script>

<template>
  <div class="dog-page">
    <!-- Top Navigation Bar -->
    <header class="dog-top-bar">
      <div class="dog-top-left">
        <!-- List view: link to main site home -->
        <NuxtLink v-if="currentView === 'list'" to="/" class="dog-back-link">
          <svg class="dog-back-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="160 208 80 128 160 48" />
          </svg>
          <span>erez.ac</span>
        </NuxtLink>
        <!-- Detail view: back to list -->
        <button v-else-if="currentView === 'detail'" class="dog-back-link" @click="goToList">
          <svg class="dog-back-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="160 208 80 128 160 48" />
          </svg>
          <span>Näyttelyt</span>
        </button>
        <!-- Results view: back to detail -->
        <button v-else-if="currentView === 'results'" class="dog-back-link" @click="goToDetail">
          <svg class="dog-back-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="160 208 80 128 160 48" />
          </svg>
          <span>Näyttely</span>
        </button>
      </div>

      <div class="dog-top-center">
        <h1 class="dog-top-title">
          <span v-if="currentView === 'list'">Näyttelytulokset</span>
          <span v-else-if="currentView === 'detail'">{{ showDetail?.title || selectedShow?.name }}</span>
          <span v-else-if="currentView === 'results'">{{ breedResults?.breed || selectedBreed?.name }}</span>
        </h1>
      </div>

      <div class="dog-top-right">
        <ThemeToggle />
      </div>
    </header>

    <!-- ═══ VIEW: SHOW LIST ═══ -->
    <Transition name="dog-fade" mode="out-in">
      <div v-if="currentView === 'list'" key="list">
        <!-- Space helper to separate header from search in list view -->
        <div class="dog-view-spacing" />

        <!-- Unified show/breed/judge search -->
        <div class="dog-search-wrap">
          <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="116" cy="116" r="84" />
            <line x1="175.4" y1="175.4" x2="224" y2="224" />
          </svg>
          <input
            v-model="filterText"
            type="text"
            class="dog-search-input"
            placeholder="Hae näyttelyä, rotua tai tuomaria..."
            @input="onSearchInput"
          />
        </div>

        <p v-if="indexedSearchActive && indexWarming" class="dog-status-note">
          Haku päivittyy: {{ indexStats.indexed_show_count }}/{{ indexStats.total_show_count }} näyttelyä.
        </p>
        <p v-else-if="indexedSearchActive && indexStats?.last_updated_iso" class="dog-status-note">
          Haku päivitetty {{ formatTimestamp(indexStats.last_updated_iso) }}.
        </p>

        <!-- Indexed search results -->
        <div v-if="indexedSearchActive">
          <div v-if="searchLoading" class="dog-skeleton-list">
            <div v-for="i in 4" :key="i" class="dog-skeleton-row" />
          </div>

          <div v-else-if="searchError" class="dog-error">
            <p>{{ searchError }}</p>
          </div>

          <div v-else-if="searchResults.length">
            <button
              v-for="res in searchResults"
              :key="res.show.id + '-' + (res.breed ? res.breed.breed_id : '')"
              class="dog-show-row"
              @click="onSelectSearchResult(res)"
            >
              <div class="dog-search-result-info">
                <span class="dog-search-show-line">
                  <span class="dog-show-date">{{ res.show.date }}</span>
                  <span class="dog-show-name">{{ res.show.name }}</span>
                </span>
                <span v-if="hasShowStats(res.show)" class="dog-show-stats" :aria-label="showStatsLabel(res.show)">
                  <span
                    v-for="stat in showStatItems(res.show)"
                    :key="stat.key"
                    :class="['dog-show-stat', stat.soft && 'dog-show-stat-soft', stat.live && 'dog-show-stat-live']"
                    :title="stat.title"
                  >
                    {{ stat.label }}
                  </span>
                </span>
                <span v-if="res.breed" class="dog-search-breed-tag">
                  {{ res.breed.name }} ({{ res.breed.count }} koiraa)
                  <span v-if="res.breed.judge" class="dog-search-judge-sub">
                    Tuomari: {{ res.breed.judge }}
                  </span>
                </span>
                <span v-else class="dog-search-breed-tag">Näyttely</span>
              </div>
              <svg class="dog-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="96 48 176 128 96 208" />
              </svg>
            </button>
          </div>

          <div v-else-if="!searchLoading" class="dog-empty">
            <p>Ei hakutuloksia.</p>
          </div>
        </div>

        <!-- Show list -->
        <div v-else>
          <!-- Featured: Tällä viikolla -->
          <div v-if="!filterText && thisWeekShows.length" class="dog-this-week-section">
            <h2 class="dog-this-week-heading">
              <svg class="dog-heading-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <rect x="32" y="48" width="192" height="176" rx="8" />
                <line x1="32" y1="88" x2="224" y2="88" />
                <line x1="80" y1="24" x2="80" y2="48" />
                <line x1="176" y1="24" x2="176" y2="48" />
              </svg>
              Tällä viikolla
            </h2>
            <div class="dog-this-week-list">
              <button
                v-for="show in thisWeekShows"
                :key="'week-' + show.id"
                class="dog-show-row dog-show-row-featured"
                @click="openShow(show)"
              >
                <span class="dog-show-date">{{ show.date }}</span>
                <span class="dog-show-body">
                  <span class="dog-show-name">{{ show.name }}</span>
                  <span v-if="hasShowStats(show)" class="dog-show-stats" :aria-label="showStatsLabel(show)">
                    <span
                      v-for="stat in showStatItems(show)"
                      :key="stat.key"
                      :class="['dog-show-stat', stat.soft && 'dog-show-stat-soft', stat.live && 'dog-show-stat-live']"
                      :title="stat.title"
                    >
                      {{ stat.label }}
                    </span>
                  </span>
                </span>
                <svg class="dog-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="96 48 176 128 96 208" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Loading skeleton -->
          <div v-if="showsLoading" class="dog-skeleton-list">
            <div v-for="i in 6" :key="i" class="dog-skeleton-row" />
          </div>

          <!-- Error -->
          <div v-else-if="showsError" class="dog-error">
            <p>{{ showsError }}</p>
            <button class="dog-btn" @click="fetchShows">Yritä uudelleen</button>
          </div>

          <!-- Show groups -->
          <div v-else-if="Object.keys(groupedShows).length">
            <div v-for="(monthShows, month) in groupedShows" :key="month" class="dog-month-group">
              <button class="dog-month-header" @click="toggleMonth(month)">
                <span class="dog-month-label">{{ month }}</span>
                <span class="dog-month-count">{{ monthShows.length }}</span>
                <svg
                  :class="['dog-chevron', !collapsedMonths.has(month) && 'dog-chevron-open']"
                  xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                >
                  <polyline points="208 96 128 176 48 96" />
                </svg>
              </button>
              <Transition name="dog-collapse">
                <div v-if="!collapsedMonths.has(month)" class="dog-month-list">
                  <button
                    v-for="show in monthShows"
                    :key="show.id"
                    class="dog-show-row"
                    @click="openShow(show)"
                  >
                    <span class="dog-show-date">{{ show.date }}</span>
                    <span class="dog-show-body">
                      <span class="dog-show-name">{{ show.name }}</span>
                      <span v-if="hasShowStats(show)" class="dog-show-stats" :aria-label="showStatsLabel(show)">
                        <span
                          v-for="stat in showStatItems(show)"
                          :key="stat.key"
                          :class="['dog-show-stat', stat.soft && 'dog-show-stat-soft', stat.live && 'dog-show-stat-live']"
                          :title="stat.title"
                        >
                          {{ stat.label }}
                        </span>
                      </span>
                    </span>
                    <svg class="dog-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="96 48 176 128 96 208" />
                    </svg>
                  </button>
                </div>
              </Transition>
            </div>
          </div>

          <!-- Empty state -->
          <div v-else class="dog-empty">
            <p>Ei näyttelyitä.</p>
          </div>
        </div>
      </div>

      <div v-else-if="currentView === 'detail'" key="detail">
        <!-- ═══ VIEW: SHOW DETAIL ═══ -->
        <!-- Metadata bar -->
        <div class="dog-meta-bar" v-if="showDetail">
          <a
            v-if="selectedShowSourceUrl"
            :href="selectedShowSourceUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="dog-source-link-pill"
          >
            <svg class="dog-pill-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M128,48H48V208H208V128" />
              <polyline points="160 48 208 48 208 96" />
              <line x1="128" y1="128" x2="208" y2="48" />
            </svg>
            Showlink
          </a>
          <span v-if="showDetail?.fetched_at_iso" class="dog-updated-pill">
            Päivitetty {{ formatTimestamp(showDetail.fetched_at_iso) }}
          </span>
        </div>

        <!-- Loading -->
        <div v-if="detailLoading" class="dog-skeleton-list">
          <div v-for="i in 8" :key="i" class="dog-skeleton-row" />
        </div>

        <!-- Error -->
        <div v-else-if="detailError" class="dog-error">
          <p>{{ detailError }}</p>
          <button class="dog-btn" @click="fetchShowDetail(selectedShow)">Yritä uudelleen</button>
        </div>

        <!-- Breeds list -->
        <div v-else-if="showDetail">
          <!-- Sub-tabs for Show Detail view -->
          <div class="dog-tabs dog-detail-tabs">
            <button
              :class="['dog-tab', showDetailTab === 'breeds' && 'dog-tab-active']"
              @click="showDetailTab = 'breeds'"
            >
              Rotuluettelo ({{ showDetail.breeds?.length || 0 }})
            </button>
            <button
              :class="['dog-tab', showDetailTab === 'dogs' && 'dog-tab-active']"
              @click="onSelectDogsTab"
            >
              Koirat & Tulokset
            </button>
          </div>

          <!-- TAB 1: BREEDS LIST -->
          <div v-if="showDetailTab === 'breeds'">
            <div class="dog-detail-filter-bar">
              <div class="dog-search-wrap dog-breed-search">
                <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="116" cy="116" r="84" />
                  <line x1="175.4" y1="175.4" x2="224" y2="224" />
                </svg>
                <input
                  v-model="breedSearchQuery"
                  type="text"
                  class="dog-search-input"
                  placeholder="Hae rotua tai tuomaria..."
                />
              </div>
              <label class="dog-toggle">
                <input v-model="showResultsOnly" type="checkbox" />
                <span>Vain tuloksia</span>
              </label>
            </div>
            <div v-if="filteredBreeds.length" class="dog-breed-list">
              <button
                v-for="breed in filteredBreeds"
                :key="breed.breed_id || breed.name"
                :class="['dog-breed-row', !breed.has_results && 'dog-breed-row-disabled']"
                :disabled="!breed.has_results"
                @click="openBreed(breed)"
              >
                <div class="dog-breed-info">
                  <span class="dog-breed-name">{{ breed.name }}</span>
                  <span class="dog-breed-count">
                    {{ breed.count }} koiraa
                    <span v-if="breed.judge" class="dog-breed-judge">
                      • Tuomari: {{ breed.judge }}
                    </span>
                  </span>
                </div>
                <div class="dog-breed-status">
                  <span v-if="breed.has_results" class="dog-check" title="Tulokset saatavilla">✓</span>
                  <span v-else class="dog-no-results" title="Ei tuloksia">—</span>
                </div>
              </button>
            </div>
            <div v-else class="dog-empty">
              <p>Ei rotuja valitulla rajauksella.</p>
            </div>
          </div>

          <!-- TAB 2: DOG RESULTS & SEARCH -->
          <div v-else-if="showDetailTab === 'dogs'">
            <div v-if="allDogsLoading" class="dog-progress-card" role="status" aria-live="polite">
              <div class="dog-progress-orbit" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <div class="dog-progress-content">
                <h2 class="dog-progress-title">Koko näyttelyn tuloksia valmistellaan</h2>
                <p class="dog-progress-copy">{{ allDogsProgressText }}</p>
                <div
                  :class="['dog-progress-track', allDogsProgressPercent === null && 'dog-progress-track-indeterminate']"
                >
                  <span
                    class="dog-progress-fill"
                    :style="allDogsProgressPercent !== null ? { width: `${allDogsProgressPercent}%` } : undefined"
                  />
                </div>
                <p class="dog-progress-note">
                  Ensimmäinen haku voi kestää, koska rotujen tulossivut haetaan taustalla tarkoituksella hitaasti.
                </p>
              </div>
            </div>

            <div v-else-if="allDogsError" class="dog-error">
              <p>{{ allDogsError }}</p>
              <button class="dog-btn" @click="loadAllShowResults">Yritä uudelleen</button>
            </div>

            <div v-else>
              <!-- Show-wide Filter Panel -->
              <div class="dog-results-filter-panel">
                <div class="dog-results-filter-grid">
                  <!-- Search text -->
                  <div class="dog-filter-col">
                    <label class="dog-filter-label">Hae koiraa</label>
                    <div class="dog-search-wrap dog-filter-search">
                      <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="116" cy="116" r="84" />
                        <line x1="175.4" y1="175.4" x2="224" y2="224" />
                      </svg>
                      <input
                        v-model="dogSearchQuery"
                        type="text"
                        class="dog-search-input"
                        placeholder="Nimi, numero tai rotu..."
                      />
                    </div>
                  </div>
                  <!-- Grade selection -->
                  <div class="dog-filter-col">
                    <label class="dog-filter-label">Laatuarvostelu</label>
                    <select v-model="dogGradeFilter" class="dog-filter-select">
                      <option value="">Kaikki arvostelut</option>
                      <option value="eri">ERI (Erinomainen)</option>
                      <option value="eh">EH (Erittäin hyvä)</option>
                      <option value="h">H (Hyvä)</option>
                      <option value="t">T (Tyydyttävä)</option>
                      <option value="kp">KP (Kunniapalkinto)</option>
                      <option value="hyl">HYL (Hylätty)</option>
                      <option value="eva">EVA (Ei voida arvostella)</option>
                      <option value="poissa">POISSA</option>
                    </select>
                  </div>
                  <!-- Class selection -->
                  <div v-if="availableShowClasses.length" class="dog-filter-col">
                    <label class="dog-filter-label">Luokka</label>
                    <select v-model="dogClassFilter" class="dog-filter-select">
                      <option value="">Kaikki luokat</option>
                      <option v-for="c in availableShowClasses" :key="c" :value="c">{{ c }}</option>
                    </select>
                  </div>
                  <!-- Award selection -->
                  <div v-if="availableShowAwards.length" class="dog-filter-col">
                    <label class="dog-filter-label">Palkinto</label>
                    <select v-model="dogAwardFilter" class="dog-filter-select">
                      <option value="">Kaikki palkinnot</option>
                      <option v-for="a in availableShowAwards" :key="a" :value="a">{{ a }}</option>
                    </select>
                  </div>
                </div>
              </div>

              <!-- Grouped Dog Results -->
              <div v-if="allDogsGroupedByBreed.length" class="dog-all-dogs-list">
                <div v-for="group in allDogsGroupedByBreed" :key="group.breedName" class="dog-breed-group-section">
                  <button class="dog-breed-group-header-btn" @click="openBreed(group.breedObj)">
                    <span class="dog-breed-group-title">{{ group.breedName }}</span>
                    <span class="dog-breed-group-badge">{{ group.dogs.length }} tulosta</span>
                    <svg class="dog-arrow-sm" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="96 48 176 128 96 208" />
                    </svg>
                  </button>

                  <div class="dog-results-grid">
                    <div
                      v-for="dog in group.dogs"
                      :key="dog.number || dog.name"
                      class="dog-result-card"
                      :class="gradeBorderClass(dog.grade)"
                    >
                      <div class="dog-result-main">
                        <div class="dog-result-top">
                          <span v-if="dog.number" class="dog-catalog-num">#{{ dog.number }}</span>
                          <span v-if="dog.placement" class="dog-placement-badge">{{ dog.placement }}.</span>
                          <span class="dog-class-badge-inline">{{ dog.class_name }}</span>
                          <span class="dog-gender-badge-inline">{{ dog.gender === 'uros' ? '♂' : dog.gender === 'narttu' ? '♀' : '' }}</span>
                          
                          <a
                            v-if="dog.reg_url"
                            :href="dog.reg_url"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="dog-dog-name"
                          >
                            {{ dog.name }}
                            <svg class="dog-external" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                              <path d="M128,48H48V208H208V128" />
                              <polyline points="160 48 208 48 208 96" />
                              <line x1="128" y1="128" x2="208" y2="48" />
                            </svg>
                          </a>
                          <span v-else class="dog-dog-name-plain">{{ dog.name }}</span>
                        </div>
                        <div class="dog-result-badges">
                          <span v-if="dog.grade" :class="['dog-grade', gradeClasses(dog.grade)]">
                            {{ dog.grade }}
                          </span>
                          <span
                            v-for="(a, ai) in (dog.awards || '').split(',').map(s => s.trim()).filter(Boolean)"
                            :key="ai"
                            class="dog-mini-award"
                          >
                            {{ a }}
                          </span>
                        </div>
                      </div>

                      <!-- Critique toggle -->
                      <button
                        v-if="dog.critique"
                        class="dog-critique-toggle"
                        @click="toggleCritique(`all-${group.breedName}-${dog.number || dog.name}`)"
                      >
                        <svg class="dog-critique-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                          <rect x="40" y="32" width="176" height="192" rx="16" />
                          <line x1="80" y1="80" x2="176" y2="80" />
                          <line x1="80" y1="128" x2="176" y2="128" />
                          <line x1="80" y1="176" x2="136" y2="176" />
                        </svg>
                        <span>{{ expandedCritiques.has(`all-${group.breedName}-${dog.number || dog.name}`) ? 'Piilota arvostelu' : 'Näytä arvostelu' }}</span>
                        <svg
                          :class="['dog-chevron-sm', expandedCritiques.has(`all-${group.breedName}-${dog.number || dog.name}`) && 'dog-chevron-open']"
                          xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                        >
                          <polyline points="208 96 128 176 48 96" />
                        </svg>
                      </button>
                      <Transition name="dog-collapse">
                        <div v-if="expandedCritiques.has(`all-${group.breedName}-${dog.number || dog.name}`)" class="dog-critique-text">
                          {{ dog.critique }}
                        </div>
                      </Transition>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="dog-empty">
                <p>Ei tuloksia valituilla suodattimilla.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="currentView === 'results'" key="results">
        <!-- ═══ VIEW: BREED RESULTS ═══ -->
        <!-- Metadata bar -->
        <div class="dog-meta-bar" v-if="breedResults">
          <span v-if="breedResults?.judge" class="dog-judge-pill">
            <svg class="dog-pill-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="128" cy="96" r="64"/>
              <path d="M32,224a96,96,0,0,1,192,0"/>
            </svg>
            Tuomari: <strong>{{ breedResults.judge }}</strong>
          </span>
          <a
            v-if="selectedBreedSourceUrl"
            :href="selectedBreedSourceUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="dog-source-link-pill"
          >
            <svg class="dog-pill-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M128,48H48V208H208V128" />
              <polyline points="160 48 208 48 208 96" />
              <line x1="128" y1="128" x2="208" y2="48" />
            </svg>
            Showlink
          </a>
          <span v-if="breedResults?.fetched_at_iso" class="dog-updated-pill">
            Päivitetty {{ formatTimestamp(breedResults.fetched_at_iso) }}
          </span>
        </div>

        <!-- Loading -->
        <div v-if="resultsLoading" class="dog-skeleton-list">
          <div v-for="i in 6" :key="i" class="dog-skeleton-row dog-skeleton-tall" />
        </div>

        <!-- Error -->
        <div v-else-if="resultsError" class="dog-error">
          <p>{{ resultsError }}</p>
          <button class="dog-btn" @click="fetchBreedResults(selectedBreed)">Yritä uudelleen</button>
        </div>

        <div v-else-if="breedResults">
          <!-- Filter Panel -->
          <div class="dog-results-filter-panel">
            <div class="dog-results-filter-grid">
              <!-- Search text -->
              <div class="dog-filter-col">
                <label class="dog-filter-label">Hae koiraa</label>
                <div class="dog-search-wrap dog-filter-search">
                  <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="116" cy="116" r="84" />
                    <line x1="175.4" y1="175.4" x2="224" y2="224" />
                  </svg>
                  <input
                    v-model="dogSearchQuery"
                    type="text"
                    class="dog-search-input"
                    placeholder="Nimi tai numero..."
                  />
                </div>
              </div>
              <!-- Grade selection -->
              <div class="dog-filter-col">
                <label class="dog-filter-label">Laatuarvostelu</label>
                <select v-model="dogGradeFilter" class="dog-filter-select">
                  <option value="">Kaikki arvostelut</option>
                  <option value="eri">ERI (Erinomainen)</option>
                  <option value="eh">EH (Erittäin hyvä)</option>
                  <option value="h">H (Hyvä)</option>
                  <option value="t">T (Tyydyttävä)</option>
                  <option value="kp">KP (Kunniapalkinto)</option>
                  <option value="hyl">HYL (Hylätty)</option>
                  <option value="eva">EVA (Ei voida arvostella)</option>
                  <option value="poissa">POISSA</option>
                </select>
              </div>
              <!-- Class selection -->
              <div v-if="availableClasses.length" class="dog-filter-col">
                <label class="dog-filter-label">Luokka</label>
                <select v-model="dogClassFilter" class="dog-filter-select">
                  <option value="">Kaikki luokat</option>
                  <option v-for="c in availableClasses" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <!-- Award selection -->
              <div v-if="availableAwards.length" class="dog-filter-col">
                <label class="dog-filter-label">Palkinto</label>
                <select v-model="dogAwardFilter" class="dog-filter-select">
                  <option value="">Kaikki palkinnot</option>
                  <option v-for="a in availableAwards" :key="a" :value="a">{{ a }}</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Awards -->
          <div v-if="breedResults.awards?.length && !dogSearchQuery && !dogGradeFilter && !dogClassFilter && !dogAwardFilter" class="dog-awards">
            <div
              v-for="(award, i) in breedResults.awards"
              :key="i"
              class="dog-award-card"
            >
              <span class="dog-award-type">{{ award.type }}</span>
              <span class="dog-award-text">{{ award.text }}</span>
            </div>
          </div>

          <!-- Results by gender and class -->
          <div v-for="(classes, gender) in resultsByGenderAndClass" :key="gender" class="dog-gender-group">
            <h2 class="dog-gender-heading">
              <span class="dog-gender-symbol">{{ gender === 'uros' ? '♂' : gender === 'narttu' ? '♀' : '🐾' }}</span>
              {{ gender === 'uros' ? 'Urokset' : gender === 'narttu' ? 'Nartut' : gender }}
            </h2>

            <div v-for="(dogs, className) in classes" :key="className" class="dog-class-section">
              <div class="dog-class-title-header">
                <span class="dog-class-badge">Luokka</span>
                <span class="dog-class-title-text">{{ className }}</span>
              </div>

              <div class="dog-results-grid">
                <div
                  v-for="dog in dogs"
                  :key="dog.number || dog.name"
                  class="dog-result-card"
                  :class="gradeBorderClass(dog.grade)"
                >
                  <div class="dog-result-main">
                    <div class="dog-result-top">
                      <span v-if="dog.number" class="dog-catalog-num">#{{ dog.number }}</span>
                      <span v-if="dog.placement" class="dog-placement-badge">{{ dog.placement }}.</span>
                      <a
                        v-if="dog.reg_url"
                        :href="dog.reg_url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="dog-dog-name"
                      >
                        {{ dog.name }}
                        <svg class="dog-external" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M128,48H48V208H208V128" />
                          <polyline points="160 48 208 48 208 96" />
                          <line x1="128" y1="128" x2="208" y2="48" />
                        </svg>
                      </a>
                      <span v-else class="dog-dog-name-plain">{{ dog.name }}</span>
                    </div>
                    <div class="dog-result-badges">
                      <span v-if="dog.grade" :class="['dog-grade', gradeClasses(dog.grade)]">
                        {{ dog.grade }}
                      </span>
                      <span
                        v-for="(a, ai) in (dog.awards || '').split(',').map(s => s.trim()).filter(Boolean)"
                        :key="ai"
                        class="dog-mini-award"
                      >
                        {{ a }}
                      </span>
                    </div>
                  </div>

                  <!-- Critique toggle -->
                  <button
                    v-if="dog.critique"
                    class="dog-critique-toggle"
                    @click="toggleCritique(`${gender}-${className}-${dog.number || dog.name}`)"
                  >
                    <svg class="dog-critique-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="40" y="32" width="176" height="192" rx="16" />
                      <line x1="80" y1="80" x2="176" y2="80" />
                      <line x1="80" y1="128" x2="176" y2="128" />
                      <line x1="80" y1="176" x2="136" y2="176" />
                    </svg>
                    <span>{{ expandedCritiques.has(`${gender}-${className}-${dog.number || dog.name}`) ? 'Piilota arvostelu' : 'Näytä arvostelu' }}</span>
                    <svg
                      :class="['dog-chevron-sm', expandedCritiques.has(`${gender}-${className}-${dog.number || dog.name}`) && 'dog-chevron-open']"
                      xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                    >
                      <polyline points="208 96 128 176 48 96" />
                    </svg>
                  </button>
                  <Transition name="dog-collapse">
                    <div v-if="expandedCritiques.has(`${gender}-${className}-${dog.number || dog.name}`)" class="dog-critique-text">
                      {{ dog.critique }}
                    </div>
                  </Transition>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty results -->
          <div v-if="!Object.keys(resultsByGenderAndClass).length" class="dog-empty">
            <p>Ei tuloksia valituilla suodattimilla.</p>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* ═══ Scoped design tokens ═══ */
.dog-page {
  /* Warm/neutral light theme colors */
  --dog-bg: #fdfbf7;         /* Warm stone-like light bg */
  --dog-surface: #f5f2eb;    /* Slightly darker surface */
  --dog-surface-el: #eae6db; /* Elements background */
  --dog-accent: #c2410c;     /* Warm rust/orange accent for light mode */
  --dog-accent-2: #b45309;   /* Slightly deeper amber/orange accent */
  --dog-text: #292524;       /* Dark text (warm stone) */
  --dog-text-muted: #6b6661; /* Muted text */
  --dog-border: #dcd7cc;     /* Light borders */
  --dog-gold: #b45309;       /* Gold color for ERI in light mode (deeper for readability) */
  --dog-silver: #475569;     /* Silver for EH */
  --dog-bronze: #854d0e;     /* Bronze for H */
  --dog-info: #0284c7;       /* Blue for KP */

  font-family: 'DM Sans', sans-serif;
  font-weight: 300;
  color: var(--dog-text);
  background: var(--dog-bg);
  min-height: 100dvh;
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem;
  padding-bottom: 4rem;
  transition: background-color 0.3s ease, color 0.3s ease;
}

:where(.dark) .dog-page {
  /* Dark mode override */
  --dog-bg: #121212;
  --dog-surface: #1e1e1e;
  --dog-surface-el: #2a2a2a;
  --dog-accent: #e8a87c;
  --dog-accent-2: #d4a373;
  --dog-text: #e8e6e3;
  --dog-text-muted: #9ca3af;
  --dog-border: #333333;
  --dog-gold: #f59e0b;
  --dog-silver: #94a3b8;
  --dog-bronze: #cd7f32;
  --dog-info: #60a5fa;
}

/* ═══ Top bar / Header ═══ */
.dog-top-bar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0.75rem 0;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--dog-border);
}
.dog-top-left {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-width: 0;
}
.dog-top-center {
  display: flex;
  justify-content: center;
  align-items: center;
  min-width: 0;
}
.dog-top-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--dog-text);
  margin: 0;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
@media (max-width: 640px) {
  .dog-top-title {
    font-size: 1.05rem;
  }
}
.dog-top-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
.dog-back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.9rem;
  color: var(--dog-text-muted);
  text-decoration: none;
  background: none;
  border: none;
  font-family: inherit;
  font-weight: 500;
  cursor: pointer;
  padding: 0;
  min-height: 44px;
  transition: color 0.15s;
  white-space: nowrap;
}
.dog-back-link:hover {
  color: var(--dog-accent);
}
.dog-back-icon {
  width: 1rem;
  height: 1rem;
  stroke-width: 2.5;
}

/* ═══ Page layout & metadata ═══ */
.dog-view-spacing {
  height: 0.5rem;
}
.dog-meta-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
}
.dog-source-link-pill,
.dog-updated-pill,
.dog-judge-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: var(--dog-surface);
  border: 1px solid var(--dog-border);
  color: var(--dog-text-muted);
}
.dog-source-link-pill {
  color: var(--dog-accent);
  text-decoration: none;
  font-weight: 500;
  transition: background-color 0.15s, border-color 0.15s;
}
.dog-source-link-pill:hover {
  background: var(--dog-surface-el);
  border-color: var(--dog-accent);
}
.dog-judge-pill strong {
  color: var(--dog-text);
  font-weight: 500;
}
.dog-pill-icon {
  width: 0.875rem;
  height: 0.875rem;
  flex-shrink: 0;
}

/* ═══ Tabs ═══ */
.dog-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--dog-border);
  margin-bottom: 1.5rem;
}
.dog-tab {
  flex: 1;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--dog-text-muted);
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  min-height: 44px;
}
.dog-tab:hover {
  color: var(--dog-text);
}
.dog-tab-active {
  color: var(--dog-accent);
  border-bottom-color: var(--dog-accent);
}

/* ═══ Search ═══ */
.dog-search-wrap {
  position: relative;
  margin-bottom: 1.5rem;
}
.dog-search-icon {
  position: absolute;
  left: 0.875rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.125rem;
  height: 1.125rem;
  color: var(--dog-text-muted);
  pointer-events: none;
}
.dog-search-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  background: var(--dog-surface);
  border: 1px solid var(--dog-border);
  border-radius: 0.5rem;
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 300;
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
  min-height: 44px;
}
.dog-search-input::placeholder {
  color: var(--dog-text-muted);
}
.dog-search-input:focus {
  border-color: var(--dog-accent);
}
.dog-status-note {
  margin: -0.85rem 0 1.5rem;
  color: var(--dog-text-muted);
  font-size: 0.8rem;
}

/* ═══ Featured: Tällä viikolla ═══ */
.dog-this-week-section {
  background: var(--dog-surface);
  border: 1px solid var(--dog-border);
  border-radius: 0.75rem;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}
.dog-this-week-heading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--dog-accent-2);
  margin: 0 0 1rem 0;
}
.dog-heading-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: var(--dog-accent);
}
.dog-this-week-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.dog-show-row-featured {
  background: var(--dog-surface-el);
  border-radius: 0.5rem;
  border-bottom: none;
}
.dog-show-row-featured:hover {
  background: color-mix(in srgb, var(--dog-surface-el) 92%, var(--dog-accent));
}

/* ═══ Skeleton ═══ */
.dog-skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.dog-skeleton-row {
  height: 3rem;
  background: var(--dog-surface);
  border-radius: 0.5rem;
  animation: dog-pulse 1.5s ease-in-out infinite;
}
.dog-skeleton-tall {
  height: 5rem;
}
@keyframes dog-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}

/* ═══ Whole-show result cache progress ═══ */
.dog-progress-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  background:
    radial-gradient(circle at 15% 20%, color-mix(in srgb, var(--dog-accent) 18%, transparent), transparent 34%),
    linear-gradient(135deg, var(--dog-surface), var(--dog-surface-el));
  border: 1px solid var(--dog-border);
  border-radius: 0.9rem;
  overflow: hidden;
}
@media (max-width: 520px) {
  .dog-progress-card {
    align-items: flex-start;
  }
}
.dog-progress-orbit {
  position: relative;
  width: 3rem;
  height: 3rem;
  flex-shrink: 0;
  border: 1px solid color-mix(in srgb, var(--dog-accent) 35%, transparent);
  border-radius: 999px;
  animation: dog-orbit-spin 2.8s linear infinite;
}
.dog-progress-orbit span {
  position: absolute;
  width: 0.55rem;
  height: 0.55rem;
  background: var(--dog-accent);
  border-radius: 999px;
}
.dog-progress-orbit span:nth-child(1) {
  top: -0.3rem;
  left: 50%;
  transform: translateX(-50%);
}
.dog-progress-orbit span:nth-child(2) {
  right: 0.2rem;
  bottom: 0.35rem;
  opacity: 0.75;
}
.dog-progress-orbit span:nth-child(3) {
  left: 0.2rem;
  bottom: 0.35rem;
  opacity: 0.45;
}
.dog-progress-content {
  min-width: 0;
  flex: 1;
}
.dog-progress-title {
  margin: 0 0 0.35rem;
  color: var(--dog-text);
  font-size: 1rem;
  font-weight: 600;
}
.dog-progress-copy,
.dog-progress-note {
  margin: 0;
  color: var(--dog-text-muted);
  font-size: 0.85rem;
}
.dog-progress-track {
  position: relative;
  height: 0.45rem;
  margin: 0.85rem 0 0.55rem;
  background: color-mix(in srgb, var(--dog-surface-el) 80%, var(--dog-text-muted));
  border-radius: 999px;
  overflow: hidden;
}
.dog-progress-fill {
  display: block;
  width: 0;
  height: 100%;
  background: linear-gradient(90deg, var(--dog-accent), var(--dog-accent-2));
  border-radius: inherit;
  transition: width 0.3s ease;
}
.dog-progress-track-indeterminate .dog-progress-fill {
  width: 38%;
  animation: dog-progress-slide 1.6s ease-in-out infinite;
}
@keyframes dog-orbit-spin {
  to { transform: rotate(360deg); }
}
@keyframes dog-progress-slide {
  0% { transform: translateX(-110%); }
  100% { transform: translateX(290%); }
}
@media (prefers-reduced-motion: reduce) {
  .dog-progress-orbit,
  .dog-progress-track-indeterminate .dog-progress-fill {
    animation: none;
  }
}

/* ═══ Error ═══ */
.dog-error {
  text-align: center;
  padding: 2rem 1rem;
  color: var(--dog-text-muted);
}
.dog-btn {
  margin-top: 0.75rem;
  padding: 0.6rem 1.5rem;
  background: var(--dog-accent);
  color: var(--dog-bg);
  border: none;
  border-radius: 0.5rem;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  min-height: 44px;
}
.dog-btn:hover {
  opacity: 0.85;
}

/* ═══ Empty ═══ */
.dog-empty {
  text-align: center;
  padding: 2rem;
  color: var(--dog-text-muted);
}
.dog-empty-hint {
  font-size: 0.85rem;
}

/* ═══ Month groups ═══ */
.dog-month-group {
  margin-bottom: 0.5rem;
}
.dog-month-header {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--dog-surface-el);
  border: none;
  border-radius: 0.5rem;
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  gap: 0.5rem;
  min-height: 44px;
  transition: background 0.15s;
}
.dog-month-header:hover {
  background: color-mix(in srgb, var(--dog-surface-el) 95%, var(--dog-text));
}
.dog-month-label {
  flex: 1;
  text-align: left;
}
.dog-month-count {
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--dog-text-muted);
  background: var(--dog-surface);
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}
.dog-chevron {
  width: 1.25rem;
  height: 1.25rem;
  transition: transform 0.2s;
  transform: rotate(-90deg);
  color: var(--dog-text-muted);
  flex-shrink: 0;
}
.dog-chevron-open {
  transform: rotate(0deg);
}

/* ═══ Show rows ═══ */
.dog-month-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.25rem;
}
.dog-show-row {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--dog-surface);
  border: 1px solid var(--dog-border);
  border-radius: 0.5rem;
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 300;
  cursor: pointer;
  text-align: left;
  gap: 0.75rem;
  min-height: 44px;
  transition: background 0.12s, border-color 0.12s;
}
.dog-show-row:hover {
  background: var(--dog-surface-el);
  border-color: var(--dog-accent);
}
.dog-show-date {
  font-family: 'Commit Mono', ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.8rem;
  color: var(--dog-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}
.dog-show-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}
.dog-show-name {
  flex: 1;
  min-width: 0;
  color: var(--dog-text);
  overflow: hidden;
  text-overflow: ellipsis;
}
.dog-show-stats {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.3rem;
  flex-shrink: 0;
}
.dog-show-stat {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  border: 1px solid var(--dog-border);
  border-radius: 999px;
  padding: 0.15rem 0.45rem;
  background: var(--dog-surface-el);
  color: var(--dog-text-muted);
  font-size: 0.72rem;
  font-weight: 500;
  line-height: 1.2;
}
.dog-show-stat-soft {
  color: var(--dog-accent-2);
  border-color: color-mix(in srgb, var(--dog-accent-2) 30%, var(--dog-border));
  background: color-mix(in srgb, var(--dog-accent-2) 8%, var(--dog-surface-el));
}
.dog-show-stat-live {
  color: var(--dog-bg);
  border-color: var(--dog-accent);
  background: var(--dog-accent);
}
.dog-search-result-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}
.dog-search-show-line {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}
.dog-search-breed-tag {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--dog-accent-2);
  margin-top: 0.15rem;
}
.dog-search-judge-sub {
  display: block;
  font-size: 0.75rem;
  color: var(--dog-text-muted);
  margin-top: 0.15rem;
  font-style: italic;
}
.dog-arrow {
  width: 1rem;
  height: 1rem;
  color: var(--dog-text-muted);
  flex-shrink: 0;
}
@media (max-width: 520px) {
  .dog-show-row {
    align-items: flex-start;
    gap: 0.55rem;
  }
  .dog-show-body {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
  }
  .dog-show-stats {
    justify-content: flex-start;
  }
  .dog-show-stat {
    font-size: 0.68rem;
    padding: 0.12rem 0.4rem;
  }
  .dog-search-show-line {
    align-items: flex-start;
  }
  .dog-arrow {
    align-self: center;
  }
}



/* ═══ Breed list (detail view) ═══ */
.dog-detail-filter-bar {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}
@media (min-width: 640px) {
  .dog-detail-filter-bar {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}
.dog-breed-search {
  flex: 1;
  max-width: 400px;
  margin-bottom: 0;
}
.dog-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 44px;
  color: var(--dog-text-muted);
  font-size: 0.85rem;
  cursor: pointer;
}
.dog-toggle input {
  width: 1rem;
  height: 1rem;
  accent-color: var(--dog-accent);
}
.dog-breed-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.dog-breed-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--dog-surface);
  border: 1px solid var(--dog-border);
  border-radius: 0.5rem;
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 300;
  cursor: pointer;
  text-align: left;
  min-height: 44px;
  transition: background 0.12s, border-color 0.12s;
}
.dog-breed-row:hover:not(:disabled) {
  background: var(--dog-surface-el);
  border-color: var(--dog-accent);
}
.dog-breed-row-disabled {
  cursor: default;
  opacity: 0.5;
}
.dog-breed-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.dog-breed-name {
  font-weight: 500;
}
.dog-breed-count {
  font-size: 0.8rem;
  color: var(--dog-text-muted);
}
.dog-breed-judge {
  color: var(--dog-text-muted);
  font-style: italic;
  font-size: 0.75rem;
}
.dog-breed-status {
  flex-shrink: 0;
}
.dog-check {
  color: #10b981;
  font-size: 1.1rem;
  font-weight: 700;
}
.dog-no-results {
  color: var(--dog-text-muted);
}

/* ═══ Filter Panel (results view) ═══ */
.dog-results-filter-panel {
  background: var(--dog-surface);
  border: 1px solid var(--dog-border);
  border-radius: 0.75rem;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}
.dog-results-filter-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}
@media (min-width: 640px) {
  .dog-results-filter-grid {
    grid-template-columns: 2fr 1.2fr 1.2fr 1.2fr;
  }
}
.dog-filter-col {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.dog-filter-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--dog-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.dog-filter-select {
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: var(--dog-surface-el);
  border: 1px solid var(--dog-border);
  border-radius: 0.375rem;
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.85rem;
  outline: none;
  min-height: 38px;
  cursor: pointer;
  box-sizing: border-box;
}
.dog-filter-select:focus {
  border-color: var(--dog-accent);
}
.dog-filter-search {
  margin-bottom: 0;
}
.dog-filter-search .dog-search-input {
  padding: 0.5rem 0.75rem 0.5rem 2.25rem;
  font-size: 0.85rem;
  min-height: 38px;
  background: var(--dog-surface-el);
}
.dog-filter-search .dog-search-icon {
  width: 1rem;
  height: 1rem;
  left: 0.75rem;
}

/* ═══ Awards ═══ */
.dog-awards {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}
.dog-award-card {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.6rem 1rem;
  background: linear-gradient(135deg, var(--dog-surface-el), var(--dog-surface));
  border: 1px solid var(--dog-accent-2);
  border-radius: 0.5rem;
  min-width: 100px;
}
.dog-award-type {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--dog-accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.dog-award-text {
  font-size: 0.85rem;
  color: var(--dog-text);
  font-weight: 400;
}

/* ═══ Gender heading ═══ */
.dog-gender-group {
  margin-bottom: 2rem;
}
.dog-gender-heading {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--dog-text);
  margin: 1.5rem 0 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--dog-border);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.dog-gender-symbol {
  font-size: 1.15rem;
  color: var(--dog-accent);
}

/* ═══ Class section ═══ */
.dog-class-section {
  margin-bottom: 1.5rem;
}
.dog-class-title-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
  margin-bottom: 0.75rem;
  border-bottom: 1px dashed var(--dog-border);
}
.dog-class-badge {
  font-size: 0.7rem;
  font-weight: 600;
  background: var(--dog-surface-el);
  color: var(--dog-text-muted);
  padding: 0.15rem 0.45rem;
  border-radius: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.dog-class-title-text {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--dog-text);
}
.dog-results-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* ═══ Result card ═══ */
.dog-result-card {
  background: var(--dog-surface);
  border: 1px solid var(--dog-border);
  border-radius: 0.5rem;
  overflow: hidden;
  transition: border-color 0.15s;
}
.dog-result-card:hover {
  border-color: var(--dog-accent-2);
}
.dog-result-main {
  padding: 0.85rem 1.25rem;
}
.dog-result-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}
.dog-catalog-num {
  font-family: 'Commit Mono', ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.75rem;
  color: var(--dog-text-muted);
  background: var(--dog-surface-el);
  padding: 0.1rem 0.4rem;
  border-radius: 0.25rem;
  flex-shrink: 0;
}
.dog-placement-badge {
  font-size: 0.8rem;
  font-weight: 700;
  background: color-mix(in srgb, var(--dog-accent) 20%, transparent);
  color: var(--dog-accent);
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.dog-dog-name {
  color: var(--dog-accent) !important;
  font-weight: 500;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
.dog-dog-name:hover {
  text-decoration: underline;
}
.dog-dog-name-plain {
  font-weight: 500;
  color: var(--dog-text);
}
.dog-external {
  width: 0.75rem;
  height: 0.75rem;
  opacity: 0.6;
  flex-shrink: 0;
}

/* ═══ Grade border accenting ═══ */
.dog-result-card.dog-border-gold { border-left: 4px solid var(--dog-gold); }
.dog-result-card.dog-border-silver { border-left: 4px solid var(--dog-silver); }
.dog-result-card.dog-border-bronze { border-left: 4px solid var(--dog-bronze); }
.dog-result-card.dog-border-info { border-left: 4px solid var(--dog-info); }
.dog-result-card.dog-border-muted { border-left: 4px solid var(--dog-text-muted); }
.dog-result-card.dog-border-default { border-left: 4px solid var(--dog-border); }

/* ═══ Result badges ═══ */
.dog-result-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}
.dog-grade {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.dog-badge-gold {
  background: color-mix(in srgb, var(--dog-gold) 15%, transparent);
  color: var(--dog-gold);
  border: 1px solid color-mix(in srgb, var(--dog-gold) 35%, transparent);
}
.dog-badge-silver {
  background: color-mix(in srgb, var(--dog-silver) 15%, transparent);
  color: var(--dog-silver);
  border: 1px solid color-mix(in srgb, var(--dog-silver) 30%, transparent);
}
.dog-badge-bronze {
  background: color-mix(in srgb, var(--dog-bronze) 15%, transparent);
  color: var(--dog-bronze);
  border: 1px solid color-mix(in srgb, var(--dog-bronze) 30%, transparent);
}
.dog-badge-info {
  background: color-mix(in srgb, var(--dog-info) 15%, transparent);
  color: var(--dog-info);
  border: 1px solid color-mix(in srgb, var(--dog-info) 30%, transparent);
}
.dog-badge-muted {
  background: color-mix(in srgb, var(--dog-text-muted) 10%, transparent);
  color: var(--dog-text-muted);
  border: 1px solid color-mix(in srgb, var(--dog-text-muted) 20%, transparent);
}
.dog-badge-default {
  background: var(--dog-surface-el);
  color: var(--dog-text);
  border: 1px solid var(--dog-border);
}
.dog-mini-award {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.45rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  font-weight: 600;
  background: color-mix(in srgb, var(--dog-accent) 12%, transparent);
  color: var(--dog-accent);
  border: 1px solid color-mix(in srgb, var(--dog-accent) 25%, transparent);
}

/* ═══ Critique ═══ */
.dog-critique-toggle {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  width: 100%;
  padding: 0.6rem 1.25rem;
  background: var(--dog-surface-el);
  border: none;
  border-top: 1px solid var(--dog-border);
  color: var(--dog-text-muted);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 400;
  cursor: pointer;
  min-height: 44px;
  transition: color 0.12s;
}
.dog-critique-toggle:hover {
  color: var(--dog-text);
}
.dog-critique-icon {
  width: 0.9rem;
  height: 0.9rem;
  color: var(--dog-text-muted);
}
.dog-chevron-sm {
  width: 1rem;
  height: 1rem;
  transition: transform 0.2s;
  transform: rotate(-90deg);
  flex-shrink: 0;
  margin-left: auto;
}
.dog-critique-text {
  padding: 0.85rem 1.25rem;
  font-size: 0.85rem;
  font-weight: 300;
  line-height: 1.6;
  color: var(--dog-text-muted);
  background: var(--dog-surface-el);
  border-top: 1px solid var(--dog-border);
  font-style: italic;
}

/* ═══ Transitions ═══ */
.dog-fade-enter-active,
.dog-fade-leave-active {
  transition: opacity 0.18s ease;
}
.dog-fade-enter-from,
.dog-fade-leave-to {
  opacity: 0;
}

.dog-collapse-enter-active,
.dog-collapse-leave-active {
  transition: opacity 0.15s ease, max-height 0.25s ease;
  overflow: hidden;
}
.dog-collapse-enter-from,
.dog-collapse-leave-to {
  opacity: 0;
  max-height: 0;
}
.dog-collapse-enter-to,
.dog-collapse-leave-from {
  max-height: 2000px;
}

/* ═══ Show-wide results (Dogs tab) ═══ */
.dog-detail-tabs {
  margin-top: 0.5rem;
}
.dog-breed-group-section {
  background: var(--dog-surface-el);
  border: 1px solid var(--dog-border);
  border-radius: 0.75rem;
  padding: 1rem;
  margin-bottom: 1.5rem;
}
.dog-breed-group-header-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  background: none;
  border: none;
  font-family: inherit;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--dog-text);
  cursor: pointer;
  padding: 0.25rem 0 0.75rem 0;
  text-align: left;
}
.dog-breed-group-header-btn:hover .dog-breed-group-title {
  color: var(--dog-accent);
}
.dog-breed-group-title {
  flex: 1;
  transition: color 0.15s;
}
.dog-breed-group-badge {
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--dog-text-muted);
  background: var(--dog-surface);
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--dog-border);
}
.dog-arrow-sm {
  width: 1rem;
  height: 1rem;
  color: var(--dog-text-muted);
  transition: transform 0.15s;
}
.dog-breed-group-header-btn:hover .dog-arrow-sm {
  transform: translateX(2px);
  color: var(--dog-accent);
}
.dog-class-badge-inline,
.dog-gender-badge-inline {
  font-size: 0.75rem;
  font-weight: 500;
  background: var(--dog-surface-el);
  color: var(--dog-text-muted);
  padding: 0.15rem 0.45rem;
  border-radius: 0.25rem;
}
.dog-gender-badge-inline {
  background: none;
  border: 1px solid var(--dog-border);
  font-size: 0.8rem;
}

/* ═══ Responsive ═══ */
@media (min-width: 640px) {
  .dog-page {
    padding: 1.5rem 2rem;
  }
  .dog-title {
    font-size: 2rem;
  }
  .dog-result-top {
    flex-wrap: nowrap;
  }
}
</style>
