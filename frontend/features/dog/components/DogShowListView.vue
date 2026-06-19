<script setup>
import DogSearchClearButton from './DogSearchClearButton.vue'
import DogStateBlock from './DogStateBlock.vue'
import {
  formatShowFullDate,
  formatShowDay,
  formatTimestamp,
  hasShowStats,
  showStatItems,
  showStatsLabel,
} from '../dogResults.js'

defineProps({
  filterText: {
    type: String,
    default: '',
  },
  showsLoading: {
    type: Boolean,
    default: false,
  },
  showsError: {
    type: String,
    default: '',
  },
  indexStats: {
    type: Object,
    default: null,
  },
  indexWarming: {
    type: Boolean,
    default: false,
  },
  indexedSearchActive: {
    type: Boolean,
    default: false,
  },
  searchResults: {
    type: Array,
    default: () => [],
  },
  searchLoading: {
    type: Boolean,
    default: false,
  },
  searchError: {
    type: String,
    default: '',
  },
  thisWeekShows: {
    type: Array,
    default: () => [],
  },
  groupedShows: {
    type: Object,
    default: () => ({}),
  },
  collapsedMonths: {
    type: Set,
    required: true,
  },
})

defineEmits([
  'filter-input',
  'select-search-result',
  'open-show',
  'toggle-month',
  'retry-shows',
])
</script>

