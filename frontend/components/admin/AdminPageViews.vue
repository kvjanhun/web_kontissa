<script setup>
import { ref, computed, onMounted } from 'vue'

const pageViews = ref([])
const events = ref(null)
const loading = ref(true)
const selectedDays = ref(7)
const enabledPaths = ref(new Set())

const PATH_COLORS = ['#ff643e', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

onMounted(() => loadAll())

async function loadAll() {
  loading.value = true
  await Promise.all([loadSummary(), loadEvents()])
  loading.value = false
}

async function loadSummary() {
  try {
    const res = await fetch('/api/pageviews')
    if (res.ok) pageViews.value = await res.json()
  } catch { /* ignore */ }
}

async function loadEvents() {
  try {
    const res = await fetch(`/api/pageviews/events?days=${selectedDays.value}`)
    if (res.ok) {
      const data = await res.json()
      events.value = data
      enabledPaths.value = new Set(data.paths)
    }
  } catch { /* ignore */ }
}

function selectDays(d) {
  selectedDays.value = d
  loadEvents()
}

function togglePath(path) {
  const s = new Set(enabledPaths.value)
  if (s.has(path)) s.delete(path)
  else s.add(path)
  enabledPaths.value = s
}

function pathColor(path) {
  if (!events.value) return PATH_COLORS[0]
  const idx = events.value.paths.indexOf(path)
  return PATH_COLORS[idx % PATH_COLORS.length]
}

// Chart dimensions
const W = 800
const H = 280
const PAD = { top: 20, right: 20, bottom: 40, left: 45 }
const chartW = W - PAD.left - PAD.right
const chartH = H - PAD.top - PAD.bottom

const maxCount = computed(() => {
  if (!events.value) return 0
  let max = 0
  for (const day of events.value.series) {
    for (const [path, count] of Object.entries(day.counts)) {
      if (enabledPaths.value.has(path) && count > max) max = count
    }
  }
  return max || 1
})

const yTicks = computed(() => {
  const m = maxCount.value
  if (m <= 5) return Array.from({ length: m + 1 }, (_, i) => i)
  const step = Math.ceil(m / 5)
  const ticks = []
  for (let i = 0; i <= m; i += step) ticks.push(i)
  if (ticks[ticks.length - 1] < m) ticks.push(m)
  return ticks
})

const xLabels = computed(() => {
  if (!events.value) return []
  const series = events.value.series
  const step = Math.max(1, Math.floor(series.length / 7))
  const labels = []
  for (let i = 0; i < series.length; i += step) {
    labels.push({ idx: i, label: series[i].date.slice(5) }) // MM-DD
  }
  // Always include last
  const last = series.length - 1
  if (labels.length === 0 || labels[labels.length - 1].idx !== last) {
    labels.push({ idx: last, label: series[last].date.slice(5) })
  }
  return labels
})

function polyline(path) {
  if (!events.value) return ''
  const series = events.value.series
  const len = series.length
  if (len === 0) return ''
  const m = maxCount.value
  return series.map((day, i) => {
    const x = PAD.left + (len > 1 ? (i / (len - 1)) * chartW : chartW / 2)
    const count = day.counts[path] || 0
    const y = PAD.top + chartH - (count / m) * chartH
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

function xPos(i) {
  const len = events.value?.series.length || 1
  return PAD.left + (len > 1 ? (i / (len - 1)) * chartW : chartW / 2)
}

function yPos(val) {
  return PAD.top + chartH - (val / maxCount.value) * chartH
}

function formatDate(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}
</script>

<template>
  <div>
    <div v-if="loading" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">Loading...</div>
    <template v-else>
      <!-- Period selector -->
      <div class="flex gap-2 mb-4" v-if="events">
        <button
          v-for="d in [7, 30, 90]"
          :key="d"
          class="px-3 py-1 rounded text-sm font-medium"
          :style="{
            background: selectedDays === d ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
            color: selectedDays === d ? 'white' : 'var(--color-text-secondary)',
            border: '1px solid ' + (selectedDays === d ? 'var(--color-accent)' : 'var(--color-border)'),
            cursor: 'pointer',
          }"
          @click="selectDays(d)"
        >{{ d }}d</button>
      </div>

      <!-- SVG Chart -->
      <div v-if="events && events.series.length > 0" class="mb-4 overflow-x-auto">
        <svg :viewBox="`0 0 ${W} ${H}`" class="w-full" style="min-width: 400px;">
          <!-- Grid lines -->
          <line
            v-for="tick in yTicks"
            :key="'grid-' + tick"
            :x1="PAD.left"
            :y1="yPos(tick)"
            :x2="W - PAD.right"
            :y2="yPos(tick)"
            stroke="var(--color-border)"
            stroke-width="0.5"
          />

          <!-- Y-axis labels -->
          <text
            v-for="tick in yTicks"
            :key="'ylabel-' + tick"
            :x="PAD.left - 8"
            :y="yPos(tick) + 4"
            text-anchor="end"
            fill="var(--color-text-tertiary)"
            font-size="11"
          >{{ tick }}</text>

          <!-- X-axis labels -->
          <text
            v-for="lbl in xLabels"
            :key="'xlabel-' + lbl.idx"
            :x="xPos(lbl.idx)"
            :y="H - 8"
            text-anchor="middle"
            fill="var(--color-text-tertiary)"
            font-size="11"
          >{{ lbl.label }}</text>

          <!-- Data lines -->
          <polyline
            v-for="path in events.paths"
            :key="path"
            v-show="enabledPaths.has(path)"
            :points="polyline(path)"
            fill="none"
            :stroke="pathColor(path)"
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
        </svg>
      </div>

      <!-- Path toggle chips -->
      <div v-if="events && events.paths.length > 0" class="flex flex-wrap gap-2 mb-6">
        <button
          v-for="path in events.paths"
          :key="path"
          class="px-3 py-1 rounded-full text-xs font-medium"
          :style="{
            background: enabledPaths.has(path) ? pathColor(path) + '20' : 'var(--color-bg-secondary)',
            color: enabledPaths.has(path) ? pathColor(path) : 'var(--color-text-tertiary)',
            border: '1px solid ' + (enabledPaths.has(path) ? pathColor(path) : 'var(--color-border)'),
            cursor: 'pointer',
          }"
          @click="togglePath(path)"
        >{{ path }}</button>
      </div>

      <!-- Summary table -->
      <div v-if="pageViews.length === 0" class="text-center py-4" :style="{ color: 'var(--color-text-secondary)' }">No page views recorded yet.</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr :style="{ borderBottom: '1px solid var(--color-border)' }">
            <th class="text-left py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Path</th>
            <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Views</th>
            <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">First Seen</th>
            <th class="text-right py-2 px-3 font-medium" :style="{ color: 'var(--color-text-secondary)' }">Last Updated</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pv in pageViews" :key="pv.path" :style="{ borderBottom: '1px solid var(--color-border)' }">
            <td class="py-2 px-3" :style="{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }">{{ pv.path }}</td>
            <td class="text-right py-2 px-3" :style="{ color: 'var(--color-text-primary)' }">{{ pv.count }}</td>
            <td class="text-right py-2 px-3 text-xs" :style="{ color: 'var(--color-text-secondary)' }">{{ formatDate(pv.created_at) }}</td>
            <td class="text-right py-2 px-3 text-xs" :style="{ color: 'var(--color-text-secondary)' }">{{ formatDate(pv.updated_at) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>
