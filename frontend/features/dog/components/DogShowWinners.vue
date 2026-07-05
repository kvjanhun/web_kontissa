<script setup>
import DogResultCard from './DogResultCard.vue'

const props = defineProps({
  // { bisGroups: [{ key, label, dogs }], rypGroups: [{ key, label, dogs }] }
  // from buildShowWinnersGroups.
  winners: {
    type: Object,
    required: true,
  },
  expandedCritiques: {
    type: Set,
    required: true,
  },
})

defineEmits(['toggle-critique'])

// Winners cards live in their own critique namespace so their toggle state never
// collides with the breed-list / award-view cards below.
function critiqueKey(prefix, group, dog) {
  return `show-winners-${prefix}-${group.key}-${dog.breedGroup || dog.breedName || ''}-${dog.number || dog.name}`
}
</script>

<template>
  <section class="dog-show-winners">
    <h2 class="dog-show-winners-title">Näyttelyn voittajat</h2>

    <div
      v-for="group in props.winners.bisGroups"
      :key="group.key"
      class="dog-show-winners-group"
    >
      <h3 class="dog-show-winners-heading">{{ group.label }}</h3>
      <div class="dog-results-grid">
        <DogResultCard
          v-for="dog in group.dogs"
          :key="critiqueKey('bis', group, dog)"
          :dog="dog"
          :critique-key="critiqueKey('bis', group, dog)"
          :critique-expanded="expandedCritiques.has(critiqueKey('bis', group, dog))"
          show-inline-meta
          show-breed-meta
          show-award-rank
          @toggle-critique="$emit('toggle-critique', $event)"
        />
      </div>
    </div>

    <template v-if="props.winners.rypGroups.length">
      <h3 class="dog-show-winners-subtitle">Ryhmävoittajat (RYP-1)</h3>
      <div
        v-for="group in props.winners.rypGroups"
        :key="group.key"
        class="dog-show-winners-group"
      >
        <h4 class="dog-show-winners-heading dog-show-winners-heading-sm">{{ group.label }}</h4>
        <div class="dog-results-grid">
          <DogResultCard
            v-for="dog in group.dogs"
            :key="critiqueKey('ryp', group, dog)"
            :dog="dog"
            :critique-key="critiqueKey('ryp', group, dog)"
            :critique-expanded="expandedCritiques.has(critiqueKey('ryp', group, dog))"
            show-inline-meta
            show-breed-meta
            @toggle-critique="$emit('toggle-critique', $event)"
          />
        </div>
      </div>
    </template>
  </section>
</template>
