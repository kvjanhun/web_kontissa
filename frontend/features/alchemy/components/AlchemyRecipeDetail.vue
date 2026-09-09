<script setup>
import { baseClass, baseLabel, categoryClass, highlightStepText, itemCategoryClass } from '../alchemyRecipes.js'

defineProps({
  recipe: {
    type: Object,
    required: true,
  },
})

defineEmits(['back'])
</script>

<template>
  <div>
    <button class="al-back" @click="$emit('back')">&larr; All recipes</button>

    <article class="al-detail">
      <h2 class="al-detail-name">{{ recipe.name }}</h2>

      <div class="al-detail-badges">
        <span :class="['al-base', baseClass(recipe.base)]">{{ baseLabel(recipe.base) }} base</span>
        <span v-if="recipe.dlc" class="al-dlc">{{ recipe.dlc }} DLC</span>
        <span v-if="!recipe.verified" class="al-unverified">unverified</span>
      </div>

      <p v-if="recipe.effect" class="al-effect">{{ recipe.effect }}</p>
      <p v-if="recipe.strongEffect" class="al-effect al-effect-strong">
        Strong: {{ recipe.strongEffect }}
      </p>

      <h3 class="al-section-title">Ingredients</h3>
      <ul class="al-ingredients">
        <li
          v-for="item in recipe.items"
          :key="item.id"
          :class="['al-ingredient', itemCategoryClass(item)]"
        >
          <span class="al-qty">{{ item.qty }}&times;</span>
          <span class="al-ing-name">{{ item.name }}</span>
          <span v-if="item.ingredient" class="al-ingredient-cat">{{ item.ingredient.category }}</span>
        </li>
      </ul>

      <h3 class="al-section-title">Brewing</h3>
      <ol class="al-steps">
        <li v-for="(step, i) in recipe.steps" :key="i" class="al-step">
          <div class="al-step-body">
            <span>
              <template v-for="(part, j) in highlightStepText(step, recipe.items)" :key="j">
                <b v-if="part.category" :class="['al-step-ing', categoryClass(part.category)]">{{ part.text }}</b>
                <template v-else>{{ part.text }}</template>
              </template>
            </span>
            <div v-if="step.turns || step.grind || step.bellows || step.finish" class="al-step-tags">
              <span v-if="step.grind" class="al-tag al-op-grind">grind</span>
              <span v-if="step.bellows" class="al-tag al-op-bellows">bellows</span>
              <span v-if="step.turns" class="al-tag al-op-turns">
                &#8987; {{ step.turns }} {{ step.turns === 1 ? 'turn' : 'turns' }}
              </span>
              <span v-if="step.finish" :class="['al-tag', `al-op-${step.finish}`]">{{ step.finish }}</span>
            </div>
          </div>
        </li>
      </ol>

      <p v-if="!recipe.verified" class="al-note">
        The brewing steps for this recipe come from a single source. Check them in
        the game before you spend the ingredients.
      </p>
    </article>
  </div>
</template>
