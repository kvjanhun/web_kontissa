import { ref } from 'vue'
import { useDarkModeStore } from '~/stores/darkMode.js'
import { wawaToIcon } from '~/components/weatherIcons.js'

const PROMPT_HTML = '<span class="flex text-gray-300 shrink-0"><span class="text-term-user">konsta@erez.ac</span><span>:</span><span class="text-term-dir">~</span><span class="mr-[1ch]">$</span></span>'
const MAX_HISTORY = 50

let hasBooted = false

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

const KNOWN_COMMANDS = ['help', 'about', 'skills', 'fetch', 'weather', 'cowsay', 'cowthink', 'echo', 'date', 'clear']

export function levenshtein(a, b) {
  const m = a.length, n = b.length
  const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0))
  for (let i = 0; i <= m; i++) dp[i][0] = i
  for (let j = 0; j <= n; j++) dp[0][j] = j
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = a[i - 1] === b[j - 1]
        ? dp[i - 1][j - 1]
        : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    }
  }
  return dp[m][n]
}

export function findClosestCommand(input) {
  let best = null
  let bestDist = Infinity
  for (const cmd of KNOWN_COMMANDS) {
    const dist = levenshtein(input, cmd)
    if (dist < bestDist) { bestDist = dist; best = cmd }
  }
  return bestDist <= 2 ? best : null
}

function pushLine(html, type = 'output') {
  outputLines.value.push({ type, html })
}

function pushPromptLine(command) {
  pushLine(`<div class="flex font-mono">${PROMPT_HTML}<span class="text-white">${escapeHtml(command)}</span></div>`, 'prompt')
}

const prefersReducedMotion = typeof window !== 'undefined' && typeof window.matchMedia === 'function'
  ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
  : false

async function delay(ms) {
  if (prefersReducedMotion) return
  return new Promise((r) => setTimeout(r, ms))
}

async function runBootSequence() {
  if (hasBooted) {
    isBooting.value = false
    return
  }
  isBooting.value = true
  const now = new Date()
  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  })

  const bootLines = [
    'Welcome to erez.ac (GNU/Linux 5.14.0-el9 x86_64)',
    '',
    ' * Type <span class="text-term-user">help</span> for available commands',
    '',
    `Last login: ${dateStr} from visitor`,
  ]

  for (const line of bootLines) {
    pushLine(line, 'boot')
    await delay(250)
  }

  pushLine('', 'boot')
  hasBooted = true
  isBooting.value = false
}

async function autoTypeCommand(command) {
  if (prefersReducedMotion) {
    await executeCommand(command)
    return
  }

  await delay(600)

  for (let i = 0; i < command.length; i++) {
    currentInput.value += command[i]
    let pause = 25 + Math.random() * 45
    if (command[i] === ' ') pause += 40 + Math.random() * 60
    else if (Math.random() < 0.1) pause += 80 + Math.random() * 80
    await delay(pause)
  }

  await delay(300)
  const cmd = currentInput.value
  currentInput.value = ''
  await executeCommand(cmd)
}

// --- Command handlers ---

function handleHelp() {
  pushLine(
    '<table class="text-sm">' +
    '<tr><td class="pr-4 text-term-amber">help</td><td class="text-gray-300">Show available commands</td></tr>' +
    '<tr><td class="pr-4 text-term-amber">about</td><td class="text-gray-300">About Konsta Janhunen</td></tr>' +
    '<tr><td class="pr-4 text-term-amber">skills</td><td class="text-gray-300">Technical skills</td></tr>' +
    '<tr><td class="pr-4 text-term-amber">fetch</td><td class="text-gray-300">System info</td></tr>' +
    '<tr><td class="pr-4 text-term-amber">weather</td><td class="text-gray-300">Current Vantaa weather</td></tr>' +
    '<tr><td class="pr-4 text-term-amber">cowsay &lt;msg&gt;</td><td class="text-gray-300">ASCII cow says your message (-f char, -l)</td></tr>' +
    '<tr><td class="pr-4 text-term-amber">cowthink &lt;msg&gt;</td><td class="text-gray-300">ASCII cow thinks your message</td></tr>' +
    '<tr><td class="pr-4 text-term-amber">echo &lt;text&gt;</td><td class="text-gray-300">Print text</td></tr>' +
    '<tr><td class="pr-4 text-term-amber">date</td><td class="text-gray-300">Current date and time</td></tr>' +
    '<tr><td class="pr-4 text-term-amber">clear</td><td class="text-gray-300">Clear terminal</td></tr>' +
    '</table>'
  )
}

