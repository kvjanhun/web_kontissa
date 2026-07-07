<script setup>
import DogResultCard from './DogResultCard.vue'

const props = defineProps({
  // { key, label, dogs } from buildShowWinnersGroups; dogs carry awardRank in
  // placement order (winner first).
  group: {
    type: Object,
    required: true,
  },
  expandedCritiques: {
    type: Set,
    required: true,
  },
  // Critique-key namespace so winners toggle state never collides with the
  // breed-list / award-view cards rendered further down the page.
  critiquePrefix: {
    type: String,
    required: true,
  },
})

defineEmits(['toggle-critique'])

// Starts collapsed: one row with the award title and the winner inline
// ("BIS  1. rotu Winner Dog #123"); expanding reveals the full result cards
// for every placement.
const expanded = ref(false)

const winner = computed(() => props.group.dogs[0] || null)

function critiqueKey(dog) {
  return `${props.critiquePrefix}-${props.group.key}-${dog.breedGroup || dog.breedName || ''}-${dog.number || dog.name}`
}
</script>

<template>
  <div class="dog-finals-group">
    <h3 class="dog-finals-head">
      <button
        type="button"
        class="dog-finals-toggle"
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        <span class="dog-finals-label">{{ group.label }}</span>
        <span v-if="!expanded && winner" class="dog-finals-inline-winner">
          <span v-if="winner.awardRank" class="dog-finals-inline-rank">{{ winner.awardRank }}.</span>
          <span v-if="winner.breedName" class="dog-finals-inline-breed">{{ winner.breedName }}</span>
          <span class="dog-finals-inline-name">{{ winner.name }}</span>
          <span v-if="winner.number" class="dog-catalog-num">#{{ winner.number }}</span>
        </span>
        <svg
          :class="['dog-chevron-sm', expanded && 'dog-chevron-open']"
          xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
        >
          <polyline points="208 96 128 176 48 96" />
        </svg>
      </button>
    </h3>

    <div v-if="expanded" class="dog-results-grid">
      <DogResultCard
        v-for="dog in group.dogs"
        :key="critiqueKey(dog)"
        :dog="dog"
        :critique-key="critiqueKey(dog)"
        :critique-expanded="expandedCritiques.has(critiqueKey(dog))"
        show-inline-meta
        show-breed-meta
        show-award-rank
        @toggle-critique="$emit('toggle-critique', $event)"
      />
    </div>
  </div>
</template>
