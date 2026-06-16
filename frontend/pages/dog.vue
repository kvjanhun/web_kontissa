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

// Breed list search query (within show detail view)
const breedSearchQuery = ref('')

// Breed results filters (within results view)
const dogSearchQuery = ref('')
const dogGradeFilter = ref('')
const dogClassFilter = ref('')
const dogAwardFilter = ref('')

// ─── Show-wide all-dogs results state (Show detail view) ─────
const allDogsLoading = ref(false)
const allDogsLoaded = ref(false)
const allDogsError = ref('')
const allDogsResults = ref([])
const allDogsProgress = ref(null)

function startShowWideSearch() {
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


const showSearchPlaceholder = computed(() => (
  allDogsLoaded.value
    ? 'Hae rotua, tuomaria tai koiraa...'
    : 'Hae rotua tai tuomaria...'
))

function searchTextMatches(value, query) {
  return String(value || '').toLowerCase().includes(query)
}

function breedMatchesSearch(breed, query) {
  if (!query) return true
  return searchTextMatches(breed?.name, query) || searchTextMatches(breed?.judge, query)
}

function dogMatchesShowSearch(dog, query) {
  if (!query) return true
  return (
    searchTextMatches(dog?.name, query) ||
    searchTextMatches(dog?.number, query) ||
    searchTextMatches(dog?.breedName, query) ||
    searchTextMatches(dog?.class_name, query) ||
    searchTextMatches(dog?.awards, query) ||
    searchTextMatches(dog?.breedObj?.judge, query)
  )
}

function dogMatchesShowFilters(dog) {
  const grade = dogGradeFilter.value.toLowerCase().trim()
  if (grade && !gradeMatchesFilter(dog.grade, grade)) return false

  const cls = dogClassFilter.value.toLowerCase().trim()
  if (cls && (dog.class_name || '').toLowerCase() !== cls) return false

  const award = dogAwardFilter.value.toLowerCase().trim()
  if (award && !(dog.awards || '').toLowerCase().includes(award)) return false

  return true
}

const allDogsAfterShowFilters = computed(() => {
  if (!allDogsLoaded.value) return []
  return allDogsResults.value.filter(dogMatchesShowFilters)
})

const showWideFiltersActive = computed(() => (
  allDogsLoaded.value && Boolean(
    breedSearchQuery.value.trim() ||
    dogGradeFilter.value ||
    dogClassFilter.value ||
    dogAwardFilter.value
  )
))

const showBreedGroups = computed(() => {
  const breeds = showDetail.value?.breeds || []
  const q = breedSearchQuery.value.toLowerCase().trim()
  const dogsByBreed = {}
  for (const dog of allDogsAfterShowFilters.value) {
    const key = dogBreedGroupKey(dog)
    if (!dogsByBreed[key]) dogsByBreed[key] = []
    dogsByBreed[key].push(dog)
  }

  const groups = {}
  for (const breed of breeds) {
    const key = breedGroupKey(breed)
    const dogs = dogsByBreed[key] || []
    const breedMatch = breedMatchesSearch(breed, q)
    const matchingDogs = q ? dogs.filter(dog => dogMatchesShowSearch(dog, q)) : dogs
    const hasResultFilters = Boolean(dogGradeFilter.value || dogClassFilter.value || dogAwardFilter.value)

    if (q || hasResultFilters) {
      if (allDogsLoaded.value) {
        if (!breedMatch && !matchingDogs.length) continue
        if (hasResultFilters && !dogs.length) continue
      } else if (!breedMatch) {
        continue
      }
    }

    groups[key] = {
      key,
      breed,
      breedName: breed.name,
      count: breed.count,
      judge: breed.judge,
      has_results: breed.has_results,
      dogs: breedMatch ? dogs : matchingDogs,
    }
  }

  for (const dog of allDogsAfterShowFilters.value) {
    const key = dogBreedGroupKey(dog)
    if (groups[key]) continue
    const breed = dog.breedObj || {}
    const dogs = dogsByBreed[key] || []
    const matchingDogs = q ? dogs.filter(item => dogMatchesShowSearch(item, q)) : dogs
    if (q && !matchingDogs.length) continue
    groups[key] = {
      key,
      breed: { ...breed, has_results: true },
      breedName: dog.breedName || breed.name,
      count: breed.count,
      judge: breed.judge,
      has_results: true,
      dogs: matchingDogs,
    }
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
const expandedBreedGroups = ref(new Set())

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

function breedGroupKeyFromParts(group, breedId, fallback = '') {
  if (group && breedId) return `${group}:${breedId}`
  return fallback
}

function breedGroupKey(breed) {
  return breedGroupKeyFromParts(breed?.group, breed?.breed_id, breed?.name || '')
}

function dogBreedGroupKey(dog) {
  const breedObj = dog?.breedObj || {}
  return breedGroupKeyFromParts(
    dog?.breedGroup || breedObj.group,
    dog?.breedId || breedObj.breed_id,
    dog?.breedName || breedObj.name || '',
  )
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

function formatShowDay(dateStr) {
  const match = String(dateStr || '').match(/\d{1,2}/)
  if (!match) return dateStr || ''
  return String(parseInt(match[0], 10))
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
  expandedBreedGroups.value = new Set()
  breedSearchQuery.value = ''
  dogSearchQuery.value = ''
  dogGradeFilter.value = ''
  dogClassFilter.value = ''
  dogAwardFilter.value = ''
  
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
  
  clearAllDogsPoll()
  allDogsLoading.value = false
  allDogsLoaded.value = false
  allDogsError.value = ''
  allDogsResults.value = []
  allDogsProgress.value = null
  expandedBreedGroups.value = new Set()
  
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

function onBreedGroupClick(group) {
  if (allDogsLoaded.value && group.dogs.length) {
    toggleBreedGroup(group.key)
    return
  }
  openBreed(group.breed)
}

function isBreedGroupExpanded(group) {
  return (
    Boolean(allDogsLoaded.value && group.dogs.length) &&
    (expandedBreedGroups.value.has(group.key) || showWideFiltersActive.value)
  )
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

function toggleBreedGroup(key) {
  const s = new Set(expandedBreedGroups.value)
  if (s.has(key)) s.delete(key)
  else s.add(key)
  expandedBreedGroups.value = s
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

const breedEmptyText = computed(() => (
  breedSearchQuery.value.trim() || dogGradeFilter.value || dogClassFilter.value || dogAwardFilter.value
    ? 'Ei rotuja tai tuloksia valituilla rajauksilla.'
    : 'Ei rotuja.'
))

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
        <!-- Detail view: back to list -->
        <button v-if="currentView === 'detail'" class="dog-back-link" aria-label="Näyttelyt" @click="goToList">
          <svg class="dog-back-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="160 208 80 128 160 48" />
          </svg>
          <span>Näyttelyt</span>
        </button>
        <!-- Results view: back to detail -->
        <button v-else-if="currentView === 'results'" class="dog-back-link" aria-label="Näyttely" @click="goToDetail">
          <svg class="dog-back-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
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
          <span v-if="searchLoading" class="dog-search-spinner" aria-hidden="true" />
        </div>

        <p v-if="indexedSearchActive && indexWarming" class="dog-status-note">
          Haku päivittyy: {{ indexStats.indexed_show_count }}/{{ indexStats.total_show_count }} näyttelyä.
        </p>
        <p v-else-if="indexedSearchActive && indexStats?.last_updated_iso" class="dog-status-note">
          Haku päivitetty {{ formatTimestamp(indexStats.last_updated_iso) }}.
        </p>

        <!-- Indexed search results -->
        <div v-if="indexedSearchActive">
          <div v-if="searchLoading" class="dog-search-loading-card" role="status" aria-live="polite">
            <div class="dog-search-loading-dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <p>Haetaan...</p>
            <div class="dog-skeleton-list">
              <div v-for="i in 4" :key="i" class="dog-skeleton-row" />
            </div>
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
                  <span class="dog-show-date">{{ formatShowDay(res.show.date) }}</span>
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
                <span class="dog-show-date">{{ formatShowDay(show.date) }}</span>
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
                    <span class="dog-show-date">{{ formatShowDay(show.date) }}</span>
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
            <svg class="dog-pill-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
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
          <div class="dog-results-filter-panel dog-show-tools-panel">
            <div
              :class="[
                'dog-results-filter-grid',
                'dog-show-tools-grid',
                allDogsLoaded && 'dog-show-tools-grid-loaded',
                allDogsLoading && 'dog-show-tools-grid-loading',
              ]"
            >
              <div class="dog-filter-col dog-show-tools-search">
                <label class="dog-filter-label">
                  {{ allDogsLoaded ? 'Rotu, tuomari tai koira' : 'Rotu tai tuomari' }}
                </label>
                <div class="dog-search-wrap dog-breed-search">
                  <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="116" cy="116" r="84" />
                    <line x1="175.4" y1="175.4" x2="224" y2="224" />
                  </svg>
                  <input
                    v-model="breedSearchQuery"
                    type="text"
                    class="dog-search-input"
                    :placeholder="showSearchPlaceholder"
                  />
                </div>
              </div>

              <div
                v-if="allDogsLoaded"
                class="dog-filter-col"
              >
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

              <div
                v-if="allDogsLoaded && availableShowClasses.length"
                class="dog-filter-col"
              >
                <label class="dog-filter-label">Luokka</label>
                <select v-model="dogClassFilter" class="dog-filter-select">
                  <option value="">Kaikki luokat</option>
                  <option v-for="c in availableShowClasses" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>

              <div
                v-if="allDogsLoaded && availableShowAwards.length"
                class="dog-filter-col"
              >
                <label class="dog-filter-label">Palkinto</label>
                <select v-model="dogAwardFilter" class="dog-filter-select">
                  <option value="">Kaikki palkinnot</option>
                  <option v-for="a in availableShowAwards" :key="a" :value="a">{{ a }}</option>
                </select>
              </div>

              <div
                v-if="!allDogsLoading && !allDogsLoaded && !allDogsError"
                class="dog-filter-col dog-show-tools-action"
              >
                <label class="dog-filter-label">Koko näyttely</label>
                <button
                  class="dog-show-wide-toggle"
                  @click="startShowWideSearch"
                >
                  <svg class="dog-toggle-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="56" y1="72" x2="200" y2="72" />
                    <circle cx="96" cy="72" r="20" />
                    <line x1="56" y1="128" x2="200" y2="128" />
                    <circle cx="152" cy="128" r="20" />
                    <line x1="56" y1="184" x2="200" y2="184" />
                    <circle cx="112" cy="184" r="20" />
                  </svg>
                  <span>Suodata koko näyttelyä</span>
                  <svg class="dog-arrow-sm" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="96 48 176 128 96 208" />
                  </svg>
                </button>
              </div>

              <div
                v-if="allDogsLoading"
                class="dog-filter-col dog-show-progress-inline"
                role="status"
                aria-live="polite"
              >
                <label class="dog-filter-label">Koko näyttely</label>
                <div class="dog-progress-inline-body">
                  <div class="dog-progress-orbit dog-progress-orbit-compact" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                  </div>
                  <div class="dog-progress-content">
                    <h2 class="dog-progress-title">Tuloksia valmistellaan</h2>
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
                      Ensimmäinen haku voi kestää, koska rotujen tulossivut haetaan taustalla rauhallisesti.
                    </p>
                  </div>
                </div>
              </div>

              <div
                v-else-if="allDogsError"
                class="dog-filter-col dog-show-progress-inline dog-show-progress-error"
              >
                <label class="dog-filter-label">Koko näyttely</label>
                <div class="dog-progress-inline-body">
                  <p class="dog-progress-copy">{{ allDogsError }}</p>
                  <button class="dog-show-retry-btn" @click="loadAllShowResults">Yritä uudelleen</button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="showBreedGroups.length" class="dog-breed-list dog-breed-group-list">
            <div
              v-for="group in showBreedGroups"
              :key="group.key"
              class="dog-breed-group-section"
            >
              <button
                :class="['dog-breed-group-header-btn', !group.has_results && !group.dogs.length && 'dog-breed-row-disabled']"
                :disabled="!group.has_results && !group.dogs.length"
                @click="onBreedGroupClick(group)"
              >
                <span class="dog-breed-group-main">
                  <span class="dog-breed-group-title">{{ group.breedName }}</span>
                  <span class="dog-breed-group-meta">
                    <span v-if="typeof group.count === 'number'">{{ group.count }} koiraa</span>
                    <span v-if="group.judge">Tuomari: {{ group.judge }}</span>
                  </span>
                </span>

                <span class="dog-breed-group-side">
                  <span
                    v-if="allDogsLoaded && group.dogs.length"
                    class="dog-breed-group-badge"
                  >
                    {{ group.dogs.length }} tulosta
                  </span>
                  <span
                    v-if="group.has_results"
                    class="dog-breed-result-icon"
                    title="Tulokset saatavilla"
                    aria-label="Tulokset saatavilla"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="128" cy="128" r="84" />
                      <polyline points="88 132 116 160 172 96" />
                    </svg>
                  </span>
                  <span
                    v-else
                    class="dog-breed-result-icon dog-breed-result-icon-muted"
                    title="Ei tuloksia"
                    aria-label="Ei tuloksia"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="128" cy="128" r="84" />
                      <line x1="88" y1="128" x2="168" y2="128" />
                    </svg>
                  </span>
                  <svg
                    v-if="allDogsLoaded && group.dogs.length"
                    :class="['dog-chevron-sm', isBreedGroupExpanded(group) && 'dog-chevron-open']"
                    xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                  >
                    <polyline points="208 96 128 176 48 96" />
                  </svg>
                  <svg
                    v-else-if="group.has_results"
                    class="dog-arrow-sm"
                    xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
                  >
                    <polyline points="96 48 176 128 96 208" />
                  </svg>
                </span>
              </button>

              <Transition name="dog-collapse">
                <div
                  v-if="isBreedGroupExpanded(group)"
                  class="dog-breed-group-dogs"
                >
                  <div class="dog-breed-group-actions">
                    <button
                      class="dog-breed-open-link"
                      @click="openBreed(group.breed)"
                    >
                      <span>Rotutulokset</span>
                      <svg class="dog-arrow-sm" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="96 48 176 128 96 208" />
                      </svg>
                    </button>
                  </div>

                  <div class="dog-results-grid">
                    <div
                      v-for="dog in group.dogs"
                      :key="`${group.key}-${dog.number || dog.name}`"
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

                      <button
                        v-if="dog.critique"
                        class="dog-critique-toggle"
                        @click="toggleCritique(`all-${group.key}-${dog.number || dog.name}`)"
                      >
                        <svg class="dog-critique-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                          <rect x="40" y="32" width="176" height="192" rx="16" />
                          <line x1="80" y1="80" x2="176" y2="80" />
                          <line x1="80" y1="128" x2="176" y2="128" />
                          <line x1="80" y1="176" x2="136" y2="176" />
                        </svg>
                        <span>{{ expandedCritiques.has(`all-${group.key}-${dog.number || dog.name}`) ? 'Piilota arvostelu' : 'Näytä arvostelu' }}</span>
                        <svg
                          :class="['dog-chevron-sm', expandedCritiques.has(`all-${group.key}-${dog.number || dog.name}`) && 'dog-chevron-open']"
                          xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                        >
                          <polyline points="208 96 128 176 48 96" />
                        </svg>
                      </button>
                      <Transition name="dog-collapse">
                        <div v-if="expandedCritiques.has(`all-${group.key}-${dog.number || dog.name}`)" class="dog-critique-text">
                          {{ dog.critique }}
                        </div>
                      </Transition>
                    </div>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
          <div v-else class="dog-empty">
            <p>{{ breedEmptyText }}</p>
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
            <svg class="dog-pill-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
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
  --dog-bg: #edf5ef;
  --dog-surface: #fffdfb;
  --dog-surface-el: #dfece5;
  --dog-accent: #11624f;
  --dog-accent-2: #9b365d;
  --dog-accent-3: #b47a12;
  --dog-text: #16231f;
  --dog-text-muted: #5d6a64;
  --dog-border: #c9d8d0;
  --dog-border-strong: #9fb7ac;
  --dog-icon: #0f4f41;
  --dog-icon-muted: #49675d;
  --dog-day-bg: #123d36;
  --dog-day-text: #f8fff9;
  --dog-gold: #b47a12;
  --dog-silver: #566979;
  --dog-bronze: #9a5e2c;
  --dog-info: #2563eb;
  --dog-radius-sm: 0.375rem;
  --dog-radius-md: 0.5rem;
  --dog-radius-lg: 0.75rem;
  --color-accent: var(--dog-accent-2);

  --dog-page-bg: var(--dog-bg);
  --dog-panel-bg: var(--dog-surface);
  --dog-panel-bg-soft: var(--dog-surface-el);
  --dog-row-bg: var(--dog-surface);
  --dog-row-hover-bg: color-mix(in srgb, var(--dog-accent) 7%, var(--dog-surface));
  --dog-control-bg: var(--dog-surface);
  --dog-pill-bg: color-mix(in srgb, var(--dog-accent) 10%, var(--dog-surface));
  --dog-control-highlight: rgba(17, 98, 79, 0.08);

  --dog-shadow-soft: 0 10px 28px -20px rgba(19, 55, 47, 0.34), 0 1px 0 rgba(255, 255, 255, 0.64);
  --dog-shadow-row: 0 16px 30px -22px rgba(19, 55, 47, 0.48), 0 2px 8px -6px rgba(19, 55, 47, 0.28);

  font-family: 'DM Sans', sans-serif;
  font-weight: 400;
  color: var(--dog-text);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--dog-bg) 82%, var(--dog-accent) 18%) 0, var(--dog-bg) 18rem),
    var(--dog-page-bg);
  min-height: 100dvh;
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem;
  padding-bottom: 4rem;
  transition: background-color 0.3s ease, color 0.3s ease;
}

:where(.dark) .dog-page {
  --dog-bg: #0f1714;
  --dog-surface: #16211d;
  --dog-surface-el: #22342d;
  --dog-accent: #73e0c0;
  --dog-accent-2: #ff9abd;
  --dog-accent-3: #f1c56a;
  --dog-text: #eff7f3;
  --dog-text-muted: #a7b9b0;
  --dog-border: #314b42;
  --dog-border-strong: #4e6d61;
  --dog-icon: #a6f4da;
  --dog-icon-muted: #c4d7ce;
  --dog-day-bg: #c7f7e6;
  --dog-day-text: #0c241e;
  --dog-gold: #f1c56a;
  --dog-silver: #bdd1dc;
  --dog-bronze: #d59a61;
  --dog-info: #8ec5ff;

  --dog-row-hover-bg: color-mix(in srgb, var(--dog-accent) 10%, var(--dog-surface));
  --dog-pill-bg: color-mix(in srgb, var(--dog-accent) 12%, var(--dog-surface));
  --dog-control-highlight: rgba(255, 255, 255, 0.05);

  --dog-shadow-soft: 0 18px 34px -26px rgba(0, 0, 0, 0.82), 0 1px 0 rgba(255, 255, 255, 0.05);
  --dog-shadow-row: 0 18px 34px -24px rgba(0, 0, 0, 0.9), 0 4px 12px -10px rgba(0, 0, 0, 0.9);
}

.dog-page svg :is(path, polyline, line, rect, circle) {
  stroke-width: inherit;
  vector-effect: non-scaling-stroke;
}

/* ═══ Top bar / Header ═══ */
.dog-top-bar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  background: color-mix(in srgb, var(--dog-surface) 84%, var(--dog-accent) 16%);
  border: 1px solid var(--dog-border);
  border-radius: var(--dog-radius-lg);
  box-shadow: var(--dog-shadow-soft);
  min-height: 64px;
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
  overflow: hidden;
  padding: 0 0.35rem;
}
.dog-top-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--dog-accent);
  margin: 0;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
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
.dog-top-right :deep(button) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.375rem;
  height: 2.375rem;
  padding: 0;
  background: var(--dog-surface);
  border: 1px solid var(--dog-border-strong);
  border-radius: 999px;
  box-shadow: inset 0 1px 0 var(--dog-control-highlight);
}
.dog-top-right :deep(button:hover) {
  opacity: 1;
  background: var(--dog-row-hover-bg);
  border-color: var(--dog-accent-2);
}
.dog-top-right :deep(svg) {
  width: 1.15rem;
  height: 1.15rem;
  stroke-width: 2.05px;
}
.dog-back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.9rem;
  color: var(--dog-accent);
  text-decoration: none;
  background: var(--dog-surface);
  border: 1px solid var(--dog-border-strong);
  border-radius: 999px;
  font-family: inherit;
  font-weight: 700;
  cursor: pointer;
  padding: 0 0.85rem;
  min-height: 38px;
  transition: background-color 0.15s, border-color 0.15s, color 0.15s;
  white-space: nowrap;
  max-width: 100%;
  min-width: 0;
}
.dog-back-link span {
  overflow: hidden;
  text-overflow: ellipsis;
}
.dog-back-link:hover {
  background: var(--dog-row-hover-bg);
  border-color: var(--dog-accent);
  color: var(--dog-accent-2);
}
.dog-back-icon {
  width: 1rem;
  height: 1rem;
  color: var(--dog-accent-2);
  stroke-width: 2px;
  transition: transform 0.15s;
}
.dog-back-link:hover .dog-back-icon {
  transform: translateX(-3px);
}
@media (max-width: 520px) {
  .dog-back-link {
    width: 2.375rem;
    padding: 0;
    justify-content: center;
  }
  .dog-back-link span {
    display: none;
  }
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
  background: var(--dog-pill-bg);
  border: 1px solid var(--dog-border);
  color: var(--dog-text);
}
.dog-source-link-pill {
  color: var(--dog-accent);
  text-decoration: none;
  font-weight: 700;
  transition: background-color 0.15s, border-color 0.15s;
}
.dog-source-link-pill:hover {
  background: var(--dog-row-hover-bg);
  border-color: var(--dog-accent);
}
.dog-judge-pill strong {
  color: var(--dog-text);
  font-weight: 500;
}
.dog-pill-icon {
  width: 0.875rem;
  height: 0.875rem;
  color: var(--dog-icon);
  stroke-width: 1.9px;
  flex-shrink: 0;
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
  color: var(--dog-icon-muted);
  stroke-width: 1.85px;
  pointer-events: none;
}
.dog-search-wrap:focus-within .dog-search-icon {
  color: var(--dog-icon);
}
.dog-search-input {
  width: 100%;
  padding: 0.75rem 2.65rem 0.75rem 2.5rem;
  background: var(--dog-control-bg);
  border: 1px solid var(--dog-border-strong);
  border-radius: var(--dog-radius-md);
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 400;
  outline: none;
  box-shadow: var(--dog-shadow-soft);
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
  min-height: 44px;
}
.dog-search-input::placeholder {
  color: var(--dog-text-muted);
}
.dog-search-input:focus {
  border-color: var(--dog-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--dog-accent) 16%, transparent), var(--dog-shadow-row);
}
.dog-search-spinner {
  position: absolute;
  right: 0.95rem;
  top: 50%;
  width: 1rem;
  height: 1rem;
  border: 2px solid color-mix(in srgb, var(--dog-accent) 22%, transparent);
  border-top-color: var(--dog-accent);
  border-radius: 999px;
  transform: translateY(-50%);
  animation: dog-search-spin 0.75s linear infinite;
  pointer-events: none;
}
.dog-search-loading-card {
  padding: 0.9rem;
  margin-bottom: 1rem;
  background: var(--dog-panel-bg);
  border: 1px solid var(--dog-border);
  border-radius: var(--dog-radius-md);
  box-shadow: var(--dog-shadow-soft);
}
.dog-search-loading-card p {
  margin: 0 0 0.85rem;
  color: var(--dog-text-muted);
  font-size: 0.85rem;
}
.dog-search-loading-dots {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-bottom: 0.45rem;
}
.dog-search-loading-dots span {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 999px;
  background: var(--dog-accent);
  animation: dog-search-dot 1s ease-in-out infinite;
}
.dog-search-loading-dots span:nth-child(2) {
  animation-delay: 0.14s;
}
.dog-search-loading-dots span:nth-child(3) {
  animation-delay: 0.28s;
}
.dog-status-note {
  margin: -0.85rem 0 1.5rem;
  color: var(--dog-text-muted);
  font-size: 0.8rem;
}

