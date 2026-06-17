<script setup>
import DogBreedGroup from './DogBreedGroup.vue'
import DogMetaBar from './DogMetaBar.vue'
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
  'update:dogGradeFilter',
  'update:dogClassFilter',
  'update:dogAwardFilter',
  'start-show-wide',
  'retry-all-dogs',
  'breed-group-click',
  'open-breed',
  'toggle-critique',
])
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
        @update:dogGradeFilter="$emit('update:dogGradeFilter', $event)"
        @update:dogClassFilter="$emit('update:dogClassFilter', $event)"
        @update:dogAwardFilter="$emit('update:dogAwardFilter', $event)"
        @start-show-wide="$emit('start-show-wide')"
        @retry-all-dogs="$emit('retry-all-dogs')"
      />

      <div v-if="showBreedGroups.length" class="dog-breed-list dog-breed-group-list">
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
