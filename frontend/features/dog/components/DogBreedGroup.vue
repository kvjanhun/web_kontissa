<script setup>
import DogResultCard from './DogResultCard.vue'

const props = defineProps({
  group: {
    type: Object,
    required: true,
  },
  allDogsLoaded: {
    type: Boolean,
    default: false,
  },
  expanded: {
    type: Boolean,
    default: false,
  },
  expandedCritiques: {
    type: Set,
    required: true,
  },
})

defineEmits(['group-click', 'open-breed', 'toggle-critique'])

function critiqueKey(dog) {
  return `all-${props.group.key}-${dog.number || dog.name}`
}
</script>

<template>
  <div class="dog-breed-group-section">
    <button
      :class="['dog-breed-group-header-btn', !group.canOpenResults && !group.dogs.length && 'dog-breed-row-disabled']"
      :disabled="!group.canOpenResults && !group.dogs.length"
      @click="$emit('group-click', group)"
    >
      <span class="dog-breed-group-main">
        <span class="dog-breed-group-title">{{ group.breedName }}</span>
        <span class="dog-breed-group-meta">
          <span v-if="typeof group.count === 'number'" class="dog-breed-group-count">{{ group.count }} koiraa</span>
          <span v-if="group.judge" class="dog-breed-group-judge">Tuomari: {{ group.judge }}</span>
        </span>
      </span>

      <span class="dog-breed-group-side">
        <span
          v-if="group.resultProgressLabel"
          class="dog-breed-group-badge dog-breed-progress-badge"
          :title="`${group.resultProgressLabel} arvosteltu`"
        >
          {{ group.resultProgressLabel }}
        </span>
        <span
          v-else-if="allDogsLoaded && group.dogs.length"
          class="dog-breed-group-badge"
        >
          {{ group.dogs.length }} tulosta
        </span>
        <span
          v-if="group.has_results"
          class="dog-breed-result-icon"
          title="Tulokset saatavilla"
          aria-label="Tulokset saatavilla"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="64 128 104 168 192 80" />
          </svg>
        </span>
        <span
          v-else
          class="dog-breed-result-icon dog-breed-result-icon-muted"
          title="Ei tuloksia"
          aria-label="Ei tuloksia"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="64" y1="128" x2="192" y2="128" />
          </svg>
        </span>
        <svg
          v-if="allDogsLoaded && group.dogs.length"
          :class="['dog-chevron-sm', expanded && 'dog-chevron-open']"
          xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
        >
          <polyline points="208 96 128 176 48 96" />
        </svg>
        <svg
          v-else-if="group.canOpenResults"
          class="dog-arrow-sm"
          xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
        >
          <polyline points="96 48 176 128 96 208" />
        </svg>
      </span>
    </button>

    <Transition name="dog-collapse">
      <div
        v-if="expanded"
        class="dog-breed-group-dogs"
      >
        <div class="dog-breed-group-actions">
          <button
            class="dog-breed-open-link"
            @click="$emit('open-breed', group.breed)"
          >
            <span>Rotutulokset</span>
            <svg class="dog-arrow-sm" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="96 48 176 128 96 208" />
            </svg>
          </button>
        </div>

        <div class="dog-results-grid">
          <DogResultCard
            v-for="dog in group.dogs"
            :key="`${group.key}-${dog.number || dog.name}`"
            :dog="dog"
            :critique-key="critiqueKey(dog)"
            :critique-expanded="expandedCritiques.has(critiqueKey(dog))"
            show-inline-meta
            @toggle-critique="$emit('toggle-critique', $event)"
          />
        </div>
      </div>
    </Transition>
  </div>
</template>
