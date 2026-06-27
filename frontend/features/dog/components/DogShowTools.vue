<script setup>
import { computed } from 'vue'
import DogSearchClearButton from './DogSearchClearButton.vue'
import { DOG_GRADE_OPTIONS, gradeOptionLabel } from '../dogResults.js'

const props = defineProps({
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
})

defineEmits([
  'update:breedSearchQuery',
  'update:resultBreedsOnly',
  'update:dogGradeFilter',
  'update:dogClassFilter',
  'update:dogAwardFilter',
  'start-show-wide',
  'retry-all-dogs',
])

const gradeOptions = computed(() => (
  props.availableShowGrades?.length ? props.availableShowGrades : DOG_GRADE_OPTIONS
))
</script>

<template>
  <div class="dog-results-filter-panel dog-show-tools-panel">
    <div
      :class="[
        'dog-results-filter-grid',
        'dog-show-tools-grid',
        allDogsLoaded && 'dog-show-tools-grid-loaded',
        allDogsLoading && 'dog-show-tools-grid-loading',
        resultBreedFilterAvailable && 'dog-show-tools-grid-live',
      ]"
    >
      <div class="dog-filter-col dog-show-tools-search">
        <label class="dog-filter-label">
          {{ allDogsLoaded ? 'Rotu, tuomari tai koira' : 'Rotu tai tuomari' }}
        </label>
        <div
          :class="[
            'dog-search-wrap',
            'dog-breed-search',
            breedSearchQuery && 'dog-search-wrap-clearable',
          ]"
        >
          <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="116" cy="116" r="84" />
            <line x1="175.4" y1="175.4" x2="224" y2="224" />
          </svg>
          <input
            :value="breedSearchQuery"
            type="text"
            class="dog-search-input"
            :placeholder="showSearchPlaceholder"
            @input="$emit('update:breedSearchQuery', $event.target.value)"
          />
          <DogSearchClearButton
            v-if="breedSearchQuery"
            @clear="$emit('update:breedSearchQuery', '')"
          />
        </div>
      </div>

      <div v-if="resultBreedFilterAvailable" class="dog-filter-col dog-results-only-col">
        <label class="dog-filter-label">Rotulista</label>
        <label class="dog-results-only-toggle">
          <input
            type="checkbox"
            :checked="resultBreedsOnly"
            @change="$emit('update:resultBreedsOnly', $event.target.checked)"
          />
          <span class="dog-results-only-switch" aria-hidden="true">
            <span />
          </span>
          <span class="dog-results-only-text">Tuloksia saaneet</span>
        </label>
      </div>

      <div v-if="allDogsLoaded" class="dog-filter-col dog-show-grade-filter">
        <label class="dog-filter-label">Laatuarvostelu</label>
        <select
          :value="dogGradeFilter"
          class="dog-filter-select"
          @change="$emit('update:dogGradeFilter', $event.target.value)"
        >
          <option
            v-for="option in gradeOptions"
            :key="option.value"
            :value="option.value"
            :disabled="option.count === 0 && option.value !== dogGradeFilter"
            :class="{ 'dog-grade-option-empty': option.count === 0 }"
          >
            {{ gradeOptionLabel(option) }}
          </option>
        </select>
      </div>

      <div v-if="allDogsLoaded && availableShowClasses.length" class="dog-filter-col dog-show-class-filter">
        <label class="dog-filter-label">Luokka</label>
        <select
          :value="dogClassFilter"
          class="dog-filter-select"
          @change="$emit('update:dogClassFilter', $event.target.value)"
        >
          <option value="">Kaikki luokat</option>
          <option v-for="className in availableShowClasses" :key="className" :value="className">
            {{ className }}
          </option>
        </select>
      </div>

      <div v-if="allDogsLoaded && availableShowAwards.length" class="dog-filter-col dog-show-award-filter">
        <label class="dog-filter-label">Palkinto</label>
        <select
          :value="dogAwardFilter"
          class="dog-filter-select"
          @change="$emit('update:dogAwardFilter', $event.target.value)"
        >
          <option value="">Kaikki palkinnot</option>
          <option v-for="award in availableShowAwards" :key="award" :value="award">
            {{ award }}
          </option>
        </select>
      </div>

      <div
        v-if="!allDogsLoading && !allDogsLoaded && !allDogsError && allDogsAvailability && !allDogsAvailability.canLoad"
        class="dog-filter-col dog-show-progress-inline dog-show-availability"
        role="status"
      >
        <label class="dog-filter-label">Koko näyttely</label>
        <div class="dog-progress-inline-body">
          <svg class="dog-availability-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="128" cy="128" r="84" />
            <path d="M128 76v56l36 20" />
          </svg>
          <div class="dog-progress-content">
            <h2 class="dog-progress-title">{{ allDogsAvailability.title }}</h2>
            <p class="dog-progress-copy">{{ allDogsAvailability.message }}</p>
          </div>
        </div>
      </div>

      <div
        v-else-if="!allDogsLoading && !allDogsLoaded && !allDogsError"
        class="dog-filter-col dog-show-tools-action"
      >
        <label class="dog-filter-label">Koko näyttely</label>
        <button
          class="dog-show-wide-toggle"
          @click="$emit('start-show-wide')"
        >
          <svg class="dog-toggle-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <line x1="56" y1="72" x2="200" y2="72" />
            <circle cx="96" cy="72" r="20" />
            <line x1="56" y1="128" x2="200" y2="128" />
            <circle cx="152" cy="128" r="20" />
            <line x1="56" y1="184" x2="200" y2="184" />
            <circle cx="112" cy="184" r="20" />
          </svg>
          <span>{{ allDogsAvailability?.actionLabel || 'Suodata koko näyttelyä' }}</span>
          <svg class="dog-arrow-sm" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="96 48 176 128 96 208" />
          </svg>
        </button>
        <p v-if="allDogsAvailability?.note" class="dog-show-wide-note">
          {{ allDogsAvailability.note }}
        </p>
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
              {{ allDogsAvailability?.loadingNote || 'Ensimmäinen haku voi kestää, koska rotujen tulossivut haetaan taustalla rauhallisesti.' }}
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
          <button class="dog-show-retry-btn" @click="$emit('retry-all-dogs')">Yritä uudelleen</button>
        </div>
      </div>
    </div>
  </div>
</template>
