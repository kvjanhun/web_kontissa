<script setup>
import { categoryClass } from '../alchemyRecipes.js'

defineProps({
  ingredients: {
    type: Array,
    required: true,
  },
  held: {
    type: Set,
    required: true,
  },
  query: {
    type: String,
    default: '',
  },
  selectedCount: {
    type: Number,
    default: 0,
  },
})

defineEmits(['update:query', 'toggle', 'clear'])
</script>

<template>
  <section>
    <div class="al-picker-head">
      <h2 class="al-section-title">
        What you have
        <span class="al-count">{{ selectedCount }} selected</span>
      </h2>
      <button v-if="selectedCount" class="al-clear" @click="$emit('clear')">Clear</button>
    </div>

    <input
      class="al-search"
      type="search"
      placeholder="Search ingredients…"
      :value="query"
      @input="$emit('update:query', $event.target.value)"
    >

    <div v-if="ingredients.length" class="al-picker">
      <label
        v-for="ingredient in ingredients"
        :key="ingredient.id"
        :class="[
          'al-pick',
          categoryClass(ingredient.category),
          held.has(ingredient.id) && 'al-pick-on',
        ]"
      >
        <input
          type="checkbox"
          :checked="held.has(ingredient.id)"
          @change="$emit('toggle', ingredient.id)"
        >
        <span class="al-ing-name">{{ ingredient.name }}</span>
        <span class="al-pick-cat">{{ ingredient.category }}</span>
      </label>
    </div>

    <p v-else class="al-empty">No ingredient matches that.</p>
  </section>
</template>
