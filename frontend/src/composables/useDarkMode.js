import { ref, watch } from 'vue'

const isDark = ref(false)

function initDarkMode() {
  const stored = localStorage.getItem('theme')
  if (stored) {
    isDark.value = stored === 'dark'
  } else {
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  applyClass()
}

function applyClass() {
  document.documentElement.classList.toggle('dark', isDark.value)
}

function toggleDark() {
  isDark.value = !isDark.value
}

watch(isDark, (val) => {
  if (typeof window === 'undefined') return
  localStorage.setItem('theme', val ? 'dark' : 'light')
  applyClass()
})

if (typeof window !== 'undefined') initDarkMode()

export function useDarkMode() {
  return { isDark, toggleDark }
}