<template>
  <div>
    <div class="dog-view-spacing" />

    <div
      :class="[
        'dog-search-wrap',
        filterText && 'dog-search-wrap-clearable',
        searchLoading && 'dog-search-wrap-loading',
      ]"
    >
      <svg class="dog-search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="116" cy="116" r="84" />
        <line x1="175.4" y1="175.4" x2="224" y2="224" />
      </svg>
      <input
        :value="filterText"
        type="text"
        class="dog-search-input"
        placeholder="Hae näyttelyä, rotua tai tuomaria..."
        @input="$emit('filter-input', $event.target.value)"
      />
      <DogSearchClearButton
        v-if="filterText"
        @clear="$emit('filter-input', '')"
      />
      <span v-if="searchLoading" class="dog-search-spinner" aria-hidden="true" />
    </div>

    <p v-if="indexedSearchActive && indexWarming" class="dog-status-note">
      Haku päivittyy: {{ indexStats?.indexed_show_count }}/{{ indexStats?.total_show_count }} näyttelyä.
    </p>
    <p v-else-if="indexedSearchActive && indexStats?.last_updated_iso" class="dog-status-note">
      Haku päivitetty {{ formatTimestamp(indexStats.last_updated_iso) }}.
    </p>

    <div v-if="indexedSearchActive">
      <div v-if="searchLoading" class="dog-search-loading-card" role="status" aria-live="polite">
        <div class="dog-search-loading-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <p>Haetaan...</p>
        <div class="dog-skeleton-list">
          <div v-for="i in 4" :key="i" class="dog-skeleton-row" />
        </div>
      </div>

      <DogStateBlock v-else-if="searchError" mode="error" :message="searchError" />

      <div v-else-if="searchResults.length">
        <button
          v-for="result in searchResults"
          :key="result.show.id + '-' + result.match + '-' + (result.breed ? result.breed.breed_id : '')"
          class="dog-show-row"
          @click="$emit('select-search-result', result)"
        >
          <div class="dog-search-result-info">
            <span class="dog-search-show-line">
              <span class="dog-show-date">{{ formatShowDay(result.show.date) }}</span>
              <span class="dog-show-name">{{ result.show.name }}</span>
            </span>
            <span v-if="hasShowStats(result.show)" class="dog-show-stats" :aria-label="showStatsLabel(result.show)">
              <span
                v-for="stat in showStatItems(result.show)"
                :key="stat.key"
                :class="['dog-show-stat', stat.soft && 'dog-show-stat-soft', stat.live && 'dog-show-stat-live']"
                :title="stat.title"
              >
                {{ stat.label }}
              </span>
            </span>
            <span v-if="formatShowFullDate(result.show)" class="dog-search-full-date">
              {{ formatShowFullDate(result.show) }}
            </span>
            <span v-if="result.breed" class="dog-search-breed-tag">
              {{ result.breed.name }} ({{ result.breed.count }} koiraa)
              <span v-if="result.breed.judge" class="dog-search-judge-sub">
                Tuomari: {{ result.breed.judge }}
              </span>
            </span>
            <span v-else-if="result.match === 'judge'" class="dog-search-breed-tag">
              Tuomari
              <span v-if="result.judge" class="dog-search-judge-sub">
                {{ result.judge }}
              </span>
            </span>
            <span v-else class="dog-search-breed-tag">Näyttely</span>
          </div>
          <svg class="dog-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="96 48 176 128 96 208" />
          </svg>
        </button>
      </div>

      <DogStateBlock v-else-if="!searchLoading" mode="empty" message="Ei hakutuloksia." />
    </div>

    <div v-else>
      <div v-if="!filterText && thisWeekShows.length" class="dog-this-week-section">
        <h2 class="dog-this-week-heading">
          <svg class="dog-heading-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="32" y="48" width="192" height="176" rx="8" />
            <line x1="32" y1="88" x2="224" y2="88" />
            <line x1="80" y1="24" x2="80" y2="48" />
            <line x1="176" y1="24" x2="176" y2="48" />
          </svg>
          Tällä viikolla
        </h2>
        <div class="dog-this-week-list">
          <button
            v-for="show in thisWeekShows"
            :key="'week-' + show.id"
            class="dog-show-row dog-show-row-featured"
            @click="$emit('open-show', show)"
          >
            <span class="dog-show-date">{{ formatShowDay(show.date) }}</span>
            <span class="dog-show-body">
              <span class="dog-show-name">{{ show.name }}</span>
              <span v-if="hasShowStats(show)" class="dog-show-stats" :aria-label="showStatsLabel(show)">
                <span
                  v-for="stat in showStatItems(show)"
                  :key="stat.key"
                  :class="['dog-show-stat', stat.soft && 'dog-show-stat-soft', stat.live && 'dog-show-stat-live']"
                  :title="stat.title"
                >
                  {{ stat.label }}
                </span>
              </span>
            </span>
            <svg class="dog-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="96 48 176 128 96 208" />
            </svg>
          </button>
        </div>
      </div>

      <DogStateBlock v-if="showsLoading" mode="loading" :rows="6" />

      <DogStateBlock
        v-else-if="showsError"
        mode="error"
        :message="showsError"
        retry-label="Yritä uudelleen"
        @retry="$emit('retry-shows')"
      />

      <div v-else-if="Object.keys(groupedShows).length">
        <div v-for="(monthShows, month) in groupedShows" :key="month" class="dog-month-group">
          <button class="dog-month-header" @click="$emit('toggle-month', month)">
            <span class="dog-month-label">{{ month }}</span>
            <span class="dog-month-count">{{ monthShows.length }}</span>
            <svg
              :class="['dog-chevron', !collapsedMonths.has(month) && 'dog-chevron-open']"
              xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
            >
              <polyline points="208 96 128 176 48 96" />
            </svg>
          </button>
          <Transition name="dog-collapse">
            <div v-if="!collapsedMonths.has(month)" class="dog-month-list">
              <button
                v-for="show in monthShows"
                :key="show.id"
                class="dog-show-row"
                @click="$emit('open-show', show)"
              >
                <span class="dog-show-date">{{ formatShowDay(show.date) }}</span>
                <span class="dog-show-body">
                  <span class="dog-show-name">{{ show.name }}</span>
                  <span v-if="hasShowStats(show)" class="dog-show-stats" :aria-label="showStatsLabel(show)">
                    <span
                      v-for="stat in showStatItems(show)"
                      :key="stat.key"
                      :class="['dog-show-stat', stat.soft && 'dog-show-stat-soft', stat.live && 'dog-show-stat-live']"
                      :title="stat.title"
                    >
                      {{ stat.label }}
                    </span>
                  </span>
                </span>
                <svg class="dog-arrow" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="96 48 176 128 96 208" />
                </svg>
              </button>
            </div>
          </Transition>
        </div>
      </div>

      <DogStateBlock v-else mode="empty" message="Ei näyttelyitä." />
    </div>
  </div>
</template>
