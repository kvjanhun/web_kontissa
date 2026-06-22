<script setup>
import DogBreedGroup from './DogBreedGroup.vue'
import DogMetaBar from './DogMetaBar.vue'
import DogResultCard from './DogResultCard.vue'
import DogShowTools from './DogShowTools.vue'
import DogStateBlock from './DogStateBlock.vue'
import { showAwardCritiqueKey, showBreedGroupCritiqueKey } from '../dogResults.js'

const props = defineProps({
  showDetail: {
    type: Object,
    default: null,
  },
  detailLoading: {
    type: Boolean,
    default: false,
  },
  detailError: {
    type: String,
    default: '',
  },
  selectedShow: {
    type: Object,
    default: null,
  },
  selectedShowSourceUrl: {
    type: String,
    default: '',
  },
  breedSearchQuery: {
    type: String,
    default: '',
  },
  resultBreedsOnly: {
    type: Boolean,
    default: false,
  },
  resultBreedFilterAvailable: {
    type: Boolean,
    default: false,
  },
  dogGradeFilter: {
    type: String,
    default: '',
  },
  dogClassFilter: {
    type: String,
    default: '',
  },
  dogAwardFilter: {
    type: String,
    default: '',
  },
  allDogsLoaded: {
    type: Boolean,
    default: false,
  },
  allDogsLoading: {
    type: Boolean,
    default: false,
  },
  allDogsError: {
    type: String,
    default: '',
  },
  allDogsProgressPercent: {
    type: Number,
    default: null,
  },
  allDogsProgressText: {
    type: String,
    default: '',
  },
  allDogsAvailability: {
    type: Object,
    default: null,
  },
  showSearchPlaceholder: {
    type: String,
    default: '',
  },
  availableShowGrades: {
    type: Array,
    default: () => [],
  },
  availableShowClasses: {
    type: Array,
    default: () => [],
  },
  availableShowAwards: {
    type: Array,
    default: () => [],
  },
  showBreedGroups: {
    type: Array,
    default: () => [],
  },
  showBreedSections: {
    type: Array,
    default: () => [],
  },
  showGroupMode: {
    type: String,
    default: 'fci',
  },
  breedGroupingAvailable: {
    type: Boolean,
    default: false,
  },
  breedSectionsCollapsible: {
    type: Boolean,
    default: false,
  },
  allBreedSectionsCollapsed: {
    type: Boolean,
    default: false,
  },
  isBreedSectionCollapsed: {
    type: Function,
    default: () => false,
  },
  showAwardResultGroups: {
    type: Array,
    default: () => [],
  },
  breedEmptyText: {
    type: String,
    default: '',
  },
  expandedCritiques: {
    type: Set,
    required: true,
  },
  isBreedGroupExpanded: {
    type: Function,
    required: true,
  },
})

const emit = defineEmits([
  'retry-detail',
  'update:breedSearchQuery',
  'update:resultBreedsOnly',
  'update:dogGradeFilter',
  'update:dogClassFilter',
  'update:dogAwardFilter',
  'update:showGroupMode',
  'start-show-wide',
  'retry-all-dogs',
  'breed-group-click',
  'open-breed',
  'toggle-critique',
  'toggle-all-critiques',
  'toggle-breed-section',
  'toggle-all-breed-sections',
])

const groupModeOptions = [
  { value: 'fci', label: 'Ryhmä' },
  { value: 'judge', label: 'Tuomari' },
  { value: 'alpha', label: 'Aakkoset' },
]

function awardCritiqueKey(group, dog) {
  return showAwardCritiqueKey(group, dog)
}

const shownDogCount = computed(() => {
  if (!props.allDogsLoaded) return null
  if (props.dogAwardFilter && props.showAwardResultGroups.length) {
    return props.showAwardResultGroups.reduce((total, group) => total + (group.dogs?.length || 0), 0)
  }
  return props.showBreedGroups.reduce((total, group) => total + (group.dogs?.length || 0), 0)
})

// Critique toggles only exist for dogs that are actually on screen: cards in the
// award view, or dogs inside breed groups that are both expanded and in a section
// that isn't collapsed. "Expand all" mirrors the breed page and acts only on those.
const visibleCritiqueKeys = computed(() => {
  if (!props.allDogsLoaded) return []
  const keys = []
  if (props.dogAwardFilter && props.showAwardResultGroups.length) {
    props.showAwardResultGroups.forEach(group => {
      group.dogs.forEach(dog => {
        if (dog.critique) keys.push(showAwardCritiqueKey(group, dog))
      })
    })
    return keys
  }
  props.showBreedSections.forEach(section => {
    if (section.label && props.isBreedSectionCollapsed(section.key)) return
    section.breeds.forEach(group => {
      if (!props.isBreedGroupExpanded(group)) return
      group.dogs.forEach(dog => {
        if (dog.critique) keys.push(showBreedGroupCritiqueKey(group, dog))
      })
    })
  })
  return keys
})

const allVisibleCritiquesExpanded = computed(() => {
  const keys = visibleCritiqueKeys.value
  if (keys.length === 0) return false
  return keys.every(key => props.expandedCritiques.has(key))
})

function toggleAllVisibleCritiques() {
  emit('toggle-all-critiques', visibleCritiqueKeys.value, !allVisibleCritiquesExpanded.value)
}
</script>

