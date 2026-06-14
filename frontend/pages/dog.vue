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

// --- Dark mode: always on for this page ---
onMounted(() => {
  document.documentElement.classList.add('dark')
})
onUnmounted(() => {
  // Restore user preference on leave
  const saved = localStorage.getItem('theme')
  if (saved !== 'dark' && !window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.classList.remove('dark')
  }
})

// ─── View state ──────────────────────────────────────────────
// 'list' | 'detail' | 'results'
const currentView = ref('list')
const activeTab = ref('shows') // 'shows' | 'search'

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
const searchQuery = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
const searchError = ref('')
const showResultsOnly = ref(false)

// ─── Collapsible months ──────────────────────────────────────
const collapsedMonths = ref(new Set())

// ─── Expanded critiques ──────────────────────────────────────
const expandedCritiques = ref(new Set())

// ─── Debounce timer ──────────────────────────────────────────
let searchTimer = null
let indexPollTimer = null
let routeSyncToken = 0

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

function pushDogQuery(query) {
  return router.push({ path: '/dog', query: buildDogQuery(query) }).catch(() => {})
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

function resetDogSelection() {
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

function sourceForShow(show) {
  return show?.source_url || (show?.id ? `https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=${show.id}` : '')
}

async function refreshIndexStats() {
  try {
    const data = await $fetch('/api/dog/shows')
    shows.value = data.shows || shows.value
    indexStats.value = data.index || indexStats.value
    if (!indexWarming.value && indexPollTimer) {
      clearInterval(indexPollTimer)
      indexPollTimer = null
    }
  } catch {
    // Keep existing page data; this is only a background freshness check.
  }
}

function startIndexPolling() {
  if (indexPollTimer || !indexWarming.value) return
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
  detailLoading.value = true
  detailError.value = ''
  showDetail.value = null
  selectedBreed.value = null
  breedResults.value = null
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
  const q = searchQuery.value.trim()
  if (q.length < 2) {
    searchResults.value = []
    searchLoading.value = false
    return
  }
  searchLoading.value = true
  searchError.value = ''
  searchTimer = setTimeout(async () => {
    try {
      const data = await $fetch(`/api/dog/search?q=${encodeURIComponent(q)}`)
      searchResults.value = data.results || []
      indexStats.value = data.index || indexStats.value
    } catch (e) {
      searchError.value = 'Haku epäonnistui.'
    } finally {
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
    })
  }
  return pushDogQuery({ show: res.show.id })
}

// ─── Navigation ──────────────────────────────────────────────
function goToList() {
  return pushDogQuery({})
}

function goToDetail() {
  if (selectedShow.value) {
    return pushDogQuery({ show: selectedShow.value.id })
  }
}

function openShow(show) {
  if (!show?.id) return
  pushDogQuery({ show: show.id })
}

function openBreed(breed) {
  if (!breed?.has_results || !selectedShow.value?.id) return
  pushDogQuery({
    show: selectedShow.value.id,
    group: breed.group,
    breed: breed.breed_id,
  })
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

const groupedShows = computed(() => {
  const groups = {}
  for (const show of filteredShows.value) {
    const month = show.month || 'Muu'
    if (!groups[month]) groups[month] = []
    groups[month].push(show)
  }
  return groups
})

const filteredBreeds = computed(() => {
  const breeds = showDetail.value?.breeds || []
  if (!showResultsOnly.value) return breeds
  return breeds.filter(b => b.has_results)
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

const routeSelectionKey = computed(() => [
  firstQueryValue(route.query.show) || '',
  firstQueryValue(route.query.group) || '',
  firstQueryValue(route.query.breed) || '',
].join('|'))

// ─── Computed: results grouped by gender ─────────────────────
const resultsByGender = computed(() => {
  if (!breedResults.value?.results) return {}
  const groups = {}
  for (const r of breedResults.value.results) {
    const gender = r.gender || 'Muu'
    if (!groups[gender]) groups[gender] = []
    groups[gender].push(r)
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
  if (g === 'poissa' || g === 'hyl' || g === 'hylätty') return 'dog-badge-muted'
  return 'dog-badge-default'
}

async function syncRouteState() {
  const syncToken = ++routeSyncToken
  const { showId, groupId, breedId } = getRouteSelection()

  if (!showId || !isNumericString(showId)) {
    resetDogSelection()
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
  } else {
    selectedShow.value = show
    currentView.value = 'detail'
    detailLoading.value = false
    detailError.value = ''
  }

  if (!groupId || !breedId) {
    currentView.value = 'detail'
    selectedBreed.value = null
    breedResults.value = null
    resultsLoading.value = false
    resultsError.value = ''
    expandedCritiques.value = new Set()
    return
  }

  if (!isNumericString(groupId) || !isNumericString(breedId) || !showDetail.value) {
    currentView.value = 'detail'
    selectedBreed.value = null
    breedResults.value = null
    resultsLoading.value = false
    resultsError.value = ''
    expandedCritiques.value = new Set()
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
  } else {
    currentView.value = 'results'
    resultsLoading.value = false
    resultsError.value = ''
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
})
</script>

<template>
  <div class="dog-page">
    <!-- ═══ VIEW: SHOW LIST ═══ -->
    <Transition name="dog-fade" mode="out-in">
      <div v-if="currentView === 'list'" key="list">
        <!-- Header -->
        <header class="dog-header">
          <h1 class="dog-title">
            <span class="dog-title-icon">🐾</span>
            Näyttelytulokset
          </h1>
          <p class="dog-subtitle">Koiranäyttelyiden tulokset ja tilastot</p>
        </header>

        <!-- Tabs -->
        <div class="dog-tabs">
          <button
            :class="['dog-tab', activeTab === 'shows' && 'dog-tab-active']"
            @click="activeTab = 'shows'"
          >
            Näyttelyt
          </button>
          <button
            :class="['dog-tab', activeTab === 'search' && 'dog-tab-active']"
            @click="activeTab = 'search'"
          >
            Hae rotua
          </button>
        </div>

        <!-- Shows tab -->
        <div v-if="activeTab === 'shows'">
          <!-- Filter -->
          <div class="dog-search-wrap">
            <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd" />
            </svg>
            <input
              v-model="filterText"
              type="text"
              class="dog-search-input"
              placeholder="Suodata näyttelyt..."
            />
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
                  xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"
                >
                  <path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clip-rule="evenodd" />
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
                    <span class="dog-show-name">{{ show.name }}</span>
                    <svg class="dog-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
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

        <!-- Search tab -->
        <div v-if="activeTab === 'search'">
          <div class="dog-search-wrap">
            <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd" />
            </svg>
            <input
              v-model="searchQuery"
              type="text"
              class="dog-search-input"
              placeholder="Esim. basenji, villakoira..."
              @input="onSearchInput"
            />
          </div>
          <p v-if="indexWarming" class="dog-status-note">
            Rotuhaku päivittyy: {{ indexStats.indexed_show_count }}/{{ indexStats.total_show_count }} näyttelyä.
          </p>
          <p v-else-if="indexStats?.last_updated_iso" class="dog-status-note">
            Rotuhaku päivitetty {{ formatTimestamp(indexStats.last_updated_iso) }}.
          </p>

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
                <span class="dog-show-date">{{ res.show.date }}</span>
                <span class="dog-show-name">{{ res.show.name }}</span>
                <span v-if="res.breed" class="dog-search-breed-tag">
                  🐾 {{ res.breed.name }} ({{ res.breed.count }} koiraa)
                </span>
                <span v-else class="dog-search-breed-tag">Näyttely</span>
              </div>
              <svg class="dog-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>

          <div v-else-if="searchQuery.trim().length >= 2 && !searchLoading" class="dog-empty">
            <p>Ei hakutuloksia.</p>
          </div>

          <div v-else-if="searchQuery.trim().length < 2" class="dog-empty dog-empty-hint">
            <p>Kirjoita vähintään 2 merkkiä hakeaksesi.</p>
          </div>
        </div>
      </div>

      <!-- ═══ VIEW: SHOW DETAIL ═══ -->
      <div v-else-if="currentView === 'detail'" key="detail">
        <!-- Breadcrumb -->
        <nav class="dog-breadcrumb">
            <button class="dog-breadcrumb-link" @click="goToList">Näyttelyt</button>
          <span class="dog-breadcrumb-sep">›</span>
          <span class="dog-breadcrumb-current">{{ selectedShow?.name }}</span>
        </nav>

        <header class="dog-header dog-header-compact">
          <h1 class="dog-title dog-title-sm">
            {{ showDetail?.title || selectedShow?.name }}
          </h1>
          <div class="dog-meta-row">
            <a
              v-if="selectedShowSourceUrl"
              :href="selectedShowSourceUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="dog-source-link"
            >
              Showlink
            </a>
            <span v-if="showDetail?.fetched_at_iso" class="dog-updated">
              Päivitetty {{ formatTimestamp(showDetail.fetched_at_iso) }}
            </span>
          </div>
        </header>

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
          <div class="dog-filter-row">
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
                <span class="dog-breed-count">{{ breed.count }} koiraa</span>
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
      </div>

      <!-- ═══ VIEW: BREED RESULTS ═══ -->
      <div v-else-if="currentView === 'results'" key="results">
        <!-- Breadcrumb -->
        <nav class="dog-breadcrumb">
          <button class="dog-breadcrumb-link" @click="goToList">Näyttelyt</button>
          <span class="dog-breadcrumb-sep">›</span>
          <button class="dog-breadcrumb-link" @click="goToDetail">{{ selectedShow?.name }}</button>
          <span class="dog-breadcrumb-sep">›</span>
          <span class="dog-breadcrumb-current">{{ selectedBreed?.name }}</span>
        </nav>

        <header class="dog-header dog-header-compact">
          <h1 class="dog-title dog-title-sm">{{ breedResults?.breed || selectedBreed?.name }}</h1>
          <p v-if="breedResults?.judge" class="dog-judge">
            Tuomari: <strong>{{ breedResults.judge }}</strong>
          </p>
          <div class="dog-meta-row">
            <a
              v-if="selectedBreedSourceUrl"
              :href="selectedBreedSourceUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="dog-source-link"
            >
              Showlink
            </a>
            <span v-if="breedResults?.fetched_at_iso" class="dog-updated">
              Päivitetty {{ formatTimestamp(breedResults.fetched_at_iso) }}
            </span>
          </div>
        </header>

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
          <!-- Awards -->
          <div v-if="breedResults.awards?.length" class="dog-awards">
            <div
              v-for="(award, i) in breedResults.awards"
              :key="i"
              class="dog-award-card"
            >
              <span class="dog-award-type">{{ award.type }}</span>
              <span class="dog-award-text">{{ award.text }}</span>
            </div>
          </div>

          <!-- Results by gender -->
          <div v-for="(dogs, gender) in resultsByGender" :key="gender" class="dog-gender-group">
            <h2 class="dog-gender-heading">
              {{ gender === 'uros' ? 'Urokset' : gender === 'narttu' ? 'Nartut' : gender }}
            </h2>

            <!-- Group by class -->
            <div
              v-for="(dog, idx) in dogs"
              :key="idx"
              class="dog-result-card"
            >
              <!-- Class separator -->
              <div
                v-if="idx === 0 || dogs[idx - 1]?.class_name !== dog.class_name"
                class="dog-class-header"
              >
                {{ dog.class_name || 'Luokka' }}
              </div>

              <div class="dog-result-main">
                <div class="dog-result-top">
                  <span v-if="dog.number" class="dog-catalog-num">{{ dog.number }}</span>
                  <span v-if="dog.placement" class="dog-placement">{{ dog.placement }}.</span>
                  <a
                    v-if="dog.reg_url"
                    :href="dog.reg_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="dog-dog-name"
                  >
                    {{ dog.name }}
                    <svg class="dog-external" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M8.75 3.5a.75.75 0 01.75-.75h3.5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0V5.06l-4.72 4.72a.75.75 0 01-1.06-1.06L11.19 4H9.5a.75.75 0 01-.75-.75z" />
                      <path d="M3.5 5.75c0-.69.56-1.25 1.25-1.25h1.5a.75.75 0 010 1.5H5v6h6v-1.25a.75.75 0 011.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-7c-.69 0-1.25-.56-1.25-1.25v-7z" />
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
                @click="toggleCritique(`${gender}-${idx}`)"
              >
                {{ expandedCritiques.has(`${gender}-${idx}`) ? 'Piilota arvostelu' : 'Näytä arvostelu' }}
                <svg
                  :class="['dog-chevron-sm', expandedCritiques.has(`${gender}-${idx}`) && 'dog-chevron-open']"
                  xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"
                >
                  <path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clip-rule="evenodd" />
                </svg>
              </button>
              <Transition name="dog-collapse">
                <div v-if="expandedCritiques.has(`${gender}-${idx}`)" class="dog-critique-text">
                  {{ dog.critique }}
                </div>
              </Transition>
            </div>
          </div>

          <!-- Empty results -->
          <div v-if="!breedResults.results?.length && !breedResults.awards?.length" class="dog-empty">
            <p>Ei tuloksia tämän rodun kohdalta.</p>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* ═══ Scoped design tokens ═══ */
.dog-page {
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

  font-family: 'DM Sans', sans-serif;
  font-weight: 300;
  color: var(--dog-text);
  background: var(--dog-bg);
  min-height: 100dvh;
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem;
  padding-bottom: 4rem;
}

/* ═══ Header ═══ */
.dog-header {
  text-align: center;
  padding: 2rem 0 1.5rem;
}
.dog-header-compact {
  padding: 1rem 0;
  text-align: left;
}
.dog-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--dog-text);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}
.dog-header-compact .dog-title {
  justify-content: flex-start;
}
.dog-title-sm {
  font-size: 1.35rem;
}
.dog-title-icon {
  font-size: 1.5rem;
}
.dog-subtitle {
  color: var(--dog-text-muted);
  margin: 0.35rem 0 0;
  font-size: 0.9rem;
}
.dog-judge {
  color: var(--dog-text-muted);
  margin: 0.25rem 0 0;
  font-size: 0.9rem;
}
.dog-judge strong {
  color: var(--dog-text);
  font-weight: 500;
}
.dog-meta-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.45rem;
  color: var(--dog-text-muted);
  font-size: 0.8rem;
}
.dog-source-link {
  color: var(--dog-accent);
  text-decoration: none;
  font-weight: 500;
}
.dog-source-link:hover {
  text-decoration: underline;
}
.dog-updated {
  color: var(--dog-text-muted);
}

/* ═══ Tabs ═══ */
.dog-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--dog-border);
  margin-bottom: 1rem;
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
  margin-bottom: 1rem;
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
  padding: 0.75rem 1rem 0.75rem 2.75rem;
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
  margin: -0.35rem 0 1rem;
  color: var(--dog-text-muted);
  font-size: 0.8rem;
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
  color: #121212;
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
  margin-bottom: 0.25rem;
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
  background: #333;
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
}
.dog-show-row {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  border-bottom: 1px solid var(--dog-border);
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 300;
  cursor: pointer;
  text-align: left;
  gap: 0.75rem;
  min-height: 44px;
  transition: background 0.12s;
}
.dog-show-row:hover {
  background: var(--dog-surface);
}
.dog-show-date {
  font-family: 'Commit Mono', ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.8rem;
  color: var(--dog-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}
.dog-show-name {
  flex: 1;
  color: var(--dog-accent);
}
.dog-search-result-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  flex: 1;
}
.dog-search-breed-tag {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--dog-accent-2);
  margin-top: 0.15rem;
}
.dog-arrow {
  width: 1rem;
  height: 1rem;
  color: var(--dog-text-muted);
  flex-shrink: 0;
}

/* ═══ Breadcrumb ═══ */
.dog-breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.75rem 0;
  font-size: 0.85rem;
  flex-wrap: wrap;
}
.dog-breadcrumb-link {
  background: none;
  border: none;
  color: var(--dog-accent);
  font-family: inherit;
  font-size: inherit;
  font-weight: 400;
  cursor: pointer;
  padding: 0.25rem 0;
  min-height: 44px;
  display: flex;
  align-items: center;
}
.dog-breadcrumb-link:hover {
  text-decoration: underline;
}
.dog-breadcrumb-sep {
  color: var(--dog-text-muted);
}
.dog-breadcrumb-current {
  color: var(--dog-text-muted);
}

