<script setup>
const props = defineProps({
  section: { type: Object, required: true },
  delay: { type: Number, default: 0 },
  compact: { type: Boolean, default: false }
})

const { data: stats, pending, error } = await useFetch('/api/project-stats', {
  key: 'project-stats',
  default: () => null,
})

const activeSince = computed(() => {
  if (!stats.value?.created_at) return null
  try {
    const d = new Date(stats.value.created_at + 'T00:00:00')
    return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  } catch {
    return stats.value.created_at
  }
})

const repoSize = computed(() => {
  const kb = stats.value?.size_kb
  if (!kb) return null
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`
})
</script>

<template>
  <div
    class="rounded-xl p-5 fade-in"
    :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', animationDelay: delay + 'ms' }"
  >
    <h2 class="text-sm font-bold uppercase tracking-wider mb-4" :style="{ color: 'var(--color-accent, #ff643e)' }">
      {{ section.title }}
    </h2>

    <p v-if="section.content" class="text-sm mb-4 leading-relaxed" :style="{ color: 'var(--color-text-secondary)' }">
      {{ section.content }}
    </p>

    <!-- Loading -->
    <div v-if="pending" :class="compact ? 'stats-grid-compact' : 'stats-grid'">
      <div v-for="n in 4" :key="n" class="animate-pulse rounded-lg" :class="compact ? 'h-12' : 'h-16'" :style="{ backgroundColor: 'var(--color-bg-tertiary)' }"></div>
    </div>

    <!-- Error -->
    <p v-else-if="error || !stats" class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">Stats unavailable</p>

    <!-- Stats grid -->
    <div v-else :class="compact ? 'stats-grid-compact' : 'stats-grid'">
      <div v-if="stats.commits" class="stat-item rounded-lg" :class="compact ? 'p-2' : 'p-3'" :style="{ backgroundColor: 'var(--color-bg-tertiary)' }">
        <div class="font-bold" :class="compact ? 'val-compact' : 'val'" :style="{ color: 'var(--color-text-primary)' }">{{ stats.commits }}</div>
        <div class="lbl" :style="{ color: 'var(--color-text-secondary)' }">Commits</div>
      </div>
      <div v-if="activeSince" class="stat-item rounded-lg" :class="compact ? 'p-2' : 'p-3'" :style="{ backgroundColor: 'var(--color-bg-tertiary)' }">
        <div class="font-bold" :class="compact ? 'val-compact' : 'val'" :style="{ color: 'var(--color-text-primary)' }">{{ activeSince }}</div>
        <div class="lbl" :style="{ color: 'var(--color-text-secondary)' }">Active since</div>
      </div>
      <div v-if="repoSize" class="stat-item rounded-lg" :class="compact ? 'p-2' : 'p-3'" :style="{ backgroundColor: 'var(--color-bg-tertiary)' }">
        <div class="font-bold" :class="compact ? 'val-compact' : 'val'" :style="{ color: 'var(--color-text-primary)' }">{{ repoSize }}</div>
        <div class="lbl" :style="{ color: 'var(--color-text-secondary)' }">Repo size</div>
      </div>
      <div v-if="stats.languages?.length" class="stat-item rounded-lg" :class="compact ? 'p-2' : 'p-3'" :style="{ backgroundColor: 'var(--color-bg-tertiary)' }">
        <div class="font-semibold val-lang" :style="{ color: 'var(--color-text-primary)' }">{{ stats.languages.slice(0, 3).join(' · ') }}</div>
        <div class="lbl" :style="{ color: 'var(--color-text-secondary)' }">Languages</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}
@media (min-width: 640px) {
  .stats-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
.stats-grid-compact {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}
.val {
  font-size: 1.25rem;
  line-height: 1.2;
}
.val-compact {
  font-size: 1rem;
  line-height: 1.2;
}
.lbl {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 0.2rem;
}
.val-lang {
  font-size: 0.8rem;
  line-height: 1.3;
}
.fade-in {
  animation: fadeSlideUp 0.5s ease both;
}
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
