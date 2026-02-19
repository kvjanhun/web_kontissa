<script setup>
import { ref, onMounted } from 'vue'

const typedCommand = ref('')
const cowsayOutput = ref('')
const typedWeatherCmd = ref('')
const weatherOutput = ref('')
const showWeatherPrompt = ref(false)
const showNewPrompt = ref(false)

const typeText = (text, target, delay = 80) => {
  return new Promise((resolve) => {
    let i = 0
    const step = () => {
      if (i < text.length) {
        target.value += text[i]
        i++
        setTimeout(step, delay)
      } else {
        resolve()
      }
    }
    step()
  })
}

const fetchCowsay = async () => {
  try {
    const res = await fetch('/api/cowsay')
    const data = await res.json()
    cowsayOutput.value = data.output
  } catch {
    cowsayOutput.value = 'Error fetching cowsay'
  }
}

const fetchWeather = async () => {
  try {
    const res = await fetch('/api/weather')
    const data = await res.json()
    if (data.error) {
      weatherOutput.value = '  Weather data unavailable'
      return
    }
    const temp = data.temperature != null ? Math.round(data.temperature) : '?'
    const feels = data.feels_like != null ? Math.round(data.feels_like) : '?'
    const wind = data.wind_speed != null ? data.wind_speed : '?'
    const cond = data.condition || 'N/A'
    const station = data.station || 'Vantaa'
    weatherOutput.value =
      `  ${station}  ${temp}°C (feels like ${feels}°C)\n` +
      `  Wind ${wind} m/s  |  ${cond}`
  } catch {
    weatherOutput.value = '  Weather data unavailable'
  }
}

const runSequence = async () => {
  await typeText('cowsay moo', typedCommand)
  await new Promise((r) => setTimeout(r, 100))
  await fetchCowsay()
  showWeatherPrompt.value = true

  await new Promise((r) => setTimeout(r, 1000))
  await typeText('weather', typedWeatherCmd)
  await new Promise((r) => setTimeout(r, 100))
  await fetchWeather()
  showNewPrompt.value = true
}

onMounted(() => {
  setTimeout(runSequence, 3000)
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
      <div class="flex font-mono" v-if="showWeatherPrompt">
        <span class="flex text-gray-300">
          <span class="text-term-user">konsta@erez.ac</span>
          <span>:</span>
          <span class="text-term-dir">~</span>
          <span class="mr-[1ch]">$</span>
        </span>
        <span class="text-white">{{ typedWeatherCmd }}</span>
      </div>
      <pre class="font-mono text-white whitespace-pre-wrap m-0">{{ weatherOutput }}</pre>
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
