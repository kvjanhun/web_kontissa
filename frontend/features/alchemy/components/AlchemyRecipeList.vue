<script setup>
import { baseClass, baseLabel, itemCategoryClass } from '../alchemyRecipes.js'

defineProps({
  recipes: {
    type: Array,
    required: true,
  },
})

defineEmits(['open'])
</script>

<template>
  <div v-if="recipes.length" class="al-list">
    <button
      v-for="recipe in recipes"
      :key="recipe.id"
      class="al-card"
      @click="$emit('open', recipe.id)"
    >
      <h3 class="al-card-name">
        {{ recipe.name }}
        <span :class="['al-base', baseClass(recipe.base)]">{{ baseLabel(recipe.base) }}</span>
        <span v-if="recipe.dlc" class="al-dlc">DLC</span>
        <span v-if="!recipe.verified" class="al-unverified">unverified</span>
      </h3>
      <p class="al-card-meta al-inline-list">
        <span
          v-for="item in recipe.items"
          :key="item.id"
          :class="['al-ing-name', itemCategoryClass(item)]"
        >{{ item.name }}</span>
      </p>
    </button>
  </div>

  <p v-else class="al-empty">No recipe matches that.</p>
</template>
