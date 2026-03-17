<script setup>
const props = defineProps({
  title: { type: String, default: '' },
  summary: { type: String, default: '' },
  accent: { type: Boolean, default: false },
  expandable: { type: Boolean, default: false },
  startOpen: { type: Boolean, default: false },
  delay: { type: Number, default: 0 }
})

const isOpen = ref(props.startOpen || !props.expandable)
const visible = ref(false)
const cardRef = ref(null)

function toggle() {
  if (!props.expandable) return
  isOpen.value = !isOpen.value
}

function close() {
  if (props.expandable) {
    isOpen.value = false
  }
}

function onClickOutside(e) {
  if (isOpen.value && cardRef.value && !cardRef.value.contains(e.target)) {
    close()
  }
}

function onKeydown(e) {
  if (e.key === 'Escape' && isOpen.value) {
    close()
  }
}

onMounted(() => {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (prefersReducedMotion) {
    visible.value = true
    if (props.expandable) {
      document.addEventListener('click', onClickOutside)
      document.addEventListener('keydown', onKeydown)
    }
    return
  }

  const observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => { visible.value = true }, props.delay)
        observer.disconnect()
      }
    },
    { threshold: 0.1 }
  )
  if (cardRef.value) observer.observe(cardRef.value)

  if (props.expandable) {
    document.addEventListener('click', onClickOutside)
    document.addEventListener('keydown', onKeydown)
  }
})

onUnmounted(() => {
  if (props.expandable) {
    document.removeEventListener('click', onClickOutside)
    document.removeEventListener('keydown', onKeydown)
  }
})
</script>

<template>
  <article
    ref="cardRef"
    class="about-card overflow-hidden transition-all duration-500"
    :class="{
      'about-card--visible': visible,
      'about-card--accent': accent,
      'about-card--expandable': expandable,
      'about-card--open': expandable && isOpen,
      'rounded-xl': true,
    }"
    :style="{
      background: 'var(--color-bg-secondary)',
      border: '1px solid var(--color-border)',
      cursor: expandable ? 'pointer' : 'default'
    }"
    @click="expandable && toggle()"
  >
    <component
      :is="expandable ? 'button' : 'div'"
      class="w-full text-left"
      :style="{ background: 'transparent' }"
      :aria-expanded="expandable ? isOpen : undefined"
      @click.stop="expandable && toggle()"
    >
      <div v-if="title" class="px-5 pt-4" :class="{ 'pb-3': !expandable || isOpen, 'pb-4': expandable && !isOpen }">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-base font-semibold tracking-wide uppercase m-0" :style="{ color: 'var(--color-accent, #ff643e)' }">
            {{ title }}
          </h2>
          <svg
            v-if="expandable"
            class="shrink-0 transition-transform duration-300"
            :class="{ 'rotate-180': isOpen }"
            width="14" height="14" viewBox="0 0 16 16" fill="none"
            :style="{ color: 'var(--color-text-tertiary)' }"
          >
            <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <p
          v-if="expandable && !isOpen && summary"
          class="text-xs mt-1 mb-0 line-clamp-2"
          :style="{ color: 'var(--color-text-tertiary)' }"
        >{{ summary }}</p>
      </div>
    </component>

    <!-- Content -->
    <div v-if="!expandable || isOpen" class="px-5 pb-5" :class="{ 'pt-4': !title }" @click.stop>
      <slot />
    </div>
  </article>
</template>

<style scoped>
.about-card {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease, box-shadow 0.2s ease;
  position: relative;
}
.about-card--visible {
  opacity: 1;
  transform: translateY(0);
}
.about-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}
.about-card--accent {
  border-color: color-mix(in srgb, var(--color-accent, #ff643e) 30%, transparent) !important;
}
</style>
