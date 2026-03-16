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
const dropdownMaxHeight = ref('60vh')
const dropdownRef = ref(null)

async function toggle() {
  if (!props.expandable) return
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    await nextTick()
    if (!dropdownRef.value || !cardRef.value) return
    const dropdownHeight = dropdownRef.value.scrollHeight
    dropdownMaxHeight.value = dropdownHeight + 'px'

    // Pad about-page only by how much the dropdown extends past its natural bottom
    const container = cardRef.value.closest('.about-page')
    if (container) {
      const cardAbsBottom = cardRef.value.getBoundingClientRect().bottom + window.scrollY
      const containerAbsBottom = container.getBoundingClientRect().bottom + window.scrollY
      const overflow = (cardAbsBottom + dropdownHeight) - containerAbsBottom + 16
      if (overflow > 0) container.style.paddingBottom = overflow + 'px'
    }
  } else {
    const container = cardRef.value?.closest('.about-page')
    if (container) container.style.paddingBottom = ''
  }
}

function close() {
  if (props.expandable) {
    isOpen.value = false
    const container = cardRef.value?.closest('.about-page')
    if (container) container.style.paddingBottom = ''
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
    class="about-card overflow-visible transition-all duration-500"
    :class="{
      'about-card--visible': visible,
      'about-card--accent': accent,
      'about-card--expandable': expandable,
      'about-card--open': expandable && isOpen,
      'rounded-xl': !(expandable && isOpen),
      'rounded-t-xl rounded-b-none': expandable && isOpen,
    }"
    :style="{
      background: 'var(--color-bg-secondary)',
      border: '1px solid var(--color-border)',
      borderBottom: expandable && isOpen ? 'none' : '1px solid var(--color-border)',
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

    <!-- Expandable: absolute overlay so it doesn't push layout -->
    <div
      v-if="expandable && isOpen"
      ref="dropdownRef"
      class="about-card__dropdown"
      @click.stop
      :style="{
        background: 'var(--color-bg-secondary)',
        borderLeft: '1px solid var(--color-border)',
        borderRight: '1px solid var(--color-border)',
        borderBottom: '1px solid var(--color-border)',
        maxHeight: dropdownMaxHeight
      }"
    >
      <div class="px-5 py-4">
        <slot />
      </div>
    </div>

    <!-- Non-expandable: normal flow -->
    <div v-if="!expandable" class="px-5 pb-5" :class="{ 'pt-4': !title }">
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
.about-card--open {
  z-index: 10;
}

.about-card__dropdown {
  position: absolute;
  top: 100%;
  left: -1px;
  right: -1px;
  border-radius: 0 0 0.75rem 0.75rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  overflow-y: auto;
  animation: dropdownIn 0.2s ease;
}

@keyframes dropdownIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
