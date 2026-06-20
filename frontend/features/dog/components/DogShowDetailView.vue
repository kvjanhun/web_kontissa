<script setup>
import DogBreedGroup from './DogBreedGroup.vue'
import DogMetaBar from './DogMetaBar.vue'
import DogResultCard from './DogResultCard.vue'
import DogShowTools from './DogShowTools.vue'
import DogStateBlock from './DogStateBlock.vue'

defineProps({
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

defineEmits([
  'retry-detail',
  'update:breedSearchQuery',
  'update:resultBreedsOnly',
  'update:dogGradeFilter',
  'update:dogClassFilter',
  'update:dogAwardFilter',
  'start-show-wide',
  'retry-all-dogs',
  'breed-group-click',
  'open-breed',
  'toggle-critique',
])

function awardCritiqueKey(group, dog) {
  return `show-award-${group.key}-${dog.breedGroup || dog.breedName || ''}-${dog.number || dog.name}`
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

      <div v-else-if="showBreedGroups.length" class="dog-breed-list dog-breed-group-list">
        <DogBreedGroup
          v-for="group in showBreedGroups"
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

      <DogStateBlock v-else mode="empty" :message="breedEmptyText" />
    </div>
  </div>
</template>
