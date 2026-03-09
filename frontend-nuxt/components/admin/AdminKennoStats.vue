<script setup>
import { ref, onMounted } from 'vue'

const stats = ref(null)
const loading = ref(true)

// Achievements
const achievements = ref(null)
const achLoading = ref(false)
const achDays = ref(7)
const RANK_COLS = [
  'Etsi sanoja!', 'Hyvä alku', 'Nyt mennään!',
  'Onnistuja', 'Sanavalmis', 'Ällistyttävä', 'Täysi kenno',
]

async function fetchAchievements(days) {
  achDays.value = days
  achLoading.value = true
  try {
    const res = await fetch(`/api/kenno/achievements?days=${days}`)
    if (res.ok) achievements.value = await res.json()
  } catch { /* ignore */ }
  finally { achLoading.value = false }
}

onMounted(async () => {
  try {
    const res = await fetch('/api/kenno/stats')
    if (res.ok) stats.value = await res.json()
  } catch { /* ignore */ }
  finally { loading.value = false }
  fetchAchievements(7)
})
</script>

<template>
  <div>
    <div v-if="loading" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Loading...</div>
    <div v-else-if="!stats" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Failed to load stats.</div>
    <div v-else class="space-y-2">
      <div v-for="(value, label) in {
        'Sanakenno Page Views': stats.page_views,
        'Blocked Words': stats.blocked_words_count,
        'Total Puzzles': stats.total_puzzles,
      }" :key="label" class="flex justify-between py-2 px-3 rounded" :style="{ borderBottom: '1px solid var(--color-border)' }">
        <span class="text-sm font-medium" :style="{ color: 'var(--color-text-secondary)' }">{{ label }}</span>
        <span class="text-sm" :style="{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }">{{ value }}</span>
      </div>
    </div>

    <!-- Achievements daily summary -->
    <div class="mt-6">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold" :style="{ color: 'var(--color-text-primary)' }">Rank Achievements</h3>
        <div class="flex gap-1">
          <button
            v-for="d in [7, 30, 90]"
            :key="d"
            class="px-2 py-0.5 rounded text-xs"
            :style="{
              background: achDays === d ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
              color: achDays === d ? 'white' : 'var(--color-text-secondary)',
              border: '1px solid ' + (achDays === d ? 'var(--color-accent)' : 'var(--color-border)'),
              cursor: 'pointer',
            }"
            @click="fetchAchievements(d)"
          >{{ d }}d</button>
        </div>
      </div>

      <div v-if="achLoading" class="text-center py-4 text-sm" :style="{ color: 'var(--color-text-secondary)' }">Loading...</div>
      <div v-else-if="achievements" class="overflow-x-auto">
        <table class="w-full text-xs" :style="{ fontFamily: 'var(--font-mono)', borderCollapse: 'collapse' }">
          <thead>
            <tr>
              <th class="text-left py-1 px-1" :style="{ color: 'var(--color-text-secondary)', borderBottom: '1px solid var(--color-border)' }">Date</th>
              <th
                v-for="r in RANK_COLS"
                :key="r"
                class="text-right py-1 px-1"
                :style="{ color: 'var(--color-text-secondary)', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap' }"
              >{{ r }}</th>
              <th class="text-right py-1 px-1 font-bold" :style="{ color: 'var(--color-text-primary)', borderBottom: '1px solid var(--color-border)' }">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="day in achievements.daily" :key="day.date">
              <td class="py-0.5 px-1" :style="{ color: 'var(--color-text-secondary)', borderBottom: '1px solid var(--color-border)' }">{{ day.date.slice(5) }}</td>
              <td
                v-for="r in RANK_COLS"
                :key="r"
                class="text-right py-0.5 px-1"
                :style="{
                  color: day.counts[r] > 0 ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)',
                  borderBottom: '1px solid var(--color-border)',
                }"
              >{{ day.counts[r] }}</td>
              <td class="text-right py-0.5 px-1 font-bold" :style="{ color: day.total > 0 ? 'var(--color-accent)' : 'var(--color-text-tertiary)', borderBottom: '1px solid var(--color-border)' }">{{ day.total }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td class="py-1 px-1 font-bold" :style="{ color: 'var(--color-text-primary)', borderTop: '2px solid var(--color-border)' }">Total</td>
              <td
                v-for="r in RANK_COLS"
                :key="r"
                class="text-right py-1 px-1 font-bold"
                :style="{ color: achievements.totals[r] > 0 ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)', borderTop: '2px solid var(--color-border)' }"
              >{{ achievements.totals[r] }}</td>
              <td class="text-right py-1 px-1 font-bold" :style="{ color: 'var(--color-accent)', borderTop: '2px solid var(--color-border)' }">{{ Object.values(achievements.totals).reduce((a, b) => a + b, 0) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  </div>
</template>
