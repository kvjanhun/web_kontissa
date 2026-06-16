import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from '#app'
import {
  availableAwardsFromResults,
  availableClassesFromResults,
  buildDogQuery,
  createShowBreedGroups,
  dogMatchesShowFilters,
  filterDogResults,
  firstQueryValue,
  formatShowDay,
  getAllDogsProgressPercent,
  getAllDogsProgressText,
  gradeBorderClass,
  gradeClasses,
  groupResultsByGenderAndClass,
  hasShowStats,
  isNumericString,
  isThisWeekLeft,
  parseShowDate,
  sameId,
  shouldCollapseMonth,
  showStatItems,
  showStatsLabel,
  sourceForShow,
} from './dogResults.js'

export function useDogBrowser() {
  const route = useRoute()
  const router = useRouter()

  const currentView = ref('list')

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

  const filterText = ref('')
  const searchResults = ref([])
  const searchLoading = ref(false)
  const searchError = ref('')

  const breedSearchQuery = ref('')
  const dogSearchQuery = ref('')
  const dogGradeFilter = ref('')
  const dogClassFilter = ref('')
  const dogAwardFilter = ref('')

  const allDogsLoading = ref(false)
  const allDogsLoaded = ref(false)
  const allDogsError = ref('')
  const allDogsResults = ref([])
  const allDogsProgress = ref(null)

  const collapsedMonths = ref(new Set())
  const expandedCritiques = ref(new Set())
  const expandedBreedGroups = ref(new Set())

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

  function getRouteSelection() {
    return {
      showId: firstQueryValue(route.query.show),
      groupId: firstQueryValue(route.query.group),
      breedId: firstQueryValue(route.query.breed),
    }
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

  const allDogsProgressPercent = computed(() => getAllDogsProgressPercent(allDogsProgress.value))
  const allDogsProgressText = computed(() => getAllDogsProgressText(allDogsProgress.value))

  const showSearchPlaceholder = computed(() => (
    allDogsLoaded.value
      ? 'Hae rotua, tuomaria tai koiraa...'
      : 'Hae rotua tai tuomaria...'
  ))

  const allDogsAfterShowFilters = computed(() => {
    if (!allDogsLoaded.value) return []
    return allDogsResults.value.filter(dog => dogMatchesShowFilters(dog, {
      grade: dogGradeFilter.value,
      className: dogClassFilter.value,
      award: dogAwardFilter.value,
    }))
  })

  const showWideFiltersActive = computed(() => (
    allDogsLoaded.value && Boolean(
      breedSearchQuery.value.trim() ||
      dogGradeFilter.value ||
      dogClassFilter.value ||
      dogAwardFilter.value
    )
  ))

  const showBreedGroups = computed(() => createShowBreedGroups({
    breeds: showDetail.value?.breeds || [],
    dogs: allDogsAfterShowFilters.value,
    query: breedSearchQuery.value,
    allDogsLoaded: allDogsLoaded.value,
    filters: {
      grade: dogGradeFilter.value,
      className: dogClassFilter.value,
      award: dogAwardFilter.value,
    },
  }))

  const availableShowClasses = computed(() => availableClassesFromResults(allDogsResults.value || []))
  const availableShowAwards = computed(() => availableAwardsFromResults(allDogsResults.value || []))

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
    } catch {
      allDogsError.value = 'Tulosten hakeminen epäonnistui.'
    } finally {
      if (!keepLoading) {
        allDogsLoading.value = false
      }
    }
  }

  function startShowWideSearch() {
    loadAllShowResults()
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

  async function fetchShows() {
    showsLoading.value = true
    showsError.value = ''
    try {
      const data = await $fetch('/api/dog/shows')
      shows.value = data.shows || []
      indexStats.value = data.index || null

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
    } catch {
      showsError.value = 'Näyttelyiden lataaminen epäonnistui.'
    } finally {
      showsLoading.value = false
    }
  }

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
    } catch {
      if (syncToken !== null && syncToken !== routeSyncToken) return
      detailError.value = 'Näyttelyn tietojen lataaminen epäonnistui.'
    } finally {
      if (syncToken === null || syncToken === routeSyncToken) {
        detailLoading.value = false
      }
    }
    if (updateRoute) pushDogQuery({ show: show.id })
  }

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
    } catch {
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

  function onSearchInput() {
    clearTimeout(searchTimer)
    const query = filterText.value.trim()
    searchRequestId += 1
    const requestId = searchRequestId
    if (query.length < 2) {
      searchResults.value = []
      searchLoading.value = false
      searchError.value = ''
      return
    }
    searchLoading.value = true
    searchError.value = ''
    searchTimer = setTimeout(async () => {
      try {
        const data = await $fetch(`/api/dog/search?q=${encodeURIComponent(query)}`)
        if (requestId !== searchRequestId) return
        searchResults.value = data.results || []
        indexStats.value = data.index || indexStats.value
      } catch {
        if (requestId !== searchRequestId) return
        searchError.value = 'Haku epäonnistui.'
      } finally {
        if (requestId !== searchRequestId) return
        searchLoading.value = false
      }
    }, 300)
  }

  function updateFilterText(value) {
    filterText.value = value
    onSearchInput()
  }

  async function onSelectSearchResult(result) {
    if (!result?.show?.id) return
    if (result.breed && result.breed.has_results) {
      return pushDogQuery({
        show: result.show.id,
        group: result.breed.group,
        breed: result.breed.breed_id,
      }, { scrollToTop: true })
    }
    return pushDogQuery({ show: result.show.id }, { scrollToTop: true })
  }

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

  function toggleMonth(month) {
    const months = new Set(collapsedMonths.value)
    if (months.has(month)) months.delete(month)
    else months.add(month)
    collapsedMonths.value = months
  }

  function toggleCritique(key) {
    const critiques = new Set(expandedCritiques.value)
    if (critiques.has(key)) critiques.delete(key)
    else critiques.add(key)
    expandedCritiques.value = critiques
  }

  function toggleBreedGroup(key) {
    const groups = new Set(expandedBreedGroups.value)
    if (groups.has(key)) groups.delete(key)
    else groups.add(key)
    expandedBreedGroups.value = groups
  }

  const filteredShows = computed(() => {
    const query = filterText.value.toLowerCase().trim()
    if (!query) return shows.value
    return shows.value.filter(show =>
      show.name.toLowerCase().includes(query) || show.date?.toLowerCase().includes(query)
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

  const thisWeekShows = computed(() => (
    shows.value.filter(show => isThisWeekLeft(parseShowDate(show.date)))
  ))

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

  const filteredDogResults = computed(() => filterDogResults(breedResults.value?.results || [], {
    search: dogSearchQuery.value,
    grade: dogGradeFilter.value,
    className: dogClassFilter.value,
    award: dogAwardFilter.value,
  }))

  const availableClasses = computed(() => availableClassesFromResults(breedResults.value?.results || []))
  const availableAwards = computed(() => availableAwardsFromResults(breedResults.value?.results || []))
  const resultsByGenderAndClass = computed(() => groupResultsByGenderAndClass(filteredDogResults.value))

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

  return {
    currentView,
    showsLoading,
    showsError,
    indexStats,
    selectedShow,
    showDetail,
    detailLoading,
    detailError,
    selectedBreed,
    breedResults,
    resultsLoading,
    resultsError,
    filterText,
    searchResults,
    searchLoading,
    searchError,
    breedSearchQuery,
    dogSearchQuery,
    dogGradeFilter,
    dogClassFilter,
    dogAwardFilter,
    allDogsLoading,
    allDogsLoaded,
    allDogsError,
    allDogsProgressPercent,
    allDogsProgressText,
    collapsedMonths,
    expandedCritiques,
    showSearchPlaceholder,
    showBreedGroups,
    availableShowClasses,
    availableShowAwards,
    showWideFiltersActive,
    indexedSearchActive,
    groupedShows,
    thisWeekShows,
    breedEmptyText,
    selectedShowSourceUrl,
    selectedBreedSourceUrl,
    indexWarming,
    filteredDogResults,
    availableClasses,
    availableAwards,
    resultsByGenderAndClass,
    startShowWideSearch,
    loadAllShowResults,
    fetchShows,
    fetchShowDetail,
    fetchBreedResults,
    updateFilterText,
    onSelectSearchResult,
    goToList,
    goToDetail,
    openShow,
    openBreed,
    onBreedGroupClick,
    isBreedGroupExpanded,
    toggleMonth,
    toggleCritique,
    formatShowDay,
    hasShowStats,
    showStatItems,
    showStatsLabel,
    gradeClasses,
    gradeBorderClass,
  }
}
