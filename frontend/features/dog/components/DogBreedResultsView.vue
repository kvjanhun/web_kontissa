<script setup>
import { computed } from 'vue'
import DogMetaBar from './DogMetaBar.vue'
import DogResultCard from './DogResultCard.vue'
import DogResultFilters from './DogResultFilters.vue'
import DogStateBlock from './DogStateBlock.vue'
import { sortBreedAwards } from '../dogResults.js'

const props = defineProps({
  breedResults: {
    type: Object,
    default: null,
  },
  resultsLoading: {
    type: Boolean,
    default: false,
  },
  resultsError: {
    type: String,
    default: '',
  },
  selectedBreed: {
    type: Object,
    default: null,
  },
  selectedBreedSourceUrl: {
    type: String,
    default: '',
  },
  dogSearchQuery: {
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
  availableGrades: {
    type: Array,
    default: () => [],
  },
  availableClasses: {
    type: Array,
    default: () => [],
  },
  availableAwards: {
    type: Array,
    default: () => [],
  },
  resultsByGenderAndClass: {
    type: Object,
    default: () => ({}),
  },
  awardResultGroups: {
    type: Array,
    default: () => [],
  },
  expandedCritiques: {
    type: Set,
    required: true,
  },
})

const emit = defineEmits([
  'retry-results',
  'update:dogSearchQuery',
  'update:dogGradeFilter',
  'update:dogClassFilter',
  'update:dogAwardFilter',
  'toggle-critique',
  'toggle-all-critiques',
])

function critiqueKey(gender, className, dog) {
  return `${gender}-${className}-${dog.number || dog.name}`
}

function awardCritiqueKey(group, dog) {
  return `award-${group.key}-${dog.number || dog.name}`
}

const sortedAwards = computed(() => {
  return sortBreedAwards(props.breedResults?.awards || [])
})

const visibleCritiqueKeys = computed(() => {
  const keys = []
  if (!props.breedResults) return keys

  if (props.dogAwardFilter && props.awardResultGroups.length) {
    props.awardResultGroups.forEach(group => {
      group.dogs.forEach(dog => {
        if (dog.critique) {
          keys.push(awardCritiqueKey(group, dog))
        }
      })
    })
  } else {
    for (const gender in props.resultsByGenderAndClass) {
      const classes = props.resultsByGenderAndClass[gender]
      for (const className in classes) {
        const dogs = classes[className]
        dogs.forEach(dog => {
          if (dog.critique) {
            keys.push(critiqueKey(gender, className, dog))
          }
        })
      }
    }
  }
  return keys
})

const allVisibleExpanded = computed(() => {
  const keys = visibleCritiqueKeys.value
  if (keys.length === 0) return false
  return keys.every(key => props.expandedCritiques.has(key))
})

const totalResultsCount = computed(() => {
  if (props.dogAwardFilter && props.awardResultGroups.length) {
    return props.awardResultGroups.reduce((acc, group) => acc + (group.dogs?.length || 0), 0)
  }
  let count = 0
  for (const gender in props.resultsByGenderAndClass) {
    const classes = props.resultsByGenderAndClass[gender]
    for (const className in classes) {
      count += classes[className]?.length || 0
    }
  }
  return count
})

function toggleAllVisible() {
  const keys = visibleCritiqueKeys.value
  const expand = !allVisibleExpanded.value
  emit('toggle-all-critiques', keys, expand)
}
</script>

<template>
  <div>
    <DogMetaBar
      v-if="breedResults"
      :judge="breedResults?.judge"
      :source-url="selectedBreedSourceUrl"
      :fetched-at-iso="breedResults?.fetched_at_iso"
    />

    <DogStateBlock v-if="resultsLoading" mode="loading" :rows="6" tall />

    <DogStateBlock
      v-else-if="resultsError"
      mode="error"
      :message="resultsError"
      retry-label="Yritä uudelleen"
      @retry="$emit('retry-results', selectedBreed)"
    />

    <div v-else-if="breedResults">
      <DogResultFilters
        :search-query="dogSearchQuery"
        :grade-filter="dogGradeFilter"
        :class-filter="dogClassFilter"
        :award-filter="dogAwardFilter"
        :grade-options="availableGrades"
        :available-classes="availableClasses"
        :available-awards="availableAwards"
        @update:searchQuery="$emit('update:dogSearchQuery', $event)"
        @update:gradeFilter="$emit('update:dogGradeFilter', $event)"
        @update:classFilter="$emit('update:dogClassFilter', $event)"
        @update:awardFilter="$emit('update:dogAwardFilter', $event)"
      />

      <div class="dog-results-meta-row-header">
        <div class="dog-results-meta-left">
          Löytyi <span class="dog-highlight-text">{{ totalResultsCount }}</span> {{ totalResultsCount === 1 ? 'koira' : 'koiraa' }}
        </div>
        <button
          v-if="visibleCritiqueKeys.length"
          type="button"
          class="dog-critique-toggle-all-btn"
          @click="toggleAllVisible"
        >
          <svg class="dog-chevron-icon" :class="{ 'dog-chevron-up': allVisibleExpanded }" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="196 96 128 164 60 96" />
          </svg>
          <span>{{ allVisibleExpanded ? 'Piilota arvostelut' : 'Näytä kaikki arvostelut' }}</span>
        </button>
      </div>

      <div v-if="sortedAwards.length && !dogSearchQuery && !dogGradeFilter && !dogClassFilter && !dogAwardFilter" class="dog-awards">
        <div
          v-for="(award, index) in sortedAwards"
          :key="index"
          class="dog-award-card"
        >
          <span class="dog-award-type">{{ award.type }}</span>
          <span class="dog-award-text">{{ award.text }}</span>
        </div>
      </div>

      <div
        v-if="dogAwardFilter && awardResultGroups.length"
        class="dog-award-results"
      >
        <div
          v-for="group in awardResultGroups"
          :key="group.key"
          class="dog-award-result-group"
        >
          <h2 class="dog-award-result-heading">{{ group.label }}</h2>

          <div class="dog-results-grid">
            <DogResultCard
              v-for="dog in group.dogs"
              :key="dog.number || dog.name"
              :dog="dog"
              :critique-key="awardCritiqueKey(group, dog)"
              :critique-expanded="expandedCritiques.has(awardCritiqueKey(group, dog))"
              show-award-rank
              @toggle-critique="$emit('toggle-critique', $event)"
            />
          </div>
        </div>
      </div>

      <template v-else>
        <div
          v-for="(classes, gender) in resultsByGenderAndClass"
          :key="gender"
          class="dog-gender-group"
        >
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
              <DogResultCard
                v-for="dog in dogs"
                :key="dog.number || dog.name"
                :dog="dog"
                :critique-key="critiqueKey(gender, className, dog)"
                :critique-expanded="expandedCritiques.has(critiqueKey(gender, className, dog))"
                @toggle-critique="$emit('toggle-critique', $event)"
              />
            </div>
          </div>
        </div>
      </template>

      <DogStateBlock
        v-if="!Object.keys(resultsByGenderAndClass).length"
        mode="empty"
        message="Ei tuloksia valituilla suodattimilla."
      />
    </div>
  </div>
</template>
