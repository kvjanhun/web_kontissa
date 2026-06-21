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
const rankValue = computed(() => (props.showAwardRank ? props.dog.awardRank : props.dog.placement) || null)
const awards = computed(() => splitAwards(props.dog.awards))
const genderSymbol = computed(() =>
  props.dog.gender === 'uros' ? '♂' : props.dog.gender === 'narttu' ? '♀' : '',
)
const hasLead = computed(() => Boolean(rankValue.value || props.dog.number))
const hasMeta = computed(() =>
  Boolean(
    (props.showInlineMeta && (props.dog.class_name || genderSymbol.value)) ||
    awards.value.length,
  ),
)
</script>

<template>
  <div class="dog-result-card" :class="[gradeBorderClass(dog.grade), critiqueExpanded && 'dog-result-card-expanded']">
    <div class="dog-result-row">
      <!-- Line 1: identity (breed + name) and primary action -->
      <div class="dog-result-head">
        <div v-if="hasLead" class="dog-result-lead">
          <span v-if="rankValue" class="dog-placement-badge" title="Sijoitus">{{ rankValue }}.</span>
          <span v-if="dog.number" class="dog-catalog-num">#{{ dog.number }}</span>
        </div>

        <div class="dog-result-identity">
          <span v-if="showBreedMeta && dog.breedName" class="dog-result-breed">{{ dog.breedName }}</span>
          <a
            v-if="safeRegUrl"
            :href="safeRegUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="dog-dog-name"
          >
            <span class="dog-dog-name-text">{{ dog.name }}</span>
            <svg class="dog-external" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M128,48H48V208H208V128" />
              <polyline points="160 48 208 48 208 96" />
              <line x1="128" y1="128" x2="208" y2="48" />
            </svg>
          </a>
          <span v-else class="dog-dog-name-plain">{{ dog.name }}</span>
        </div>

        <div class="dog-result-actions">
          <span v-if="dog.grade" :class="['dog-grade', gradeClasses(dog.grade)]">
            {{ dog.grade }}
          </span>
          <button
            v-if="dog.critique"
            class="dog-critique-toggle"
            :aria-expanded="critiqueExpanded"
            @click="$emit('toggle-critique', critiqueKey)"
          >
            <svg class="dog-critique-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="40" y="32" width="176" height="192" rx="16" />
              <line x1="80" y1="80" x2="176" y2="80" />
              <line x1="80" y1="128" x2="176" y2="128" />
              <line x1="80" y1="176" x2="136" y2="176" />
            </svg>
            <span class="dog-critique-toggle-text">{{ critiqueExpanded ? 'Piilota' : 'Arvostelu' }}</span>
            <svg
              :class="['dog-chevron-sm', critiqueExpanded && 'dog-chevron-open']"
              xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
            >
              <polyline points="208 96 128 176 48 96" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Line 2: class, gender, and awards (wraps freely) -->
      <div v-if="hasMeta" class="dog-result-meta">
        <span v-if="showInlineMeta && dog.class_name" class="dog-result-class">{{ dog.class_name }}</span>
        <span v-if="showInlineMeta && genderSymbol" :class="['dog-result-gender', dog.gender]">{{ genderSymbol }}</span>
        <span
          v-for="(award, index) in awards"
          :key="index"
          class="dog-mini-award"
        >
          {{ award }}
        </span>
      </div>
    </div>

    <!-- Expanded critique text -->
    <Transition name="dog-collapse">
      <div v-if="dog.critique && critiqueExpanded" class="dog-critique-text">
        {{ dog.critique }}
      </div>
    </Transition>
  </div>
</template>
