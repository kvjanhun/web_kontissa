<script setup>
import { computed } from 'vue'
import DogResultCard from './DogResultCard.vue'
import DogStateBlock from './DogStateBlock.vue'
import { formatShowFullDate, genderSymbol, normalizeGender } from '../dogResults.js'

const props = defineProps({
  dogProfile: {
    type: Object,
    default: null,
  },
  profileLoading: {
    type: Boolean,
    default: false,
  },
  profileError: {
    type: String,
    default: '',
  },
  expandedCritiques: {
    type: Set,
    default: () => new Set(),
  },
})

defineEmits(['retry-profile', 'open-entry', 'open-show', 'toggle-critique', 'go-list'])

const safeProfileRegUrl = computed(() => safeHref(props.dogProfile?.reg_url))
const profileGenderSymbol = computed(() => genderSymbol(props.dogProfile?.gender))
const profileGenderClass = computed(() => normalizeGender(props.dogProfile?.gender))

// Entries arrive newest-show-first; group consecutive rows of the same show so
// a show with several rows (rare) renders under one header.
const entriesByShow = computed(() => {
  const groups = []
  for (const entry of props.dogProfile?.entries || []) {
    const last = groups[groups.length - 1]
    if (last && last.show.id === entry.show?.id) {
      last.entries.push(entry)
    } else {
      groups.push({ show: entry.show || {}, entries: [entry] })
    }
  }
  return groups
})

function critiqueKey(entry) {
  return `profile:${entry.show?.id}:${entry.fci_group}:${entry.breed_id}:${entry.number ?? entry.name}`
}
</script>

<template>
  <section class="dog-profile">
    <DogStateBlock
      v-if="profileLoading"
      mode="loading"
      :rows="5"
      tall
    />

    <DogStateBlock
      v-else-if="profileError"
      mode="error"
      :message="profileError"
      retry-label="Yritä uudelleen"
      @retry="$emit('retry-profile')"
    />

    <template v-else-if="dogProfile">
      <header class="dog-profile-head">
        <h2 class="dog-profile-name">
          <span v-if="profileGenderSymbol" :class="['dog-result-gender', profileGenderClass]">{{ profileGenderSymbol }}</span>
          {{ dogProfile.name }}
        </h2>
        <div class="dog-profile-meta">
          <a
            v-if="safeProfileRegUrl"
            :href="safeProfileRegUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="dog-profile-reg"
          >{{ dogProfile.reg_id }}</a>
          <span v-else class="dog-profile-reg">{{ dogProfile.reg_id }}</span>
          <span v-if="dogProfile.owner" class="dog-profile-owner">Om. {{ dogProfile.owner }}</span>
          <span class="dog-profile-counts">
            {{ dogProfile.show_count }} {{ dogProfile.show_count === 1 ? 'näyttely' : 'näyttelyä' }}
            · {{ dogProfile.result_count }} {{ dogProfile.result_count === 1 ? 'tulos' : 'tulosta' }}
          </span>
        </div>
      </header>

      <div v-if="!entriesByShow.length" class="dog-empty">
        <p>Ei tuloksia tälle koiralle.</p>
      </div>

      <div
        v-for="group in entriesByShow"
        :key="group.show.id"
        class="dog-profile-show"
      >
        <button class="dog-profile-show-head" type="button" @click="$emit('open-show', group.show)">
          <span v-if="formatShowFullDate(group.show)" class="dog-profile-show-date">
            {{ formatShowFullDate(group.show) }}
          </span>
          <span class="dog-profile-show-name">{{ group.show.name || group.show.title }}</span>
          <svg class="dog-chevron-sm dog-profile-show-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="96 48 176 128 96 208" />
          </svg>
        </button>

        <div class="dog-results-grid">
          <div
            v-for="entry in group.entries"
            :key="critiqueKey(entry)"
            class="dog-profile-entry"
          >
            <button
              v-if="entry.breed_name"
              type="button"
              class="dog-profile-entry-breed"
              title="Avaa rodun tulokset"
              @click="$emit('open-entry', entry)"
            >
              {{ entry.breed_name }}<template v-if="entry.judge"> · {{ entry.judge }}</template>
            </button>
            <DogResultCard
              :dog="entry"
              :critique-key="critiqueKey(entry)"
              :critique-expanded="expandedCritiques.has(critiqueKey(entry))"
              show-inline-meta
              @toggle-critique="$emit('toggle-critique', $event)"
            />
          </div>
        </div>
      </div>
    </template>

    <DogStateBlock
      v-else
      mode="empty"
      message="Ei tuloksia tälle koiralle."
    />
  </section>
</template>
