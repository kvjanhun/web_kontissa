<script setup>
const navigate = inject('adminNavigate', () => {})

const health = ref(null)
const projects = ref([])
const totalViews = ref(null)

onMounted(() => {
  loadHealth()
  loadProjects()
  loadViews()
})

async function loadHealth() {
  try {
    const res = await fetch('/api/admin/health')
    if (res.ok) health.value = await res.json()
  } catch { /* ignore */ }
}
async function loadProjects() {
  try {
    const res = await fetch('/api/admin/projects')
    if (res.ok) projects.value = await res.json()
  } catch { /* ignore */ }
}
async function loadViews() {
  try {
    const res = await fetch('/api/pageviews')
    if (res.ok) {
      const rows = await res.json()
      totalViews.value = rows.reduce((sum, r) => sum + (r.count || 0), 0)
    }
  } catch { /* ignore */ }
}

const publishedCount = computed(() => projects.value.filter(p => !p.hidden).length)
const hiddenCount = computed(() => projects.value.filter(p => p.hidden).length)

function formatBytes(bytes) {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0, val = bytes
  while (val >= 1024 && i < units.length - 1) { val /= 1024; i++ }
  return `${val.toFixed(1)} ${units[i]}`
}
function formatUptime(seconds) {
  if (!seconds) return '—'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  return d ? `${d}d ${h}h` : `${h}h`
}

const stats = computed(() => [
  { icon: 'flat-color-icons:gallery', value: String(projects.value.length), label: 'Projects' },
  { icon: 'flat-color-icons:combo-chart', value: totalViews.value != null ? totalViews.value.toLocaleString() : '—', label: 'Page views · total' },
  { icon: 'flat-color-icons:database', value: formatBytes(health.value?.db_size_bytes), label: 'Database size' },
  { icon: 'flat-color-icons:ok', value: formatUptime(health.value?.uptime_seconds), label: 'Uptime' },
])
</script>

<template>
  <div class="dash">
    <div class="dash__head">
      <div>
        <h1 class="dash__title">Welcome back, Konsta</h1>
        <p class="dash__sub">Here's what's happening across erez.ac.</p>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="dash__stats">
      <div v-for="s in stats" :key="s.label" class="card stat">
        <span class="stat__icon"><Icon :name="s.icon" /></span>
        <div class="stat__value">{{ s.value }}</div>
        <div class="stat__label">{{ s.label }}</div>
      </div>
    </div>

    <div class="dash__grid">
      <!-- Grafana -->
      <a href="/logs/" target="_blank" rel="noopener noreferrer" class="card grafana">
        <span class="grafana__icon"><Icon name="flat-color-icons:combo-chart" /></span>
        <div class="grafana__body">
          <h3 class="grafana__title">Observability — Grafana</h3>
          <p class="grafana__text">Logs, metrics and dashboards (Loki · Prometheus). Opens the Grafana console.</p>
        </div>
        <span class="grafana__go"><Icon name="flat-color-icons:globe" /></span>
      </a>

      <!-- Content overview -->
      <div class="card overview">
        <div class="overview__head">
          <h3 class="overview__title"><Icon name="flat-color-icons:document" /> Content overview</h3>
          <button class="overview__manage" @click="navigate('home')">Edit →</button>
        </div>
        <div class="overview__grid">
          <button class="ov-cell" @click="navigate('projects')">
            <div class="ov-cell__num">{{ publishedCount }}</div>
            <div class="ov-cell__label"><Icon name="flat-color-icons:ok" /> Live projects</div>
          </button>
          <button class="ov-cell" @click="navigate('projects')">
            <div class="ov-cell__num">{{ hiddenCount }}</div>
            <div class="ov-cell__label"><Icon name="flat-color-icons:no-idea" /> Hidden</div>
          </button>
          <div class="ov-cell ov-cell--static">
            <div class="ov-cell__num">2</div>
            <div class="ov-cell__label"><Icon name="flat-color-icons:globe" /> Locales</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dash { max-width: 1100px; margin: 0 auto; }
.dash__head { margin-bottom: 22px; }
.dash__title { margin: 0 0 4px; font-size: 25px; font-weight: 600; letter-spacing: -0.02em; }
.dash__sub { margin: 0; font-size: 14px; color: var(--as-tx-2); }

.card {
  background: var(--as-panel);
  border: 1px solid var(--as-line);
  border-radius: 13px;
  padding: 18px;
}

.dash__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 14px;
}
.stat__icon { font-size: 24px; display: inline-flex; margin-bottom: 12px; }
.stat__value { font-size: 26px; font-weight: 600; letter-spacing: -0.02em; line-height: 1; }
.stat__label { font-size: 12.5px; color: var(--as-tx-2); margin-top: 6px; }

.dash__grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 14px; }

.grafana {
  display: flex;
  align-items: center;
  gap: 16px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.grafana:hover { border-color: var(--as-accent); box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05); }
.grafana__icon { font-size: 34px; display: inline-flex; flex: none; }
.grafana__body { flex: 1; min-width: 0; }
.grafana__title { margin: 0 0 4px; font-size: 15px; font-weight: 600; }
.grafana__text { margin: 0; font-size: 13px; color: var(--as-tx-2); line-height: 1.5; }
.grafana__go { font-size: 20px; color: var(--as-tx-3); flex: none; }

.overview__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.overview__title { margin: 0; font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.overview__manage { font-size: 12.5px; color: var(--as-accent); background: none; border: none; cursor: pointer; font-weight: 600; }
.overview__grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.ov-cell {
  background: #f7f7f3;
  border: none;
  border-radius: 9px;
  padding: 13px;
  text-align: left;
  cursor: pointer;
  font: inherit;
}
.ov-cell--static { cursor: default; }
.ov-cell:not(.ov-cell--static):hover { background: #efefe9; }
.ov-cell__num { font-size: 22px; font-weight: 600; }
.ov-cell__label { font-size: 12px; color: var(--as-tx-2); display: flex; align-items: center; gap: 5px; margin-top: 3px; }

@media (max-width: 900px) {
  .dash__stats { grid-template-columns: repeat(2, 1fr); }
  .dash__grid { grid-template-columns: 1fr; }
}
</style>
