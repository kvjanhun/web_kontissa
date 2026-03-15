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
  if (props.expandable) {
    isOpen.value = !isOpen.value
  }
}

onMounted(() => {
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
})
</script>

<template>
  <article
    ref="cardRef"
    class="about-card rounded-xl overflow-hidden transition-all duration-500"
    :class="{
      'about-card--visible': visible,
      'about-card--accent': accent,
      'about-card--expandable': expandable
    }"
    :style="{
      background: 'var(--color-bg-secondary)',
      border: '1px solid var(--color-border)'
    }"
  >
    <component
      :is="expandable ? 'button' : 'div'"
      class="w-full text-left"
      :class="{ 'cursor-pointer': expandable }"
      :style="{ background: 'transparent' }"
      :aria-expanded="expandable ? isOpen : undefined"
      @click="toggle"
    >
      <div v-if="title" class="px-5 pt-4" :class="{ 'pb-3': !expandable || isOpen, 'pb-4': expandable && !isOpen }">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-base font-semibold tracking-wide uppercase m-0" :style="{ color: 'var(--color-accent, #ff643e)' }">
            {{ title }}
          </h2>
          <div v-if="expandable" class="flex items-center gap-1.5">
            <span
              v-if="!isOpen"
              class="text-xs"
              :style="{ color: 'var(--color-text-tertiary)' }"
            >{{ summary || 'Read more' }}</span>
            <svg
              class="shrink-0 transition-transform duration-300"
              :class="{ 'rotate-180': isOpen }"
              width="14" height="14" viewBox="0 0 16 16" fill="none"
              :style="{ color: 'var(--color-text-tertiary)' }"
            >
              <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </div>
      </div>
    </component>

    <div
      v-if="expandable"
      class="about-card__body"
      :class="{ 'about-card__body--open': isOpen }"
    >
      <div class="px-5 pb-5 overflow-hidden">
        <slot />
      </div>
    </div>
    <div v-else class="px-5 pb-5" :class="{ 'pt-4': !title }">
      <slot />
    </div>
  </article>
</template>

<style scoped>
.about-card {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease, box-shadow 0.2s ease;
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

.about-card__body {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.3s ease;
}
.about-card__body > div {
  overflow: hidden;
}
.about-card__body--open {
  grid-template-rows: 1fr;
}
</style>
