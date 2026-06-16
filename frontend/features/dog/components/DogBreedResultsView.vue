<script setup>
import DogMetaBar from './DogMetaBar.vue'
import DogResultCard from './DogResultCard.vue'
import DogResultFilters from './DogResultFilters.vue'
import DogStateBlock from './DogStateBlock.vue'

defineProps({
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
  expandedCritiques: {
    type: Set,
    required: true,
  },
})

defineEmits([
  'retry-results',
  'update:dogSearchQuery',
  'update:dogGradeFilter',
  'update:dogClassFilter',
  'update:dogAwardFilter',
  'toggle-critique',
])

function critiqueKey(gender, className, dog) {
  return `${gender}-${className}-${dog.number || dog.name}`
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
        :available-classes="availableClasses"
        :available-awards="availableAwards"
        @update:searchQuery="$emit('update:dogSearchQuery', $event)"
        @update:gradeFilter="$emit('update:dogGradeFilter', $event)"
        @update:classFilter="$emit('update:dogClassFilter', $event)"
        @update:awardFilter="$emit('update:dogAwardFilter', $event)"
      />

      <div v-if="breedResults.awards?.length && !dogSearchQuery && !dogGradeFilter && !dogClassFilter && !dogAwardFilter" class="dog-awards">
        <div
          v-for="(award, index) in breedResults.awards"
          :key="index"
          class="dog-award-card"
        >
          <span class="dog-award-type">{{ award.type }}</span>
          <span class="dog-award-text">{{ award.text }}</span>
        </div>
      </div>

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

      <DogStateBlock
        v-if="!Object.keys(resultsByGenderAndClass).length"
        mode="empty"
        message="Ei tuloksia valituilla suodattimilla."
      />
    </div>
  </div>
</template>
