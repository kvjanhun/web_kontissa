<script setup>
import DogSearchClearButton from './DogSearchClearButton.vue'
import { DOG_GRADE_OPTIONS } from '../dogResults.js'

defineProps({
  searchQuery: {
    type: String,
    default: '',
  },
  gradeFilter: {
    type: String,
    default: '',
  },
  classFilter: {
    type: String,
    default: '',
  },
  awardFilter: {
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
  searchLabel: {
    type: String,
    default: 'Hae koiraa',
  },
  searchPlaceholder: {
    type: String,
    default: 'Nimi tai numero...',
  },
  showSearch: {
    type: Boolean,
    default: true,
  },
})

defineEmits([
  'update:searchQuery',
  'update:gradeFilter',
  'update:classFilter',
  'update:awardFilter',
])
</script>

<template>
  <div class="dog-results-filter-panel">
    <div class="dog-results-filter-grid">
      <div v-if="showSearch" class="dog-filter-col">
        <label class="dog-filter-label">{{ searchLabel }}</label>
        <div
          :class="[
            'dog-search-wrap',
            'dog-filter-search',
            searchQuery && 'dog-search-wrap-clearable',
          ]"
        >
          <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="116" cy="116" r="84" />
            <line x1="175.4" y1="175.4" x2="224" y2="224" />
          </svg>
          <input
            :value="searchQuery"
            type="text"
            class="dog-search-input"
            :placeholder="searchPlaceholder"
            @input="$emit('update:searchQuery', $event.target.value)"
          />
          <DogSearchClearButton
            v-if="searchQuery"
            @clear="$emit('update:searchQuery', '')"
          />
        </div>
      </div>

      <div class="dog-filter-col">
        <label class="dog-filter-label">Laatuarvostelu</label>
        <select
          :value="gradeFilter"
          class="dog-filter-select"
          @change="$emit('update:gradeFilter', $event.target.value)"
        >
          <option v-for="option in DOG_GRADE_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </div>

      <div v-if="availableClasses.length" class="dog-filter-col">
        <label class="dog-filter-label">Luokka</label>
        <select
          :value="classFilter"
          class="dog-filter-select"
          @change="$emit('update:classFilter', $event.target.value)"
        >
          <option value="">Kaikki luokat</option>
          <option v-for="className in availableClasses" :key="className" :value="className">
            {{ className }}
          </option>
        </select>
      </div>

      <div v-if="availableAwards.length" class="dog-filter-col">
        <label class="dog-filter-label">Palkinto</label>
        <select
          :value="awardFilter"
          class="dog-filter-select"
          @change="$emit('update:awardFilter', $event.target.value)"
        >
          <option value="">Kaikki palkinnot</option>
          <option v-for="award in availableAwards" :key="award" :value="award">
            {{ award }}
          </option>
        </select>
      </div>
    </div>
  </div>
</template>
