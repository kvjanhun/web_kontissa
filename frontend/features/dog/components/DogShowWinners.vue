<script setup>
import DogFinalsGroup from './DogFinalsGroup.vue'

defineProps({
  // [{ key, label, dogs }] BIS sections from buildShowWinnersGroups. Group
  // placements (RYP) render inside the FCI breed-list sections instead.
  winners: {
    type: Array,
    required: true,
  },
  expandedCritiques: {
    type: Set,
    required: true,
  },
})

defineEmits(['toggle-critique'])
</script>

<template>
  <section class="dog-show-winners">
    <h2 class="dog-show-winners-title">Näyttelyn voittajat</h2>

    <DogFinalsGroup
      v-for="group in winners"
      :key="group.key"
      :group="group"
      :expanded-critiques="expandedCritiques"
      critique-prefix="show-winners-bis"
      @toggle-critique="$emit('toggle-critique', $event)"
    />
  </section>
</template>