async function handleWeather() {
  try {
    const res = await fetch('/api/weather')
    const data = await res.json()
    if (data.error) {
      pushLine('<span class="text-term-error">Weather data unavailable</span>')
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
    pushLine('<span class="text-term-error">Weather data unavailable</span>')
  }
}

function handleAbout() {
  pushLine(
    '<div class="my-1">' +
    '<div class="text-white font-bold">Konsta Janhunen</div>' +
    '<div class="text-gray-300 mt-1">Software developer based in Helsinki, Finland.</div>' +
    '<div class="text-gray-300">Building things with Python, JavaScript, and whatever gets the job done.</div>' +
    '<div class="mt-2">' +
    '<a href="https://github.com/kvjanhun" class="text-term-amber hover:underline" target="_blank" rel="noopener">github.com/kvjanhun</a>' +
    '<span class="text-gray-500 mx-2">|</span>' +
    '<a href="https://linkedin.com/in/kvjanhun" class="text-term-dir hover:underline" target="_blank" rel="noopener">linkedin.com/in/kvjanhun</a>' +
    '</div>' +
    '</div>'
  )
}

function formatUptime(seconds) {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h ${m}m`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

async function handleFetch() {
  const logo = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192.3 146" class="w-20 shrink-0" aria-hidden="true"><path fill="#d45c5c" d="m128,84c12.5,0 30.6-2.6 30.6-17.5a19.53,19.53 0 0 0-0.3-3.4L150.9,30.7C149.2,23.6 147.7,20.3 135.2,14.1 125.5,9.1 104.4,1 98.1,1 92.2,1 90.5,8.5 83.6,8.5 76.9,8.5 72,2.9 65.7,2.9c-6,0-9.9,4.1-12.9,12.5 0,0-8.4,23.7-9.5,27.2a6.15,6.15 0 0 0-0.2,1.9C43,53.7 79.3,83.9 128,84m32.5-11.4c1.7,8.2 1.7,9.1 1.7,10.1 0,14-15.7,21.8-36.4,21.8C79,104.5 38.1,77.1 38.1,59a18.35,18.35 0 0 1 1.5-7.3C22.8,52.5 1,55.5 1,74.7 1,106.2 75.6,145 134.6,145c45.3,0 56.7-20.5 56.7-36.7 0-12.7-11-27.1-30.8-35.7"/><path fill="#7a3030" d="m160.5,72.6c1.7,8.2 1.7,9.1 1.7,10.1 0,14-15.7,21.8-36.4,21.8C79,104.5 38.1,77.1 38.1,59a18.35,18.35 0 0 1 1.5-7.3l3.7-9.1a6.15,6.15 0 0 0-0.2,1.9c0,9.2 36.3,39.4 84.9,39.4 12.5,0 30.6-2.6 30.6-17.5A19.53,19.53 0 0 0 158.3,63Z"/></svg>'

  let uptime = '?'
  let disk = '?'
  let memory = '?'
  let load = '?'

  try {
    const res = await fetch('/api/server-info')
    const data = await res.json()
    if (data.uptime_seconds != null) uptime = formatUptime(data.uptime_seconds)
    if (data.disk_used_percent != null) disk = `${data.disk_used_percent}% used`
    if (data.memory_total_mb != null) {
      const used = data.memory_used_mb != null ? (data.memory_used_mb / 1024).toFixed(1) : '?'
      const total = (data.memory_total_mb / 1024).toFixed(1)
      memory = `${used} / ${total} GiB`
    } else if (data.memory_used_mb != null) {
      memory = `${data.memory_used_mb} MB`
    }
    if (data.load_1min != null) load = data.load_1min.toFixed(2)
  } catch {
    // non-fatal — display '?' for live fields
  }

  const style = getComputedStyle(document.documentElement)
  const cv = (v) => style.getPropertyValue(v).trim()
  const swatches = [
    '--color-term-rose', '--color-term-sand', '--color-term-amber', '--color-term-user',
    '--color-term-sage', '--color-term-dir', '--color-text-secondary', '--color-text-primary',
  ].map(v => `<span style="color:${cv(v)}">███</span>`).join('')

  const info = [
    '<span class="text-term-user font-bold">konsta</span><span class="text-gray-300">@</span><span class="text-term-user font-bold">erez.ac</span>',
    '<span class="text-gray-500">─────────────────────────────────────</span>',
    `<span class="text-term-dir">OS</span>       <span class="text-gray-300">RHEL 9 (5.14.0-el9 x86_64)</span>`,
    `<span class="text-term-dir">CPU</span>      <span class="text-gray-300">Intel Celeron N4505 @ 2.00GHz</span>`,
    `<span class="text-term-dir">Memory</span>   <span class="text-gray-300">${escapeHtml(memory)}</span>`,
    `<span class="text-term-dir">Disk</span>     <span class="text-gray-300">${escapeHtml(disk)}</span>`,
    `<span class="text-term-dir">Load</span>     <span class="text-gray-300">${escapeHtml(load)}</span>`,
    `<span class="text-term-dir">Uptime</span>   <span class="text-gray-300">${escapeHtml(uptime)}</span>`,
    `<span class="text-term-dir">Theme</span>    <span class="text-gray-300">${document.documentElement.classList.contains('dark') ? 'Dark' : 'Light'} mode</span>`,
    `<span class="text-term-dir">Font</span>     <span class="text-gray-300">Ubuntu Mono / DM Sans</span>`,
    '',
    swatches,
  ]

  pushLine(
    '<div class="flex items-center gap-4 my-1">' +
    logo +
    '<pre class="font-mono text-sm leading-relaxed m-0">' + info.join('\n') + '</pre>' +
    '</div>'
  )
}

export function parseCowArgs(argsArray) {
  let character = 'cow'
  let message = ''
  const rest = [...argsArray]

  for (let i = 0; i < rest.length; i++) {
    if (rest[i] === '-f' && i + 1 < rest.length) {
      character = rest[i + 1]
      i++
    } else if (rest[i] === '-l') {
      return { list: true }
    } else {
      message = rest.slice(i).join(' ')
      break
    }
  }

  return { character, message: message || 'moo' }
}

async function handleCowsay(argsArray, think = false) {
  const parsed = parseCowArgs(argsArray)

  if (parsed.list) {
    try {
      const res = await fetch('/api/cowsay/characters')
      const data = await res.json()
      pushLine(`<span class="text-gray-300">${escapeHtml(data.characters.join('  '))}</span>`)
    } catch {
      pushLine('<span class="text-term-error">Error fetching character list</span>')
    }
    return
  }

  const params = new URLSearchParams({
    message: parsed.message,
    character: parsed.character,
  })
  if (think) params.set('think', 'true')

  try {
    const res = await fetch(`/api/cowsay?${params}`)
    const data = await res.json()
    if (data.error) {
      pushLine(`<span class="text-term-error">${escapeHtml(data.error)}</span>`)
      return
    }
    pushLine(`<pre class="font-mono text-sm whitespace-pre m-0">${escapeHtml(data.output)}</pre>`)
  } catch {
    pushLine('<span class="text-term-error">Error fetching cowsay</span>')
  }
}

function handleSkills() {
  pushLine(
    '<div class="my-1 text-sm space-y-1.5">' +
    '<div><span class="text-term-sand font-bold">Languages</span>  <span class="text-gray-300">Python · JavaScript · SQL · Bash · HTML/CSS</span></div>' +
    '<div><span class="text-term-amber font-bold">Frontend</span>   <span class="text-gray-300">Vue · Nuxt · React · Tailwind CSS · Vite</span></div>' +
    '<div><span class="text-term-sage font-bold">Backend</span>    <span class="text-gray-300">Flask · Node.js · REST APIs · SQLite</span></div>' +
    '<div><span class="text-term-rose font-bold">Infra</span>      <span class="text-gray-300">Docker · Nginx · Linux · GitHub Actions</span></div>' +
    '<div><span class="text-term-dir font-bold">Tools</span>      <span class="text-gray-300">Git · Claude Code · Agentic coding · VS Code</span></div>' +
    '</div>'
  )
}

function getCommandText(cmd, argsArray) {
  switch (cmd) {
    case 'echo':
      return argsArray.join(' ')
    case 'date': {
      const now = new Date()
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      const d = days[now.getDay()]
      const m = months[now.getMonth()]
      const day = String(now.getDate()).padStart(2, ' ')
      const hh = String(now.getHours()).padStart(2, '0')
      const mm = String(now.getMinutes()).padStart(2, '0')
      const ss = String(now.getSeconds()).padStart(2, '0')
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
      return `${d} ${m} ${day} ${hh}:${mm}:${ss} ${tz} ${now.getFullYear()}`
    }
    default:
      return null
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

  // Handle piping to cowsay/cowthink
  const pipeMatch = trimmed.match(/^(.+?)\s*\|\s*(cowsay|cowthink)(.*)$/i)
  if (pipeMatch) {
    const leftSide = pipeMatch[1].trim()
    const leftParts = leftSide.split(/\s+/)
    const leftCmd = leftParts[0].toLowerCase()
    const leftArgs = leftParts.slice(1)
    const pipeTo = pipeMatch[2].toLowerCase()
    const pipeArgs = pipeMatch[3].trim().split(/\s+/).filter(Boolean)

    isProcessing.value = true
    try {
      const text = getCommandText(leftCmd, leftArgs)
      if (text === null) {
        pushLine(`<span class="text-term-error">sh: ${escapeHtml(leftCmd)}: cannot pipe output</span>`)
        return
      }
      // Prepend piped text to cowsay args (flags first, then text)
      const cowArgs = [...pipeArgs, text]
      await handleCowsay(cowArgs, pipeTo === 'cowthink')
    } finally {
      isProcessing.value = false
    }
    return
  }

  const parts = trimmed.split(/\s+/)
  const cmd = parts[0].toLowerCase()
  const argsArray = parts.slice(1)

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
      case 'fetch':
        await handleFetch()
        break
      case 'skills':
        handleSkills()
        break
      case 'cowsay':
        await handleCowsay(argsArray)
        break
      case 'cowthink':
        await handleCowsay(argsArray, true)
        break
      case 'echo':
      case 'date': {
        const text = getCommandText(cmd, argsArray)
        pushLine(`<span class="text-gray-300">${escapeHtml(text)}</span>`)
        break
      }
      case 'clear':
        outputLines.value = []
        break
      default: {
        const suggestion = findClosestCommand(cmd)
        pushLine(`<span class="text-term-error">sh: ${escapeHtml(cmd)}: command not found</span>`)
        if (suggestion) {
          pushLine(`<span class="text-gray-400">Did you mean: <span class="text-term-amber">${suggestion}</span>?</span>`)
        }
        break
      }
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
    autoTypeCommand,
    historyUp,
    historyDown,
  }
}