/* ═══ Featured: Tällä viikolla ═══ */
.dog-this-week-section {
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--dog-panel-bg) 86%, var(--dog-accent) 14%), color-mix(in srgb, var(--dog-panel-bg) 90%, var(--dog-accent-2) 10%));
  border: 1px solid var(--dog-border-strong);
  border-radius: var(--dog-radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--dog-shadow-soft);
}
.dog-this-week-heading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--dog-accent);
  margin: 0 0 1rem 0;
}
.dog-heading-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: var(--dog-accent-2);
  stroke-width: 1.9px;
}
.dog-this-week-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.dog-show-row-featured {
  background: var(--dog-row-bg);
  border-radius: var(--dog-radius-sm);
  border-color: color-mix(in srgb, var(--dog-accent) 34%, var(--dog-border));
}
.dog-show-row-featured:hover {
  background: var(--dog-row-hover-bg);
}

/* ═══ Skeleton ═══ */
.dog-skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.dog-skeleton-row {
  height: 3rem;
  background:
    linear-gradient(90deg, transparent, color-mix(in srgb, var(--dog-accent) 10%, transparent), transparent),
    var(--dog-row-bg);
  border: 1px solid color-mix(in srgb, var(--dog-border) 70%, transparent);
  border-radius: var(--dog-radius-sm);
  animation: dog-pulse 1.5s ease-in-out infinite;
}
.dog-skeleton-tall {
  height: 5rem;
}
@keyframes dog-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}
@keyframes dog-search-spin {
  to { transform: translateY(-50%) rotate(360deg); }
}
@keyframes dog-search-dot {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.45; }
  40% { transform: translateY(-0.22rem); opacity: 1; }
}