<template>
  <div>
    <DogMetaBar
      v-if="showDetail"
      :source-url="selectedShowSourceUrl"
      :fetched-at-iso="showDetail?.fetched_at_iso"
    />

    <DogStateBlock v-if="detailLoading" mode="loading" :rows="8" />

    <DogStateBlock
      v-else-if="detailError"
      mode="error"
      :message="detailError"
      retry-label="Yritä uudelleen"
      @retry="$emit('retry-detail', selectedShow)"
    />

    <div v-else-if="showDetail">
      <DogShowTools
        :breed-search-query="breedSearchQuery"
        :result-breeds-only="resultBreedsOnly"
        :result-breed-filter-available="resultBreedFilterAvailable"
        :dog-grade-filter="dogGradeFilter"
        :dog-class-filter="dogClassFilter"
        :dog-award-filter="dogAwardFilter"
        :all-dogs-loaded="allDogsLoaded"
        :all-dogs-loading="allDogsLoading"
        :all-dogs-error="allDogsError"
        :all-dogs-progress-percent="allDogsProgressPercent"
        :all-dogs-progress-text="allDogsProgressText"
        :all-dogs-availability="allDogsAvailability"
        :show-search-placeholder="showSearchPlaceholder"
        :available-show-grades="availableShowGrades"
        :available-show-classes="availableShowClasses"
        :available-show-awards="availableShowAwards"
        @update:breedSearchQuery="$emit('update:breedSearchQuery', $event)"
        @update:resultBreedsOnly="$emit('update:resultBreedsOnly', $event)"
        @update:dogGradeFilter="$emit('update:dogGradeFilter', $event)"
        @update:dogClassFilter="$emit('update:dogClassFilter', $event)"
        @update:dogAwardFilter="$emit('update:dogAwardFilter', $event)"
        @start-show-wide="$emit('start-show-wide')"
        @retry-all-dogs="$emit('retry-all-dogs')"
      />

      <div v-if="shownDogCount !== null" class="dog-results-meta-row-header">
        <div class="dog-results-meta-left">
          Löytyi <span class="dog-highlight-text">{{ shownDogCount }}</span> {{ shownDogCount === 1 ? 'koira' : 'koiraa' }}
        </div>
        <button
          v-if="visibleCritiqueKeys.length"
          type="button"
          class="dog-critique-toggle-all-btn"
          @click="toggleAllVisibleCritiques"
        >
          <svg class="dog-chevron-icon" :class="{ 'dog-chevron-up': allVisibleCritiquesExpanded }" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="196 96 128 164 60 96" />
          </svg>
          <span>{{ allVisibleCritiquesExpanded ? 'Piilota arvostelut' : 'Näytä kaikki arvostelut' }}</span>
        </button>
      </div>

      <div
        v-if="allDogsLoaded && dogAwardFilter && showAwardResultGroups.length"
        class="dog-award-results dog-show-award-results"
      >
        <div
          v-for="group in showAwardResultGroups"
          :key="group.key"
          class="dog-award-result-group"
        >
          <h2 class="dog-award-result-heading">{{ group.label }}</h2>

          <div class="dog-results-grid">
            <DogResultCard
              v-for="dog in group.dogs"
              :key="`${group.key}-${dog.breedGroup || dog.breedName || ''}-${dog.number || dog.name}`"
              :dog="dog"
              :critique-key="awardCritiqueKey(group, dog)"
              :critique-expanded="expandedCritiques.has(awardCritiqueKey(group, dog))"
              show-inline-meta
              show-breed-meta
              show-award-rank
              @toggle-critique="$emit('toggle-critique', $event)"
            />
          </div>
        </div>
      </div>

      <template v-else-if="showBreedSections.length">
        <div v-if="breedGroupingAvailable" class="dog-breed-list-controls">
          <div
            class="dog-breed-mode-tabs"
            role="tablist"
            aria-label="Rotujen ryhmittely"
          >
            <button
              v-for="mode in groupModeOptions"
              :key="mode.value"
              type="button"
              role="tab"
              :aria-selected="showGroupMode === mode.value"
              :class="['dog-breed-mode-tab', showGroupMode === mode.value && 'dog-breed-mode-tab-active']"
              @click="$emit('update:showGroupMode', mode.value)"
            >
              {{ mode.label }}
            </button>
          </div>

          <button
            v-if="breedSectionsCollapsible"
            type="button"
            class="dog-breed-collapse-all"
            @click="$emit('toggle-all-breed-sections')"
          >
            {{ allBreedSectionsCollapsed ? 'Avaa kaikki' : 'Sulje kaikki' }}
          </button>
        </div>

        <div class="dog-breed-sections">
          <section
            v-for="section in showBreedSections"
            :key="section.key"
            class="dog-breed-section"
          >
            <h2 v-if="section.label" class="dog-breed-section-head">
              <button
                type="button"
                class="dog-breed-section-heading"
                :aria-expanded="!isBreedSectionCollapsed(section.key)"
                @click="$emit('toggle-breed-section', section.key)"
              >
                <span class="dog-breed-section-title">{{ section.label }}</span>
                <span class="dog-breed-section-count">{{ section.breeds.length }}</span>
                <svg
                  :class="['dog-breed-section-chevron', !isBreedSectionCollapsed(section.key) && 'dog-breed-section-chevron-open']"
                  xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                >
                  <polyline points="208 96 128 176 48 96" />
                </svg>
              </button>
            </h2>
            <div
              v-show="!section.label || !isBreedSectionCollapsed(section.key)"
              class="dog-breed-list dog-breed-group-list"
            >
              <DogBreedGroup
                v-for="group in section.breeds"
                :key="group.key"
                :group="group"
                :all-dogs-loaded="allDogsLoaded"
                :expanded="isBreedGroupExpanded(group)"
                :expanded-critiques="expandedCritiques"
                @group-click="$emit('breed-group-click', $event)"
                @open-breed="$emit('open-breed', $event)"
                @toggle-critique="$emit('toggle-critique', $event)"
              />
            </div>
          </section>
        </div>
      </template>

      <DogStateBlock v-else mode="empty" :message="breedEmptyText" />
    </div>
  </div>
</template>