/* ═══ Breed list (detail view) ═══ */
.dog-filter-row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.5rem;
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
}
.dog-breed-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  border-bottom: 1px solid var(--dog-border);
  color: var(--dog-text);
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 300;
  cursor: pointer;
  text-align: left;
  min-height: 44px;
  transition: background 0.12s;
}
.dog-breed-row:hover:not(:disabled) {
  background: var(--dog-surface);
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
.dog-breed-status {
  flex-shrink: 0;
}
.dog-check {
  color: #4ade80;
  font-size: 1.1rem;
  font-weight: 700;
}
.dog-no-results {
  color: var(--dog-text-muted);
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
  margin-bottom: 1.5rem;
}
.dog-gender-heading {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--dog-accent-2);
  margin: 1rem 0 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--dog-border);
}

/* ═══ Class header ═══ */
.dog-class-header {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--dog-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0.6rem 0 0.3rem;
  margin-top: 0.5rem;
}

/* ═══ Result card ═══ */
.dog-result-card {
  background: var(--dog-surface);
  border-radius: 0.5rem;
  margin-bottom: 0.375rem;
  overflow: hidden;
}
.dog-result-main {
  padding: 0.75rem 1rem;
}
.dog-result-top {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.35rem;
}
.dog-catalog-num {
  font-family: 'Commit Mono', ui-monospace, Menlo, Consolas, monospace;
  font-size: 0.8rem;
  color: var(--dog-text-muted);
  flex-shrink: 0;
}
.dog-placement {
  font-weight: 700;
  color: var(--dog-accent);
  font-size: 1rem;
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
  background: color-mix(in srgb, var(--dog-gold) 20%, transparent);
  color: var(--dog-gold);
  border: 1px solid color-mix(in srgb, var(--dog-gold) 40%, transparent);
}
.dog-badge-silver {
  background: color-mix(in srgb, var(--dog-silver) 15%, transparent);
  color: var(--dog-silver);
  border: 1px solid color-mix(in srgb, var(--dog-silver) 30%, transparent);
}
.dog-badge-bronze {
  background: color-mix(in srgb, var(--dog-bronze) 20%, transparent);
  color: var(--dog-bronze);
  border: 1px solid color-mix(in srgb, var(--dog-bronze) 35%, transparent);
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
  background: color-mix(in srgb, var(--dog-accent) 15%, transparent);
  color: var(--dog-accent);
  border: 1px solid color-mix(in srgb, var(--dog-accent) 30%, transparent);
}

/* ═══ Critique ═══ */
.dog-critique-toggle {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  width: 100%;
  padding: 0.5rem 1rem;
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
.dog-chevron-sm {
  width: 1rem;
  height: 1rem;
  transition: transform 0.2s;
  transform: rotate(-90deg);
  flex-shrink: 0;
}
.dog-critique-text {
  padding: 0.75rem 1rem;
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
