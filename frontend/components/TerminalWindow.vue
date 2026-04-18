<script setup>
defineProps({
  fill: { type: Boolean, default: false },
})

const {
  outputLines,
  currentInput,
  isBooting,
  isProcessing,
  executeCommand,
  runBootSequence,
  autoTypeCommand,
  historyUp,
  historyDown,
} = useTerminal()

const hiddenInput = ref(null)
const scrollContainer = ref(null)
const scrollTop = ref(0)
const scrollHeight = ref(1)
const clientHeight = ref(1)

const canScroll = computed(() => scrollHeight.value > clientHeight.value)
const thumbHeight = computed(() => {
  if (!canScroll.value) return 0
  return Math.max(24, (clientHeight.value / scrollHeight.value) * clientHeight.value)
})
const thumbTop = computed(() => {
  if (!canScroll.value) return 0
  const maxScroll = scrollHeight.value - clientHeight.value
  const maxThumb = clientHeight.value - thumbHeight.value
  return maxScroll > 0 ? (scrollTop.value / maxScroll) * maxThumb : 0
})

function updateScrollMetrics() {
  const el = scrollContainer.value
  if (!el) return
  scrollTop.value = el.scrollTop
  scrollHeight.value = el.scrollHeight
  clientHeight.value = el.clientHeight
}

function focusInput() {
  hiddenInput.value?.focus()
}

async function handleEnter() {
  if (isBooting.value || isProcessing.value) return
  const cmd = currentInput.value
  currentInput.value = ''
  await executeCommand(cmd)
}

function handleKeydown(e) {
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    historyUp()
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    historyDown()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
      updateScrollMetrics()
    }
  })
}

let resizeObserver = null

watch(outputLines, scrollToBottom, { deep: true })

onMounted(async () => {
  if (scrollContainer.value) {
    resizeObserver = new ResizeObserver(updateScrollMetrics)
    resizeObserver.observe(scrollContainer.value)
  }
  const firstBoot = !outputLines.value.length
  await runBootSequence()
  scrollToBottom()
  if (window.matchMedia('(pointer: fine)').matches) {
    focusInput()
  }
  if (firstBoot) {
    await autoTypeCommand("cowsay You can type here!")
  }
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})
</script>

<template>
  <div
    class="w-full overflow-hidden"
    :class="fill ? 'flex flex-col h-full' : 'rounded-lg shadow-lg'"
    @click="focusInput"
  >
    <div class="relative bg-term-bg" :class="fill ? 'flex-1 min-h-0' : ''">
      <!-- Scrollable content -->
      <div
        ref="scrollContainer"
        class="font-mono text-sm text-white p-4 overflow-y-scroll overflow-x-auto pr-6"
        :class="fill ? 'h-full' : 'h-[360px]'"
        style="-ms-overflow-style: none; scrollbar-width: none;"
        role="log"
        aria-live="polite"
        @scroll="updateScrollMetrics"
      >
        <div class="min-w-max">
          <!-- Output lines -->
          <div
            v-for="(line, i) in outputLines"
            :key="i"
            v-html="line.html"
          />

          <!-- Active prompt (when not booting) -->
          <div v-if="!isBooting" class="flex font-mono">
            <span class="flex text-gray-300 shrink-0">
              <span class="text-term-user">konsta@erez.ac</span>
              <span>:</span>
              <span class="text-term-dir">~</span>
              <span class="mr-[1ch]">$</span>
            </span>
            <span class="text-white whitespace-pre">{{ currentInput }}</span>
            <span class="block self-center h-[1em] w-[0.6em] cursor-blink shrink-0"></span>
          </div>
        </div>
      </div>

      <!-- Custom scrollbar track (inside terminal padding) -->
      <div
        class="absolute top-2 bottom-2 right-1.5 w-1.5 rounded-full"
        style="background: #1a1a1a;"
        aria-hidden="true"
      >
        <div
          v-if="canScroll"
          class="w-1.5 rounded-full"
          :style="{
            background: '#555',
            height: thumbHeight + 'px',
            marginTop: thumbTop + 'px',
          }"
        />
      </div>
    </div>

    <!-- Hidden input for keyboard capture -->
    <input
      ref="hiddenInput"
      v-model="currentInput"
      class="sr-only"
      type="text"
      autocapitalize="off"
      autocorrect="off"
      spellcheck="false"
      aria-label="Terminal input"
      @keydown.enter.prevent="handleEnter"
      @keydown="handleKeydown"
    />
  </div>
</template>

<style scoped>
/* Hide native scrollbar across all browsers */
.overflow-y-scroll::-webkit-scrollbar {
  display: none;
}
</style>
