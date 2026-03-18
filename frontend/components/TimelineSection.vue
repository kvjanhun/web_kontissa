<script setup>
const props = defineProps({
  section: { type: Object, required: true },
  delay: { type: Number, default: 0 }
})

const entries = computed(() => {
  return props.section.content.split('\n')
    .map(line => {
      const parts = line.split('|').map(s => s.trim())
      if (parts.length < 2 || !parts[0]) return null
      let formattedDate = parts[0]
      try {
        const d = new Date(parts[0] + 'T00:00:00')
        formattedDate = d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
      } catch {}
      return { date: formattedDate, title: parts[1] || '', description: parts[2] || '' }
    })
    .filter(Boolean)
})

const loopedEntries = computed(() => [...entries.value, ...entries.value])

const windowRef = ref(null)
const trackRef = ref(null)
const offset = ref(0)
const hovered = ref(false)

const SPEED = 14 // px/s

let rafId = null
let prevTime = null
let touchY = null

function half() {
  return trackRef.value ? trackRef.value.scrollHeight / 2 : 0
}

function wrap() {
  const h = half()
  if (!h) return
  if (offset.value >= h) offset.value -= h
  if (offset.value < 0) offset.value += h
}

function tick(time) {
  if (prevTime !== null && !hovered.value) {
    offset.value += SPEED * (time - prevTime) / 1000
    wrap()
  }
  prevTime = time
  rafId = requestAnimationFrame(tick)
}

onMounted(() => {
  rafId = requestAnimationFrame(tick)
  // touchmove must be non-passive to call preventDefault
  windowRef.value?.addEventListener('touchmove', onTouchMove, { passive: false })
})
onUnmounted(() => {
  if (rafId) cancelAnimationFrame(rafId)
  windowRef.value?.removeEventListener('touchmove', onTouchMove)
})

// Only pause auto-scroll for mouse pointer, not touch taps
function onPointerEnter(e) {
  if (e.pointerType === 'mouse') hovered.value = true
}
function onPointerLeave(e) {
  if (e.pointerType === 'mouse') { hovered.value = false; prevTime = null }
}

function onWheel(e) {
  e.preventDefault()
  offset.value += e.deltaY * 0.5
  wrap()
}

function onTouchStart(e) {
  touchY = e.touches[0].clientY
}
function onTouchMove(e) {
  if (touchY === null) return
  e.preventDefault()
  offset.value += touchY - e.touches[0].clientY
  touchY = e.touches[0].clientY
  wrap()
}
function onTouchEnd() {
  touchY = null
}
</script>

<template>
  <div
    class="rounded-xl px-5 pt-3 pb-3 fade-in"
    :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', animationDelay: delay + 'ms' }"
  >
    <h2 class="text-sm font-bold uppercase tracking-wider mb-2" :style="{ color: 'var(--color-accent, #ff643e)' }">
      {{ section.title }}
    </h2>

    <div
      ref="windowRef"
      class="tl-window"
      @pointerenter="onPointerEnter"
      @pointerleave="onPointerLeave"
      @wheel="onWheel"
      @touchstart.passive="onTouchStart"
      @touchend.passive="onTouchEnd"
    >
      <div ref="trackRef" :style="{ transform: `translateY(-${offset}px)` }">
        <div v-for="(entry, i) in loopedEntries" :key="i" class="tl-entry">
          <div class="tl-dot" :style="{ backgroundColor: 'var(--color-accent, #ff643e)' }"></div>
          <div>
            <div class="tl-title" :style="{ color: 'var(--color-text-primary)' }">{{ entry.title }}</div>
            <div class="tl-sub">
              <span class="tl-date" :style="{ color: 'var(--color-accent, #ff643e)' }">{{ entry.date }}</span>
              <span v-if="entry.description" :style="{ color: 'var(--color-text-secondary)' }"> · {{ entry.description }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tl-window {
  height: 9.5rem;
  overflow: hidden;
  cursor: ns-resize;
  mask-image: linear-gradient(to bottom, transparent, black 18%, black 82%, transparent);
  -webkit-mask-image: linear-gradient(to bottom, transparent, black 18%, black 82%, transparent);
}
.tl-entry {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding-bottom: 0.7rem;
}
.tl-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 0.3rem;
  flex-shrink: 0;
}
.tl-title {
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.3;
}
.tl-sub {
  font-size: 0.68rem;
  line-height: 1.35;
  margin-top: 0.05rem;
}
.tl-date {
  font-weight: 600;
}
.fade-in {
  animation: fadeSlideUp 0.5s ease both;
}
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
