<script setup>
import AlchemyIngredientPicker from './components/AlchemyIngredientPicker.vue'
import AlchemyMatchResults from './components/AlchemyMatchResults.vue'
import AlchemyRecipeDetail from './components/AlchemyRecipeDetail.vue'
import AlchemyRecipeList from './components/AlchemyRecipeList.vue'
import { BASE_LIQUIDS, baseClass } from './alchemyRecipes.js'
import { useAlchemyBrowser } from './useAlchemyBrowser.js'
import './alchemy.css'

const {
  view,
  recipes,
  recipeQuery,
  baseFilter,
  allBasesSelected,
  toggleBase,
  selectAllBases,
  ingredientQuery,
  visibleRecipes,
  visibleIngredients,
  selectedRecipe,
  heldSet,
  selectedCount,
  matches,
  openRecipe,
  showList,
  showMatcher,
  toggleIngredient,
  clearSelection,
} = useAlchemyBrowser()
</script>

<template>
  <div class="alchemy-page">
    <div class="alchemy-shell">
      <header class="al-header">
        <h1 class="al-title">Al<span class="al-title-mark">chemy</span></h1>
        <p class="al-subtitle">Kingdom Come: Deliverance II — recipes and what your herbs will brew</p>
      </header>

      <nav class="al-tabs">
        <button
          :class="['al-tab', view !== 'matcher' && 'al-tab-active']"
          @click="showList"
        >
          Recipes
        </button>
        <button
          :class="['al-tab', view === 'matcher' && 'al-tab-active']"
          @click="showMatcher"
        >
          What can I brew?
        </button>
      </nav>

      <AlchemyRecipeDetail
        v-if="view === 'detail'"
        :recipe="selectedRecipe"
        @back="showList"
      />

      <template v-else-if="view === 'matcher'">
        <AlchemyIngredientPicker
          :ingredients="visibleIngredients"
          :held="heldSet"
          :query="ingredientQuery"
          :selected-count="selectedCount"
          @update:query="ingredientQuery = $event"
          @toggle="toggleIngredient"
          @clear="clearSelection"
        />
        <AlchemyMatchResults
          :matches="matches"
          :has-selection="selectedCount > 0"
          @open="openRecipe"
        />
      </template>

      <template v-else>
        <div class="al-controls">
          <input
            v-model="recipeQuery"
            class="al-search"
            type="search"
            placeholder="Search recipes or ingredients…"
          >
          <!-- A toggle group: "All" is the reset action (every base back in),
               each base chip is a membership toggle whose active state means
               "currently included", not "currently the only one shown". -->
          <div class="al-filters">
            <button
              :class="['al-chip', allBasesSelected && 'al-chip-active']"
              @click="selectAllBases"
            >
              All
            </button>
            <button
              v-for="base in BASE_LIQUIDS"
              :key="base.id"
              :class="['al-chip', baseClass(base.id), baseFilter.has(base.id) && 'al-chip-active']"
              @click="toggleBase(base.id)"
            >
              {{ base.label }}
            </button>
          </div>
        </div>

        <AlchemyRecipeList :recipes="visibleRecipes" @open="openRecipe" />

        <p class="al-note">
          {{ recipes.length }} recipes, cross-checked against four sources. An
          "unverified" marker means the brewing steps rest on a single source —
          check those in the game before you spend the ingredients.
        </p>
      </template>
    </div>
  </div>
</template>
