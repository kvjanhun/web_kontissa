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
  <div class="w-4/5 h-68 max-sm:h-32 mb-8 shadow-[2px_4px_5px_rgba(0,0,0,0.5)]">
    <div class="flex w-full h-9 items-center justify-between px-4 rounded-t-md term-bar-bg">
      <div>&nbsp;</div>
      <span class="text-[#d5d0ce] text-sm leading-none">konsta@erez.ac:~</span>
      <div class="flex items-center gap-1.5 font-mono">
        <button class="text-black text-[0.66rem] size-4 border-none rounded-full term-btn-bg">&#x2013;</button>
        <button class="text-black text-[0.66rem] size-4 border-none rounded-full term-btn-bg">&#x2610;</button>
        <button class="text-black text-[0.66rem] size-4 border-none rounded-full term-btn-close">&#x2715;</button>
      </div>
    </div>
    <div class="bg-term-bg font-mono text-sm text-white block p-0.5 -mt-px h-[calc(100%-2.4rem)]">
      <div class="flex font-mono">
        <span class="flex ml-1 text-gray-300">
          <span class="text-term-user">konsta@erez.ac</span>
          <span>:</span>
          <span class="text-term-dir">~</span>
          <span class="mr-[1ch]">$</span>
        </span>
        <span class="text-white">{{ typedCommand }}</span>
      </div>
      <pre class="font-mono text-white whitespace-pre-wrap m-0">{{ cowsayOutput }}</pre>
      <div class="flex font-mono" v-if="showNewPrompt">
        <span class="flex ml-1 text-gray-300">
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
