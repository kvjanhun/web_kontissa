<script setup>
import { baseClass, baseLabel, categoryClass, itemCategoryClass } from '../alchemyRecipes.js'

defineProps({
  matches: {
    type: Object,
    required: true,
  },
  hasSelection: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['open'])
</script>

<template>
  <section>
    <p v-if="!hasSelection" class="al-empty">
      Tick the ingredients in your pack and this tells you what they brew.
    </p>

    <template v-else>
      <h2 class="al-section-title">
        You can brew
        <span class="al-count">{{ matches.canBrew.length }}</span>
      </h2>
      <div v-if="matches.canBrew.length" class="al-list">
        <button
          v-for="recipe in matches.canBrew"
          :key="recipe.id"
          class="al-card al-card-good"
          @click="$emit('open', recipe.id)"
        >
          <h3 class="al-card-name">
            {{ recipe.name }}
            <span :class="['al-base', baseClass(recipe.base)]">{{ baseLabel(recipe.base) }}</span>
          </h3>
          <p class="al-card-meta al-inline-list">
            <span
              v-for="item in recipe.items"
              :key="item.id"
              :class="['al-ing-name', itemCategoryClass(item)]"
            ><span class="al-qty-inline">{{ item.qty }}&times;</span> {{ item.name }}</span>
          </p>
        </button>
      </div>
      <p v-else class="al-empty">Nothing yet — those ingredients don't complete a recipe.</p>

      <h2 class="al-section-title">
        One ingredient short
        <span class="al-count">{{ matches.oneShort.length }}</span>
      </h2>
      <div v-if="matches.oneShort.length" class="al-list">
        <button
          v-for="recipe in matches.oneShort"
          :key="recipe.id"
          class="al-card al-card-short"
          @click="$emit('open', recipe.id)"
        >
          <h3 class="al-card-name">
            {{ recipe.name }}
            <span :class="['al-base', baseClass(recipe.base)]">{{ baseLabel(recipe.base) }}</span>
          </h3>
          <p class="al-card-missing">
            Still need:
            <span
              :class="['al-ing-name', categoryClass(recipe.missing.ingredient?.category)]"
            >{{ recipe.missing.name }}</span>
          </p>
        </button>
      </div>
      <p v-else class="al-empty">Nothing is one ingredient away.</p>
    </template>

    <p class="al-note">
      Matching is on which ingredients you hold, not how many. Base liquids —
      water, wine, oil and spiritus — are assumed available.
    </p>
  </section>
</template>
