<script setup>
import { ref, onMounted } from 'vue'

const typedCommand = ref('')
const cowsayOutput = ref('')
const showNewPrompt = ref(false)
const commandText = 'cowsay moo'

const typeCommand = (i) => {
  if (i < commandText.length) {
    typedCommand.value += commandText[i]
    setTimeout(() => typeCommand(i + 1), 80)
  } else {
    setTimeout(fetchCowsay, 100)
  }
}

const fetchCowsay = async () => {
  try {
    const res = await fetch('/api/cowsay')
    const data = await res.json()
    cowsayOutput.value = data.output
    showNewPrompt.value = true
  } catch {
    cowsayOutput.value = 'Error fetching cowsay'
  }
}

onMounted(() => {
  setTimeout(() => typeCommand(0), 3000)
})
</script>

<template>
  <div class="w-full rounded-lg overflow-hidden shadow-lg min-h-[280px]">
    <div class="bg-term-bg font-mono text-sm text-white p-4 min-h-[280px]">
      <div class="flex font-mono">
        <span class="flex text-gray-300">
          <span class="text-term-user">konsta@erez.ac</span>
          <span>:</span>
          <span class="text-term-dir">~</span>
          <span class="mr-[1ch]">$</span>
        </span>
        <span class="text-white">{{ typedCommand }}</span>
      </div>
      <pre class="font-mono text-white whitespace-pre-wrap m-0">{{ cowsayOutput }}</pre>
      <div class="flex font-mono" v-if="showNewPrompt">
        <span class="flex text-gray-300">
          <span class="text-term-user">konsta@erez.ac</span>
          <span>:</span>
          <span class="text-term-dir">~</span>
          <span class="mr-[1ch]">$</span>
          <span class="block h-3.5 w-px my-px cursor-blink"></span>
        </span>
      </div>
    </div>
  </div>
</template>
