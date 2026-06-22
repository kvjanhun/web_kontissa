<script setup>
import { computed, watch } from 'vue'
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
  resultBreedsOnly,
  resultBreedFilterAvailable,
  dogSearchQuery,
  dogGradeFilter,
  dogClassFilter,
  dogAwardFilter,
  allDogsLoading,
  allDogsLoaded,
  allDogsError,
  allDogsProgressPercent,
  allDogsProgressText,
  allDogsAvailability,
  collapsedMonths,
  expandedCritiques,
  showSearchPlaceholder,
  showBreedGroups,
  showGroupMode,
  showBreedSections,
  breedGroupingAvailable,
  breedSectionsCollapsible,
  allBreedSectionsCollapsed,
  isBreedSectionCollapsed,
  toggleBreedSection,
  toggleAllBreedSections,
  availableShowGrades,
  availableShowClasses,
  availableShowAwards,
  showAwardResultGroups,
  indexedSearchActive,
  groupedShows,
  thisWeekShows,
  breedEmptyText,
  selectedShowSourceUrl,
  selectedBreedSourceUrl,
  indexWarming,
  availableGrades,
  availableClasses,
  availableAwards,
  resultsByGenderAndClass,
  awardResultGroups,
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
  toggleAllCritiques,
} = useDogBrowser()

const pageTitle = computed(() => {
  if (currentView.value === 'detail') return showDetail.value?.title || selectedShow.value?.name || ''
  if (currentView.value === 'results') return breedResults.value?.breed || selectedBreed.value?.name || ''
  return 'Näyttelytulokset'
})

// Reflect the open show/breed in the document title so browser tabs and shared
// deep links (?show=…&breed=…) are meaningful instead of always generic.
watch(pageTitle, (title) => {
  if (!import.meta.client) return
  document.title = title ? `${title} | erez.ac` : 'Näyttelytulokset | erez.ac'
}, { immediate: true })
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
        v-model:result-breeds-only="resultBreedsOnly"
        v-model:dog-grade-filter="dogGradeFilter"
        v-model:dog-class-filter="dogClassFilter"
        v-model:dog-award-filter="dogAwardFilter"
        v-model:show-group-mode="showGroupMode"
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
        :all-dogs-availability="allDogsAvailability"
        :result-breed-filter-available="resultBreedFilterAvailable"
        :show-search-placeholder="showSearchPlaceholder"
        :available-show-grades="availableShowGrades"
        :available-show-classes="availableShowClasses"
        :available-show-awards="availableShowAwards"
        :show-breed-groups="showBreedGroups"
        :show-breed-sections="showBreedSections"
        :breed-grouping-available="breedGroupingAvailable"
        :breed-sections-collapsible="breedSectionsCollapsible"
        :all-breed-sections-collapsed="allBreedSectionsCollapsed"
        :is-breed-section-collapsed="isBreedSectionCollapsed"
        :show-award-result-groups="showAwardResultGroups"
        :breed-empty-text="breedEmptyText"
        :expanded-critiques="expandedCritiques"
        :is-breed-group-expanded="isBreedGroupExpanded"
        @retry-detail="fetchShowDetail"
        @start-show-wide="startShowWideSearch"
        @retry-all-dogs="loadAllShowResults"
        @breed-group-click="onBreedGroupClick"
        @open-breed="openBreed"
        @toggle-critique="toggleCritique"
        @toggle-breed-section="toggleBreedSection"
        @toggle-all-breed-sections="toggleAllBreedSections"
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
        :available-grades="availableGrades"
        :available-classes="availableClasses"
        :available-awards="availableAwards"
        :results-by-gender-and-class="resultsByGenderAndClass"
        :award-result-groups="awardResultGroups"
        :expanded-critiques="expandedCritiques"
        @retry-results="fetchBreedResults"
        @toggle-critique="toggleCritique"
        @toggle-all-critiques="toggleAllCritiques"
      />
    </Transition>
  </div>
</template>
