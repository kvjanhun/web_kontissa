import { ref } from 'vue'
import { useDarkMode } from './useDarkMode.js'
import { wawaToIcon } from '../components/weatherIcons.js'

const PROMPT_HTML = '<span class="flex text-gray-300 shrink-0"><span class="text-term-user">konsta@erez.ac</span><span>:</span><span class="text-term-dir">~</span><span class="mr-[1ch]">$</span></span>'
const MAX_HISTORY = 50

const outputLines = ref([])
const currentInput = ref('')
const commandHistory = ref([])
const historyIndex = ref(-1)
const isBooting = ref(true)
const isProcessing = ref(false)

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function pushLine(html, type = 'output') {
  outputLines.value.push({ type, html })
}

function pushPromptLine(command) {
  pushLine(`<div class="flex font-mono">${PROMPT_HTML}<span class="text-white">${escapeHtml(command)}</span></div>`, 'prompt')
}

const prefersReducedMotion = typeof window !== 'undefined'
  ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
  : false

async function delay(ms) {
  if (prefersReducedMotion) return
  return new Promise((r) => setTimeout(r, ms))
}

async function runBootSequence() {
  isBooting.value = true
  const now = new Date()
  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  })

  const bootLines = [
    'Welcome to erez.ac (GNU/Linux 5.14.0-el9 x86_64)',
    '',
    ' * Server: Intel NUC11ATKC2, Helsinki',
    ' * Stack:  Flask 3.1 + Vue 3 + SQLite',
    ' * Status: <span class="text-term-user">All systems operational</span>',
    '',
    `Last login: ${dateStr} from visitor`,
  ]

  for (const line of bootLines) {
    pushLine(line, 'boot')
    await delay(250)
  }

  pushLine('', 'boot')
  isBooting.value = false
}

// --- Command handlers ---

function handleHelp() {
  pushLine(
    '<table class="text-sm">' +
    '<tr><td class="pr-4 text-term-user">help</td><td class="text-gray-300">Show available commands</td></tr>' +
    '<tr><td class="pr-4 text-term-user">weather</td><td class="text-gray-300">Current Helsinki weather</td></tr>' +
    '<tr><td class="pr-4 text-term-user">about</td><td class="text-gray-300">About Konsta Janhunen</td></tr>' +
    '<tr><td class="pr-4 text-term-user">neofetch</td><td class="text-gray-300">System info</td></tr>' +
    '<tr><td class="pr-4 text-term-user">cowsay &lt;msg&gt;</td><td class="text-gray-300">ASCII cow says your message</td></tr>' +
    '<tr><td class="pr-4 text-term-user">clear</td><td class="text-gray-300">Clear terminal</td></tr>' +
    '</table>'
  )
}

async function handleWeather() {
  try {
    const res = await fetch('/api/weather')
    const data = await res.json()
    if (data.error) {
      pushLine('<span class="text-red-400">Weather data unavailable</span>')
      return
    }
    const temp = data.temperature != null ? Math.round(data.temperature) : '?'
    const feels = data.feels_like != null ? Math.round(data.feels_like) : '?'
    const wind = data.wind_speed != null ? data.wind_speed : '?'
    const cond = data.condition || 'N/A'
    const icon = wawaToIcon(data.wawa_code)

    pushLine(
      `<div class="flex items-center gap-2 my-1">` +
      `<span>${icon}</span>` +
      `<span class="text-white font-bold">${temp}°C</span>` +
      `<span class="text-gray-400">feels like ${feels}°C</span>` +
      `<span class="text-gray-500">|</span>` +
      `<span class="text-gray-400">wind ${wind} m/s</span>` +
      `<span class="text-gray-500">|</span>` +
      `<span class="text-gray-300">${escapeHtml(cond)}</span>` +
      `</div>` +
      `<div class="text-gray-500 text-xs">Helsinki-Vantaa (FMI)</div>`
    )
  } catch {
    pushLine('<span class="text-red-400">Weather data unavailable</span>')
  }
}

function handleAbout() {
  pushLine(
    '<div class="my-1">' +
    '<div class="text-white font-bold">Konsta Janhunen</div>' +
    '<div class="text-gray-300 mt-1">Software developer based in Helsinki, Finland.</div>' +
    '<div class="text-gray-300">Building things with Python, JavaScript, and whatever gets the job done.</div>' +
    '<div class="mt-2">' +
    '<a href="https://github.com/kvjanhun" class="text-accent hover:underline" target="_blank" rel="noopener">github.com/kvjanhun</a>' +
    '<span class="text-gray-500 mx-2">|</span>' +
    '<a href="https://linkedin.com/in/kvjanhun" class="text-term-dir hover:underline" target="_blank" rel="noopener">linkedin.com/in/kvjanhun</a>' +
    '</div>' +
    '</div>'
  )
}

