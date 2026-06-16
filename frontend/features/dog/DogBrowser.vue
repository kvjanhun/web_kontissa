<script setup>
import { computed } from 'vue'
import DogBreedResultsView from './components/DogBreedResultsView.vue'
import DogShowDetailView from './components/DogShowDetailView.vue'
import DogShowListView from './components/DogShowListView.vue'
import DogTopBar from './components/DogTopBar.vue'
import { useDogBrowser } from './useDogBrowser.js'
import './dog.css'

const {
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
  indexedSearchActive,
  groupedShows,
  thisWeekShows,
  breedEmptyText,
  selectedShowSourceUrl,
  selectedBreedSourceUrl,
  indexWarming,
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
} = useDogBrowser()

const pageTitle = computed(() => {
  if (currentView.value === 'detail') return showDetail.value?.title || selectedShow.value?.name || ''
  if (currentView.value === 'results') return breedResults.value?.breed || selectedBreed.value?.name || ''
  return 'Näyttelytulokset'
})
</script>

<template>
  <div class="dog-page">
    <DogTopBar
      :current-view="currentView"
      :title="pageTitle"
      @go-list="goToList"
      @go-detail="goToDetail"
    />

    <Transition name="dog-fade" mode="out-in">
      <DogShowListView
        v-if="currentView === 'list'"
        key="list"
        :filter-text="filterText"
        :shows-loading="showsLoading"
        :shows-error="showsError"
        :index-stats="indexStats"
        :index-warming="Boolean(indexWarming)"
        :indexed-search-active="indexedSearchActive"
        :search-results="searchResults"
        :search-loading="searchLoading"
        :search-error="searchError"
        :this-week-shows="thisWeekShows"
        :grouped-shows="groupedShows"
        :collapsed-months="collapsedMonths"
        @filter-input="updateFilterText"
        @select-search-result="onSelectSearchResult"
        @open-show="openShow"
        @toggle-month="toggleMonth"
        @retry-shows="fetchShows"
      />

      <DogShowDetailView
        v-else-if="currentView === 'detail'"
        key="detail"
        v-model:breed-search-query="breedSearchQuery"
        v-model:dog-grade-filter="dogGradeFilter"
        v-model:dog-class-filter="dogClassFilter"
        v-model:dog-award-filter="dogAwardFilter"
        :show-detail="showDetail"
        :detail-loading="detailLoading"
        :detail-error="detailError"
        :selected-show="selectedShow"
        :selected-show-source-url="selectedShowSourceUrl"
        :all-dogs-loaded="allDogsLoaded"
        :all-dogs-loading="allDogsLoading"
        :all-dogs-error="allDogsError"
        :all-dogs-progress-percent="allDogsProgressPercent"
        :all-dogs-progress-text="allDogsProgressText"
        :show-search-placeholder="showSearchPlaceholder"
        :available-show-classes="availableShowClasses"
        :available-show-awards="availableShowAwards"
        :show-breed-groups="showBreedGroups"
        :breed-empty-text="breedEmptyText"
        :expanded-critiques="expandedCritiques"
        :is-breed-group-expanded="isBreedGroupExpanded"
        @retry-detail="fetchShowDetail"
        @start-show-wide="startShowWideSearch"
        @retry-all-dogs="loadAllShowResults"
        @breed-group-click="onBreedGroupClick"
        @open-breed="openBreed"
        @toggle-critique="toggleCritique"
      />

      <DogBreedResultsView
        v-else-if="currentView === 'results'"
        key="results"
        v-model:dog-search-query="dogSearchQuery"
        v-model:dog-grade-filter="dogGradeFilter"
        v-model:dog-class-filter="dogClassFilter"
        v-model:dog-award-filter="dogAwardFilter"
        :breed-results="breedResults"
        :results-loading="resultsLoading"
        :results-error="resultsError"
        :selected-breed="selectedBreed"
        :selected-breed-source-url="selectedBreedSourceUrl"
        :available-classes="availableClasses"
        :available-awards="availableAwards"
        :results-by-gender-and-class="resultsByGenderAndClass"
        :expanded-critiques="expandedCritiques"
        @retry-results="fetchBreedResults"
        @toggle-critique="toggleCritique"
      />
    </Transition>
  </div>
</template>
