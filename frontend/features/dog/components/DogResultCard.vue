<script setup>
import { gradeBorderClass, gradeClasses, splitAwards } from '../dogResults.js'

const props = defineProps({
  dog: {
    type: Object,
    required: true,
  },
  critiqueKey: {
    type: String,
    required: true,
  },
  critiqueExpanded: {
    type: Boolean,
    default: false,
  },
  showInlineMeta: {
    type: Boolean,
    default: false,
  },
  showBreedMeta: {
    type: Boolean,
    default: false,
  },
  showAwardRank: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['toggle-critique'])

const safeRegUrl = computed(() => safeHref(props.dog.reg_url))
</script>

<template>
  <div class="dog-result-card" :class="gradeBorderClass(dog.grade)">
    <div class="dog-result-main">
      <div class="dog-result-top">
        <span v-if="showAwardRank && dog.awardRank" class="dog-placement-badge">{{ dog.awardRank }}.</span>
        <span v-if="dog.number" class="dog-catalog-num">#{{ dog.number }}</span>
        <span v-if="!showAwardRank && dog.placement" class="dog-placement-badge">{{ dog.placement }}.</span>
        <span v-if="showBreedMeta && dog.breedName" class="dog-breed-badge-inline">{{ dog.breedName }}</span>
        <span v-if="showInlineMeta" class="dog-class-badge-inline">{{ dog.class_name }}</span>
        <span v-if="showInlineMeta" class="dog-gender-badge-inline">{{ dog.gender === 'uros' ? '♂' : dog.gender === 'narttu' ? '♀' : '' }}</span>

        <a
          v-if="safeRegUrl"
          :href="safeRegUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="dog-dog-name"
        >
          {{ dog.name }}
          <svg class="dog-external" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M128,48H48V208H208V128" />
            <polyline points="160 48 208 48 208 96" />
            <line x1="128" y1="128" x2="208" y2="48" />
          </svg>
        </a>
        <span v-else class="dog-dog-name-plain">{{ dog.name }}</span>
      </div>

      <div class="dog-result-badges">
        <span v-if="dog.grade" :class="['dog-grade', gradeClasses(dog.grade)]">
          {{ dog.grade }}
        </span>
        <span
          v-for="(award, index) in splitAwards(dog.awards)"
          :key="index"
          class="dog-mini-award"
        >
          {{ award }}
        </span>
      </div>
    </div>

    <button
      v-if="dog.critique"
      class="dog-critique-toggle"
      @click="$emit('toggle-critique', critiqueKey)"
    >
      <svg class="dog-critique-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="40" y="32" width="176" height="192" rx="16" />
        <line x1="80" y1="80" x2="176" y2="80" />
        <line x1="80" y1="128" x2="176" y2="128" />
        <line x1="80" y1="176" x2="136" y2="176" />
      </svg>
      <span>{{ critiqueExpanded ? 'Piilota arvostelu' : 'Näytä arvostelu' }}</span>
      <svg
        :class="['dog-chevron-sm', critiqueExpanded && 'dog-chevron-open']"
        xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
      >
        <polyline points="208 96 128 176 48 96" />
      </svg>
    </button>

    <Transition name="dog-collapse">
      <div v-if="dog.critique && critiqueExpanded" class="dog-critique-text">
        {{ dog.critique }}
      </div>
    </Transition>
  </div>
</template>
