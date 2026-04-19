<script setup>
defineProps({
  fill: { type: Boolean, default: false },
})

const {
  outputLines,
  currentInput,
  autoTypedText,
  isBooting,
  isProcessing,
  executeCommand,
  runBootSequence,
  runChoreography,
  stopChoreography,
  historyUp,
  historyDown,
} = useTerminal()

const hiddenInput = ref(null)
const scrollContainer = ref(null)

function focusInput() {
  hiddenInput.value?.focus()
}

async function handleEnter() {
  if (isBooting.value || isProcessing.value) return
  if (stopChoreography()) return
  const cmd = currentInput.value
  currentInput.value = ''
  await executeCommand(cmd)
}

function handleKeydown(e) {
  if (e.key === 'ArrowUp') {
    stopChoreography()
    e.preventDefault()
    historyUp()
  } else if (e.key === 'ArrowDown') {
    stopChoreography()
    e.preventDefault()
    historyDown()
  } else if (e.key !== 'Enter') {
    stopChoreography()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  })
}

watch(outputLines, scrollToBottom, { deep: true })

onMounted(async () => {
  const firstBoot = !outputLines.value.length
  await runBootSequence()
  scrollToBottom()
  if (window.matchMedia('(pointer: fine)').matches) {
    focusInput()
  }
  if (firstBoot) {
    runChoreography()
  }
})

onBeforeUnmount(() => {
  stopChoreography()
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
        class="font-mono text-sm text-white p-4 overflow-y-scroll overflow-x-auto"
        :class="fill ? 'h-full' : 'h-[360px]'"
        style="-ms-overflow-style: none; scrollbar-width: none;"
        role="log"
        aria-live="polite"
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
            <span class="text-white whitespace-pre">{{ autoTypedText || currentInput }}</span>
            <span class="block self-center h-[1em] w-[0.6em] cursor-blink shrink-0"></span>
          </div>
        </div>
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