function handleNeofetch() {
  const { isDark } = useDarkMode()
  const logo = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192.3 146" class="w-20 shrink-0" aria-hidden="true"><path fill="#e00" d="m128,84c12.5,0 30.6-2.6 30.6-17.5a19.53,19.53 0 0 0-0.3-3.4L150.9,30.7C149.2,23.6 147.7,20.3 135.2,14.1 125.5,9.1 104.4,1 98.1,1 92.2,1 90.5,8.5 83.6,8.5 76.9,8.5 72,2.9 65.7,2.9c-6,0-9.9,4.1-12.9,12.5 0,0-8.4,23.7-9.5,27.2a6.15,6.15 0 0 0-0.2,1.9C43,53.7 79.3,83.9 128,84m32.5-11.4c1.7,8.2 1.7,9.1 1.7,10.1 0,14-15.7,21.8-36.4,21.8C79,104.5 38.1,77.1 38.1,59a18.35,18.35 0 0 1 1.5-7.3C22.8,52.5 1,55.5 1,74.7 1,106.2 75.6,145 134.6,145c45.3,0 56.7-20.5 56.7-36.7 0-12.7-11-27.1-30.8-35.7"/><path fill="#600" d="m160.5,72.6c1.7,8.2 1.7,9.1 1.7,10.1 0,14-15.7,21.8-36.4,21.8C79,104.5 38.1,77.1 38.1,59a18.35,18.35 0 0 1 1.5-7.3l3.7-9.1a6.15,6.15 0 0 0-0.2,1.9c0,9.2 36.3,39.4 84.9,39.4 12.5,0 30.6-2.6 30.6-17.5A19.53,19.53 0 0 0 158.3,63Z"/></svg>'

  const info = [
    '<span class="text-red-400 font-bold">konsta</span><span class="text-gray-300">@</span><span class="text-red-400 font-bold">erez.ac</span>',
    '<span class="text-gray-500">───────────────────────────</span>',
    `<span class="text-term-dir">OS</span>      <span class="text-gray-300">RHEL 9 (5.14.0-el9 x86_64)</span>`,
    `<span class="text-term-dir">Host</span>    <span class="text-gray-300">Intel NUC11ATKC2, Helsinki</span>`,
    `<span class="text-term-dir">Stack</span>   <span class="text-gray-300">Flask 3.1 / Vue 3 / SQLite</span>`,
    `<span class="text-term-dir">Theme</span>   <span class="text-gray-300">${isDark.value ? 'Dark' : 'Light'} mode</span>`,
    `<span class="text-term-dir">Font</span>    <span class="text-gray-300">Ubuntu Mono / DM Sans</span>`,
  ]

  pushLine(
    '<div class="flex items-center gap-4 my-1">' +
    logo +
    '<pre class="font-mono text-sm leading-relaxed m-0">' + info.join('\n') + '</pre>' +
    '</div>'
  )
}

async function handleCowsay(message) {
  const msg = message.trim() || 'moo'
  try {
    const res = await fetch(`/api/cowsay?message=${encodeURIComponent(msg)}`)
    const data = await res.json()
    if (data.error) {
      pushLine(`<span class="text-red-400">${escapeHtml(data.error)}</span>`)
      return
    }
    pushLine(`<pre class="font-mono text-sm whitespace-pre m-0">${escapeHtml(data.output)}</pre>`)
  } catch {
    pushLine('<span class="text-red-400">Error fetching cowsay</span>')
  }
}

async function executeCommand(input) {
  const trimmed = input.trim()
  if (!trimmed) {
    pushPromptLine('')
    return
  }

  // Add to history
  if (commandHistory.value[0] !== trimmed) {
    commandHistory.value.unshift(trimmed)
    if (commandHistory.value.length > MAX_HISTORY) {
      commandHistory.value.pop()
    }
  }
  historyIndex.value = -1

  pushPromptLine(trimmed)

  const parts = trimmed.split(/\s+/)
  const cmd = parts[0].toLowerCase()
  const args = parts.slice(1).join(' ')

  isProcessing.value = true
  try {
    switch (cmd) {
      case 'help':
        handleHelp()
        break
      case 'weather':
        await handleWeather()
        break
      case 'about':
        handleAbout()
        break
      case 'neofetch':
        handleNeofetch()
        break
      case 'cowsay':
        await handleCowsay(args)
        break
      case 'clear':
        outputLines.value = []
        break
      default:
        pushLine(`<span class="text-red-400">bash: ${escapeHtml(cmd)}: command not found</span>`)
    }
  } finally {
    isProcessing.value = false
  }
}

function historyUp() {
  if (commandHistory.value.length === 0) return
  if (historyIndex.value < commandHistory.value.length - 1) {
    historyIndex.value++
    currentInput.value = commandHistory.value[historyIndex.value]
  }
}

function historyDown() {
  if (historyIndex.value > 0) {
    historyIndex.value--
    currentInput.value = commandHistory.value[historyIndex.value]
  } else if (historyIndex.value === 0) {
    historyIndex.value = -1
    currentInput.value = ''
  }
}

export function useTerminal() {
  return {
    outputLines,
    currentInput,
    isBooting,
    isProcessing,
    executeCommand,
    runBootSequence,
    historyUp,
    historyDown,
  }
}