/* ═══ Whole-show result cache progress ═══ */
.dog-show-progress-inline {
  min-width: 0;
}
.dog-progress-inline-body {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  min-height: 44px;
  padding: 0.7rem 0.75rem;
  background: var(--dog-control-bg);
  border: 1px solid var(--dog-border-strong);
  border-radius: var(--dog-radius-md);
  box-shadow: inset 0 1px 0 var(--dog-control-highlight);
}
.dog-show-progress-error .dog-progress-inline-body {
  align-items: center;
  justify-content: space-between;
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
.dog-progress-orbit-compact {
  width: 2rem;
  height: 2rem;
  margin-top: 0.15rem;
}
.dog-progress-orbit span {
  position: absolute;
  width: 0.55rem;
  height: 0.55rem;
  background: var(--dog-accent);
  border-radius: 999px;
}
.dog-progress-orbit-compact span {
  width: 0.42rem;
  height: 0.42rem;
}
.dog-progress-orbit span:nth-child(1) {
  top: -0.3rem;
  left: 50%;
  transform: translateX(-50%);
}
.dog-progress-orbit-compact span:nth-child(1) {
  top: -0.22rem;
}
.dog-progress-orbit span:nth-child(2) {
  right: 0.2rem;
  bottom: 0.35rem;
  opacity: 0.75;
}
.dog-progress-orbit-compact span:nth-child(2) {
  right: 0.1rem;
  bottom: 0.22rem;
}
.dog-progress-orbit span:nth-child(3) {
  left: 0.2rem;
  bottom: 0.35rem;
  opacity: 0.45;
}
.dog-progress-orbit-compact span:nth-child(3) {
  left: 0.1rem;
  bottom: 0.22rem;
}
.dog-progress-content {
  min-width: 0;
  flex: 1;
}
.dog-progress-title {
  margin: 0 0 0.25rem;
  color: var(--dog-text);
  font-size: 0.9rem;
  font-weight: 700;
}
.dog-progress-copy,
.dog-progress-note {
  margin: 0;
  color: var(--dog-text-muted);
  font-size: 0.8rem;
}
.dog-progress-track {
  position: relative;
  height: 0.4rem;
  margin: 0.55rem 0 0.4rem;
  background: color-mix(in srgb, var(--dog-surface-el) 80%, var(--dog-text-muted));
  border-radius: 999px;
  overflow: hidden;
}
.dog-progress-fill {
  display: block;
  width: 0;
  height: 100%;
  background: var(--dog-accent);
  border-radius: inherit;
  transition: width 0.3s ease;
}
.dog-progress-track-indeterminate .dog-progress-fill {
  width: 38%;
  animation: dog-progress-slide 1.6s ease-in-out infinite;
}
.dog-show-retry-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 0.75rem;
  background: var(--dog-accent);
  border: 1px solid var(--dog-accent);
  border-radius: 999px;
  color: #ffffff;
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
}
@keyframes dog-orbit-spin {
  to { transform: rotate(360deg); }
}
@keyframes dog-progress-slide {
  0% { transform: translateX(-110%); }
  100% { transform: translateX(290%); }
}
@media (prefers-reduced-motion: reduce) {
  .dog-search-spinner,
  .dog-search-loading-dots span,
  .dog-skeleton-row,
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
  color: #ffffff;
  border: 1px solid var(--dog-accent-2);
  border-radius: var(--dog-radius-sm);
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--dog-shadow-soft);
  transition: opacity 0.15s, transform 0.15s;
  min-height: 44px;
}
.dog-btn:hover {
  opacity: 0.85;
  transform: translateY(-1px);
}

/* ═══ Empty ═══ */
.dog-empty {
  text-align: center;
  padding: 2rem;
  color: var(--dog-text-muted);
  background: var(--dog-panel-bg-soft);
  border: 1px solid var(--dog-border);
  border-radius: var(--dog-radius-md);
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
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--dog-panel-bg-soft) 88%, var(--dog-accent) 12%), color-mix(in srgb, var(--dog-panel-bg-soft) 92%, var(--dog-accent-2) 8%));
  border: 1px solid var(--dog-border-strong);
  border-radius: var(--dog-radius-md);
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  gap: 0.5rem;
  min-height: 44px;
  transition: background 0.15s, border-color 0.15s;
}
.dog-month-header:hover {
  background: var(--dog-row-hover-bg);
  border-color: var(--dog-accent);
}
.dog-month-label {
  flex: 1;
  text-align: left;
  color: var(--dog-accent);
  font-weight: 800;
}
.dog-month-count {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--dog-accent-2);
  background: color-mix(in srgb, var(--dog-accent-2) 10%, var(--dog-surface));
  border: 1px solid color-mix(in srgb, var(--dog-accent-2) 32%, var(--dog-border));
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}
.dog-chevron {
  width: 1.25rem;
  height: 1.25rem;
  transition: transform 0.2s, color 0.15s, opacity 0.15s;
  transform: rotate(-90deg);
  color: var(--dog-accent-2);
  stroke-width: 2.15px;
  opacity: 1;
  flex-shrink: 0;
}
.dog-chevron-open {
  transform: rotate(0deg);
}
.dog-month-header:hover .dog-chevron {
  color: var(--dog-accent-2);
  opacity: 1;
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
  background: var(--dog-row-bg);
  border: 1px solid var(--dog-border);
  border-radius: var(--dog-radius-sm);
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 400;
  cursor: pointer;
  text-align: left;
  gap: 0.75rem;
  min-height: 44px;
  transition: background 0.12s, border-color 0.12s, box-shadow 0.12s, transform 0.12s;
}
.dog-show-row:hover {
  background: var(--dog-row-hover-bg);
  border-color: var(--dog-accent);
  box-shadow: var(--dog-shadow-row);
  transform: translateY(-1px);
}
.dog-show-date {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.65rem;
  font-family: inherit;
  font-size: 1.05rem;
  line-height: 1;
  color: var(--dog-day-text);
  background:
    linear-gradient(145deg, color-mix(in srgb, var(--dog-day-bg) 88%, var(--dog-accent-3) 12%), var(--dog-day-bg));
  border: 1px solid color-mix(in srgb, var(--dog-day-bg) 52%, var(--dog-border));
  box-shadow: inset 0 1px 0 color-mix(in srgb, #ffffff 20%, transparent), 0 8px 16px -14px var(--dog-day-bg);
  font-weight: 800;
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
  border: 1px solid var(--dog-border-strong);
  border-radius: 999px;
  padding: 0.15rem 0.45rem;
  background: var(--dog-surface-el);
  color: var(--dog-text);
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1.2;
}
.dog-show-stat-soft {
  color: var(--dog-accent-2);
  border-color: color-mix(in srgb, var(--dog-accent-2) 30%, var(--dog-border));
  background: color-mix(in srgb, var(--dog-accent-2) 8%, var(--dog-surface-el));
}
.dog-show-stat-live {
  color: #ffffff;
  border-color: var(--dog-accent-2);
  background: var(--dog-accent-2);
  font-weight: 600;
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
  font-weight: 700;
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
  color: var(--dog-accent-2);
  stroke-width: 2.15px;
  opacity: 1;
  flex-shrink: 0;
  transition: color 0.15s, transform 0.15s, opacity 0.15s;
}
.dog-show-row:hover .dog-arrow {
  color: var(--dog-accent-2);
  opacity: 1;
  transform: translateX(3px);
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
.dog-show-tools-panel {
  background: color-mix(in srgb, var(--dog-panel-bg) 90%, var(--dog-accent) 10%);
}
.dog-results-filter-grid.dog-show-tools-grid {
  align-items: end;
  grid-template-columns: 1fr;
}
@media (min-width: 640px) {
  .dog-results-filter-grid.dog-show-tools-grid {
    grid-template-columns: minmax(0, 1fr) minmax(16rem, 24rem);
  }
  .dog-results-filter-grid.dog-show-tools-grid-loading {
    grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
  }
  .dog-results-filter-grid.dog-show-tools-grid-loaded {
    grid-template-columns:
      minmax(0, 2.2fr)
      minmax(0, 0.8fr)
      minmax(0, 0.8fr)
      minmax(0, 0.85fr);
  }
}
.dog-breed-search {
  margin-bottom: 0;
}
.dog-show-wide-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0 1rem;
  min-height: 44px;
  background: var(--dog-control-bg);
  border: 1px solid var(--dog-border-strong);
  border-radius: var(--dog-radius-md);
  color: var(--dog-accent-2);
  font-family: inherit;
  font-size: 0.88rem;
  font-weight: 800;
  cursor: pointer;
  width: 100%;
  white-space: nowrap;
  box-shadow: inset 0 1px 0 var(--dog-control-highlight);
  transition: background 0.15s, border-color 0.15s, color 0.15s, transform 0.15s;
}
.dog-show-wide-toggle:hover {
  background: color-mix(in srgb, var(--dog-accent-2) 10%, var(--dog-surface));
  border-color: var(--dog-accent-2);
  transform: translateY(-1px);
}
.dog-toggle-icon {
  width: 1rem;
  height: 1rem;
  color: var(--dog-accent-2);
  stroke-width: 2px;
  flex-shrink: 0;
}
.dog-breed-list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.dog-breed-row-disabled {
  cursor: default;
  opacity: 0.5;
}

/* ═══ Filter Panel (results view) ═══ */
.dog-results-filter-panel {
  background: var(--dog-panel-bg);
  border: 1px solid var(--dog-border);
  border-radius: var(--dog-radius-lg);
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--dog-shadow-soft);
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
  min-width: 0;
}
.dog-filter-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--dog-text-muted);
  text-transform: uppercase;
  letter-spacing: 0;
}
.dog-filter-select {
  width: 100%;
  min-width: 0;
  padding: 0.5rem 0.75rem;
  background: var(--dog-control-bg);
  border: 1px solid var(--dog-border);
  border-radius: var(--dog-radius-sm);
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.85rem;
  outline: none;
  min-height: 38px;
  cursor: pointer;
  box-sizing: border-box;
  box-shadow: inset 0 1px 0 var(--dog-control-highlight);
}
.dog-filter-select:focus {
  border-color: var(--dog-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--dog-accent) 15%, transparent);
}
.dog-filter-search {
  margin-bottom: 0;
}
.dog-filter-search .dog-search-input {
  padding: 0.5rem 0.75rem 0.5rem 2.25rem;
  font-size: 0.85rem;
  min-height: 38px;
  background: var(--dog-control-bg);
  box-shadow: none;
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
  background: var(--dog-surface);
  border: 1px solid var(--dog-border);
  border-radius: var(--dog-radius-sm);
  min-width: 100px;
}
.dog-award-type {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--dog-accent-2);
  text-transform: uppercase;
  letter-spacing: 0;
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
  color: var(--dog-accent-2);
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
  background: var(--dog-pill-bg);
  color: var(--dog-text-muted);
  padding: 0.15rem 0.45rem;
  border: 1px solid var(--dog-border);
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0;
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
  background: var(--dog-row-bg);
  border: 1px solid var(--dog-border);
  border-radius: var(--dog-radius-md);
  overflow: hidden;
  box-shadow: var(--dog-shadow-soft);
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.dog-result-card:hover {
  background: var(--dog-row-hover-bg);
  border-color: var(--dog-accent);
  box-shadow: var(--dog-shadow-row);
  transform: translateY(-1px);
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
  background: var(--dog-pill-bg);
  padding: 0.1rem 0.4rem;
  border: 1px solid var(--dog-border);
  border-radius: 999px;
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
  font-weight: 700;
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
  color: var(--dog-icon);
  opacity: 1;
  stroke-width: 1.85px;
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
  letter-spacing: 0;
}
.dog-badge-gold {
  background: color-mix(in srgb, var(--dog-gold) 12%, var(--dog-surface));
  color: var(--dog-gold);
  border: 1px solid color-mix(in srgb, var(--dog-gold) 30%, var(--dog-border));
}
.dog-badge-silver {
  background: color-mix(in srgb, var(--dog-silver) 12%, var(--dog-surface));
  color: var(--dog-silver);
  border: 1px solid color-mix(in srgb, var(--dog-silver) 30%, var(--dog-border));
}
.dog-badge-bronze {
  background: color-mix(in srgb, var(--dog-bronze) 12%, var(--dog-surface));
  color: var(--dog-bronze);
  border: 1px solid color-mix(in srgb, var(--dog-bronze) 30%, var(--dog-border));
}
.dog-badge-info {
  background: color-mix(in srgb, var(--dog-info) 12%, var(--dog-surface));
  color: var(--dog-info);
  border: 1px solid color-mix(in srgb, var(--dog-info) 30%, var(--dog-border));
}
.dog-badge-muted {
  background: color-mix(in srgb, var(--dog-text-muted) 10%, var(--dog-surface));
  color: var(--dog-text-muted);
  border: 1px solid color-mix(in srgb, var(--dog-text-muted) 20%, var(--dog-border));
}
.dog-badge-default {
  background: var(--dog-pill-bg);
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
  background: color-mix(in srgb, var(--dog-accent-2) 12%, var(--dog-surface));
  color: var(--dog-accent-2);
  border: 1px solid color-mix(in srgb, var(--dog-accent-2) 30%, var(--dog-border));
}

/* ═══ Critique ═══ */
.dog-critique-toggle {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  width: 100%;
  padding: 0.6rem 1.25rem;
  background: color-mix(in srgb, var(--dog-surface-el) 30%, transparent);
  border: none;
  border-top: 1px solid var(--dog-border);
  color: var(--dog-text-muted);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 400;
  cursor: pointer;
  min-height: 44px;
  transition: background-color 0.12s, color 0.12s;
}
.dog-critique-toggle:hover {
  background: color-mix(in srgb, var(--dog-accent) 8%, var(--dog-surface-el));
  color: var(--dog-text);
}
.dog-critique-icon {
  width: 0.9rem;
  height: 0.9rem;
  color: var(--dog-icon);
  stroke-width: 1.9px;
}
.dog-chevron-sm {
  width: 1rem;
  height: 1rem;
  color: var(--dog-accent-2);
  stroke-width: 2.15px;
  transition: transform 0.2s, color 0.15s;
  transform: rotate(-90deg);
  flex-shrink: 0;
  margin-left: auto;
}
.dog-critique-toggle:hover .dog-chevron-sm {
  color: var(--dog-accent-2);
}
.dog-critique-text {
  padding: 0.85rem 1.25rem;
  font-size: 0.85rem;
  font-weight: 400;
  line-height: 1.6;
  color: var(--dog-text-muted);
  background: color-mix(in srgb, var(--dog-surface-el) 30%, var(--dog-surface));
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

/* ═══ Show-wide results ═══ */
.dog-breed-group-list {
  gap: 0.55rem;
}
.dog-breed-group-section {
  background: var(--dog-panel-bg);
  border: 1px solid var(--dog-border);
  border-radius: var(--dog-radius-md);
  padding: 0;
  margin-bottom: 0;
  box-shadow: var(--dog-shadow-soft);
  overflow: hidden;
}
.dog-breed-group-header-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  background: var(--dog-row-bg);
  border: none;
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--dog-text);
  cursor: pointer;
  padding: 0.85rem 1rem;
  text-align: left;
  min-height: 64px;
  transition: background 0.12s, color 0.12s;
}
.dog-breed-group-header-btn:hover:not(:disabled) {
  background: var(--dog-row-hover-bg);
}
.dog-breed-group-header-btn:hover:not(:disabled) .dog-breed-group-title {
  color: var(--dog-accent);
}
.dog-breed-group-main {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
  flex: 1;
}
.dog-breed-group-title {
  font-weight: 700;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.15s;
}
.dog-breed-group-meta {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem 0.7rem;
  color: var(--dog-text-muted);
  font-size: 0.78rem;
}
.dog-breed-group-side {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  flex-shrink: 0;
}
.dog-breed-group-badge {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--dog-accent-2);
  background: var(--dog-pill-bg);
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--dog-border);
}
.dog-breed-result-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  color: var(--dog-accent);
  flex-shrink: 0;
}
.dog-breed-result-icon svg {
  width: 100%;
  height: 100%;
}
.dog-breed-result-icon-muted {
  color: var(--dog-text-muted);
  opacity: 0.58;
}
.dog-breed-group-dogs {
  border-top: 1px solid var(--dog-border);
  padding: 0.75rem 1rem 1rem;
  background: color-mix(in srgb, var(--dog-panel-bg) 94%, var(--dog-accent) 6%);
}
.dog-breed-group-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.75rem;
}
.dog-breed-open-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-height: 34px;
  padding: 0 0.75rem;
  background: var(--dog-control-bg);
  border: 1px solid var(--dog-border);
  border-radius: 999px;
  color: var(--dog-accent);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.dog-breed-open-link:hover {
  background: var(--dog-row-hover-bg);
  border-color: var(--dog-accent);
}
.dog-arrow-sm {
  width: 1rem;
  height: 1rem;
  color: var(--dog-accent-2);
  opacity: 1;
  stroke-width: 2.15px;
  transition: transform 0.15s, color 0.15s, opacity 0.15s;
}
.dog-breed-group-header-btn:hover .dog-arrow-sm {
  transform: translateX(3px);
  color: var(--dog-accent-2);
  opacity: 1;
}
@media (max-width: 560px) {
  .dog-breed-group-header-btn {
    align-items: flex-start;
  }
  .dog-breed-group-side {
    gap: 0.35rem;
  }
  .dog-breed-group-badge {
    display: none;
  }
}
.dog-class-badge-inline,
.dog-gender-badge-inline {
  font-size: 0.75rem;
  font-weight: 500;
  background: var(--dog-pill-bg);
  color: var(--dog-text-muted);
  padding: 0.15rem 0.45rem;
  border: 1px solid var(--dog-border);
  border-radius: 999px;
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
