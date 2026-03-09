import { ref, computed, watch, mergeProps, unref, nextTick, useSSRContext, withCtx, createTextVNode, toDisplayString } from "vue";
import { ssrRenderAttrs, ssrRenderStyle, ssrRenderList, ssrInterpolate, ssrRenderAttr, ssrRenderComponent } from "vue/server-renderer";
import { c as useDarkModeStore, u as useI18nStore } from "../server.mjs";
import { _ as _export_sfc } from "./_plugin-vue_export-helper-1tPrXgE0.js";
import { _ as __nuxt_component_0$1 } from "./nuxt-link-CgzrXG5R.js";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/hookable/dist/index.mjs";
import { u as useHead } from "./v3-DCBci_gg.js";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ofetch/dist/node.mjs";
import "#internal/nuxt/paths";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unctx/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/h3/dist/index.mjs";
import "pinia";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/defu/dist/defu.mjs";
import "vue-router";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ufo/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/klona/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/@unhead/vue/dist/index.mjs";
const WEATHER_ICONS = {
  sun: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="8" cy="8" r="3.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  partlyCloudy: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="6" cy="5" r="2.5"/><path d="M6 1v1M2 5H1M11 5h-1M3.17 2.17l.71.71M8.83 2.17l-.71.71" stroke="currentColor" stroke-width="1" stroke-linecap="round"/><path d="M4 10a3 3 0 0 1 2.83-3h.34A3 3 0 0 1 10 10a2 2 0 0 1 2 2H4a2 2 0 0 1 0-4z"/></svg>',
  cloud: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 12a3 3 0 0 1-.18-6A4 4 0 0 1 11.5 5 3.5 3.5 0 0 1 12 12H4z"/></svg>',
  rain: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 9a3 3 0 0 1-.18-6A4 4 0 0 1 11.5 2 3.5 3.5 0 0 1 12 9H4z"/><path d="M5 11v3M8 11v3M11 11v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  snow: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 9a3 3 0 0 1-.18-6A4 4 0 0 1 11.5 2 3.5 3.5 0 0 1 12 9H4z"/><circle cx="5" cy="11.5" r="1"/><circle cx="8" cy="13" r="1"/><circle cx="11" cy="11.5" r="1"/></svg>',
  fog: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M2 5h12M2 8h12M2 11h10M4 14h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/></svg>',
  thunderstorm: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 8a3 3 0 0 1-.18-6A4 4 0 0 1 11.5 1 3.5 3.5 0 0 1 12 8H4z"/><path d="M9 9l-2 4h3l-2 3" stroke="#facc15" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>',
  wind: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 16 16"><path d="M2 5h8a2 2 0 1 0-2-2M2 8h10a2 2 0 1 1-2 2M2 11h6a2 2 0 1 0-2-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  thermometer: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M9 1a2 2 0 0 0-2 2v6.27A3.5 3.5 0 1 0 11 13a3.48 3.48 0 0 0-2-3.17V3a2 2 0 0 0-2-2zm0 2a.5.5 0 0 1 .5.5v7.08a.5.5 0 0 1-.25.43A2 2 0 1 1 7 13a2 2 0 0 0 1.25-1.99.5.5 0 0 1-.25-.43V3.5A.5.5 0 0 1 9 3z"/></svg>'
};
function wawaToIcon(code) {
  if (code == null) return WEATHER_ICONS.thermometer;
  code = Number(code);
  if (code === 0) return WEATHER_ICONS.sun;
  if (code >= 1 && code <= 3) return WEATHER_ICONS.partlyCloudy;
  if (code >= 4 && code <= 5) return WEATHER_ICONS.fog;
  if (code >= 10 && code <= 12) return WEATHER_ICONS.fog;
  if (code === 18) return WEATHER_ICONS.wind;
  if (code >= 20 && code <= 26) return WEATHER_ICONS.cloud;
  if (code >= 27 && code <= 29) return WEATHER_ICONS.wind;
  if (code >= 30 && code <= 49) return WEATHER_ICONS.fog;
  if (code >= 50 && code <= 59) return WEATHER_ICONS.rain;
  if (code >= 60 && code <= 69) return WEATHER_ICONS.rain;
  if (code >= 70 && code <= 79) return WEATHER_ICONS.snow;
  if (code >= 80 && code <= 84) return WEATHER_ICONS.rain;
  if (code >= 85 && code <= 89) return WEATHER_ICONS.snow;
  if (code >= 90 && code <= 99) return WEATHER_ICONS.thunderstorm;
  return WEATHER_ICONS.cloud;
}
const PROMPT_HTML = '<span class="flex text-gray-300 shrink-0"><span class="text-term-user">konsta@erez.ac</span><span>:</span><span class="text-term-dir">~</span><span class="mr-[1ch]">$</span></span>';
const MAX_HISTORY = 50;
let hasBooted = false;
const outputLines = ref([]);
const currentInput = ref("");
const commandHistory = ref([]);
const historyIndex = ref(-1);
const isBooting = ref(true);
const isProcessing = ref(false);
function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
const KNOWN_COMMANDS = ["help", "about", "skills", "fetch", "weather", "cowsay", "cowthink", "echo", "date", "clear"];
function levenshtein(a, b) {
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = a[i - 1] === b[j - 1] ? dp[i - 1][j - 1] : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
    }
  }
  return dp[m][n];
}
function findClosestCommand(input) {
  let best = null;
  let bestDist = Infinity;
  for (const cmd of KNOWN_COMMANDS) {
    const dist = levenshtein(input, cmd);
    if (dist < bestDist) {
      bestDist = dist;
      best = cmd;
    }
  }
  return bestDist <= 2 ? best : null;
}
function pushLine(html, type = "output") {
  outputLines.value.push({ type, html });
}
function pushPromptLine(command) {
  pushLine(`<div class="flex font-mono">${PROMPT_HTML}<span class="text-white">${escapeHtml(command)}</span></div>`, "prompt");
}
async function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
async function runBootSequence() {
  if (hasBooted) {
    isBooting.value = false;
    return;
  }
  isBooting.value = true;
  const now = /* @__PURE__ */ new Date();
  const dateStr = now.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  });
  const bootLines = [
    "Welcome to erez.ac (GNU/Linux 5.14.0-el9 x86_64)",
    "",
    " * Server: Intel NUC11ATKC2, Vantaa",
    " * Stack:  Flask 3.1 + Vue 3 + SQLite",
    ' * Type <span class="text-term-user">help</span> for available commands',
    "",
    `Last login: ${dateStr} from visitor`
  ];
  for (const line of bootLines) {
    pushLine(line, "boot");
    await delay(250);
  }
  pushLine("", "boot");
  hasBooted = true;
  isBooting.value = false;
}
function handleHelp() {
  pushLine(
    '<table class="text-sm"><tr><td class="pr-4 text-term-user">help</td><td class="text-gray-300">Show available commands</td></tr><tr><td class="pr-4 text-term-user">about</td><td class="text-gray-300">About Konsta Janhunen</td></tr><tr><td class="pr-4 text-term-user">skills</td><td class="text-gray-300">Technical skills</td></tr><tr><td class="pr-4 text-term-user">fetch</td><td class="text-gray-300">System info</td></tr><tr><td class="pr-4 text-term-user">weather</td><td class="text-gray-300">Current Vantaa weather</td></tr><tr><td class="pr-4 text-term-user">cowsay &lt;msg&gt;</td><td class="text-gray-300">ASCII cow says your message (-f char, -l)</td></tr><tr><td class="pr-4 text-term-user">cowthink &lt;msg&gt;</td><td class="text-gray-300">ASCII cow thinks your message</td></tr><tr><td class="pr-4 text-term-user">echo &lt;text&gt;</td><td class="text-gray-300">Print text</td></tr><tr><td class="pr-4 text-term-user">date</td><td class="text-gray-300">Current date and time</td></tr><tr><td class="pr-4 text-term-user">clear</td><td class="text-gray-300">Clear terminal</td></tr></table>'
  );
}
async function handleWeather() {
  try {
    const res = await fetch("/api/weather");
    const data = await res.json();
    if (data.error) {
      pushLine('<span class="text-red-400">Weather data unavailable</span>');
      return;
    }
    const temp = data.temperature != null ? Math.round(data.temperature) : "?";
    const feels = data.feels_like != null ? Math.round(data.feels_like) : "?";
    const wind = data.wind_speed != null ? data.wind_speed : "?";
    const cond = data.condition || "N/A";
    const icon = wawaToIcon(data.wawa_code);
    pushLine(
      `<div class="flex items-center gap-2 my-1"><span>${icon}</span><span class="text-white font-bold">${temp}°C</span><span class="text-gray-400">feels like ${feels}°C</span><span class="text-gray-500">|</span><span class="text-gray-400">wind ${wind} m/s</span><span class="text-gray-500">|</span><span class="text-gray-300">${escapeHtml(cond)}</span></div><div class="text-gray-500 text-xs">Helsinki-Vantaa (FMI)</div>`
    );
  } catch {
    pushLine('<span class="text-red-400">Weather data unavailable</span>');
  }
}
function handleAbout() {
  pushLine(
    '<div class="my-1"><div class="text-white font-bold">Konsta Janhunen</div><div class="text-gray-300 mt-1">Software developer based in Helsinki, Finland.</div><div class="text-gray-300">Building things with Python, JavaScript, and whatever gets the job done.</div><div class="mt-2"><a href="https://github.com/kvjanhun" class="text-accent hover:underline" target="_blank" rel="noopener">github.com/kvjanhun</a><span class="text-gray-500 mx-2">|</span><a href="https://linkedin.com/in/kvjanhun" class="text-term-dir hover:underline" target="_blank" rel="noopener">linkedin.com/in/kvjanhun</a></div></div>'
  );
}
function handleFetch() {
  const { isDark } = useDarkModeStore();
  const logo = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192.3 146" class="w-20 shrink-0" aria-hidden="true"><path fill="#e00" d="m128,84c12.5,0 30.6-2.6 30.6-17.5a19.53,19.53 0 0 0-0.3-3.4L150.9,30.7C149.2,23.6 147.7,20.3 135.2,14.1 125.5,9.1 104.4,1 98.1,1 92.2,1 90.5,8.5 83.6,8.5 76.9,8.5 72,2.9 65.7,2.9c-6,0-9.9,4.1-12.9,12.5 0,0-8.4,23.7-9.5,27.2a6.15,6.15 0 0 0-0.2,1.9C43,53.7 79.3,83.9 128,84m32.5-11.4c1.7,8.2 1.7,9.1 1.7,10.1 0,14-15.7,21.8-36.4,21.8C79,104.5 38.1,77.1 38.1,59a18.35,18.35 0 0 1 1.5-7.3C22.8,52.5 1,55.5 1,74.7 1,106.2 75.6,145 134.6,145c45.3,0 56.7-20.5 56.7-36.7 0-12.7-11-27.1-30.8-35.7"/><path fill="#600" d="m160.5,72.6c1.7,8.2 1.7,9.1 1.7,10.1 0,14-15.7,21.8-36.4,21.8C79,104.5 38.1,77.1 38.1,59a18.35,18.35 0 0 1 1.5-7.3l3.7-9.1a6.15,6.15 0 0 0-0.2,1.9c0,9.2 36.3,39.4 84.9,39.4 12.5,0 30.6-2.6 30.6-17.5A19.53,19.53 0 0 0 158.3,63Z"/></svg>';
  const info = [
    '<span class="text-red-400 font-bold">konsta</span><span class="text-gray-300">@</span><span class="text-red-400 font-bold">erez.ac</span>',
    '<span class="text-gray-500">─────────────────────────────────────</span>',
    `<span class="text-term-dir">OS</span>       <span class="text-gray-300">RHEL 9 (5.14.0-el9 x86_64)</span>`,
    `<span class="text-term-dir">Host</span>     <span class="text-gray-300">Intel NUC11ATKC2, Vantaa</span>`,
    `<span class="text-term-dir">CPU</span>      <span class="text-gray-300">Intel Celeron N4505 @ 2.00GHz</span>`,
    `<span class="text-term-dir">Memory</span>   <span class="text-gray-300">7.3 GiB</span>`,
    `<span class="text-term-dir">Disk</span>     <span class="text-gray-300">70G (31% used)</span>`,
    `<span class="text-term-dir">Uptime</span>   <span class="text-gray-300">47 weeks</span>`,
    `<span class="text-term-dir">Docker</span>   <span class="text-gray-300">28.0.4</span>`,
    `<span class="text-term-dir">Stack</span>    <span class="text-gray-300">Flask 3.1 / Vue 3 / SQLite</span>`,
    `<span class="text-term-dir">Theme</span>    <span class="text-gray-300">${isDark.value ? "Dark" : "Light"} mode</span>`,
    `<span class="text-term-dir">Font</span>     <span class="text-gray-300">Ubuntu Mono / DM Sans</span>`
  ];
  pushLine(
    '<div class="flex items-center gap-4 my-1">' + logo + '<pre class="font-mono text-sm leading-relaxed m-0">' + info.join("\n") + "</pre></div>"
  );
}
function parseCowArgs(argsArray) {
  let character = "cow";
  let message = "";
  const rest = [...argsArray];
  for (let i = 0; i < rest.length; i++) {
    if (rest[i] === "-f" && i + 1 < rest.length) {
      character = rest[i + 1];
      i++;
    } else if (rest[i] === "-l") {
      return { list: true };
    } else {
      message = rest.slice(i).join(" ");
      break;
    }
  }
  return { character, message: message || "moo" };
}
async function handleCowsay(argsArray, think = false) {
  const parsed = parseCowArgs(argsArray);
  if (parsed.list) {
    try {
      const res = await fetch("/api/cowsay/characters");
      const data = await res.json();
      pushLine(`<span class="text-gray-300">${escapeHtml(data.characters.join("  "))}</span>`);
    } catch {
      pushLine('<span class="text-red-400">Error fetching character list</span>');
    }
    return;
  }
  const params = new URLSearchParams({
    message: parsed.message,
    character: parsed.character
  });
  if (think) params.set("think", "true");
  try {
    const res = await fetch(`/api/cowsay?${params}`);
    const data = await res.json();
    if (data.error) {
      pushLine(`<span class="text-red-400">${escapeHtml(data.error)}</span>`);
      return;
    }
    pushLine(`<pre class="font-mono text-sm whitespace-pre m-0">${escapeHtml(data.output)}</pre>`);
  } catch {
    pushLine('<span class="text-red-400">Error fetching cowsay</span>');
  }
}
function handleSkills() {
  pushLine(
    '<div class="my-1 text-sm space-y-1.5"><div><span class="text-term-user font-bold">Languages</span>  <span class="text-gray-300">Python · JavaScript · SQL · Bash · HTML/CSS</span></div><div><span class="text-term-dir font-bold">Frontend</span>   <span class="text-gray-300">Vue 3 · React · Tailwind CSS · Vite</span></div><div><span class="text-accent font-bold">Backend</span>    <span class="text-gray-300">Flask · Node.js · REST APIs · SQLite</span></div><div><span class="text-purple-400 font-bold">Infra</span>      <span class="text-gray-300">Docker · Nginx · Linux (RHEL) · GitHub Actions</span></div><div><span class="text-yellow-400 font-bold">Tools</span>      <span class="text-gray-300">Git · Claude Code · Agentic coding · VS Code</span></div></div>'
  );
}
function getCommandText(cmd, argsArray) {
  switch (cmd) {
    case "echo":
      return argsArray.join(" ");
    case "date": {
      const now = /* @__PURE__ */ new Date();
      const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const d = days[now.getDay()];
      const m = months[now.getMonth()];
      const day = String(now.getDate()).padStart(2, " ");
      const hh = String(now.getHours()).padStart(2, "0");
      const mm = String(now.getMinutes()).padStart(2, "0");
      const ss = String(now.getSeconds()).padStart(2, "0");
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      return `${d} ${m} ${day} ${hh}:${mm}:${ss} ${tz} ${now.getFullYear()}`;
    }
    default:
      return null;
  }
}
async function executeCommand(input) {
  const trimmed = input.trim();
  if (!trimmed) {
    pushPromptLine("");
    return;
  }
  if (commandHistory.value[0] !== trimmed) {
    commandHistory.value.unshift(trimmed);
    if (commandHistory.value.length > MAX_HISTORY) {
      commandHistory.value.pop();
    }
  }
  historyIndex.value = -1;
  pushPromptLine(trimmed);
  const pipeMatch = trimmed.match(/^(.+?)\s*\|\s*(cowsay|cowthink)(.*)$/i);
  if (pipeMatch) {
    const leftSide = pipeMatch[1].trim();
    const leftParts = leftSide.split(/\s+/);
    const leftCmd = leftParts[0].toLowerCase();
    const leftArgs = leftParts.slice(1);
    const pipeTo = pipeMatch[2].toLowerCase();
    const pipeArgs = pipeMatch[3].trim().split(/\s+/).filter(Boolean);
    isProcessing.value = true;
    try {
      const text = getCommandText(leftCmd, leftArgs);
      if (text === null) {
        pushLine(`<span class="text-red-400">bash: ${escapeHtml(leftCmd)}: cannot pipe output</span>`);
        return;
      }
      const cowArgs = [...pipeArgs, text];
      await handleCowsay(cowArgs, pipeTo === "cowthink");
    } finally {
      isProcessing.value = false;
    }
    return;
  }
  const parts = trimmed.split(/\s+/);
  const cmd = parts[0].toLowerCase();
  const argsArray = parts.slice(1);
  isProcessing.value = true;
  try {
    switch (cmd) {
      case "help":
        handleHelp();
        break;
      case "weather":
        await handleWeather();
        break;
      case "about":
        handleAbout();
        break;
      case "fetch":
        handleFetch();
        break;
      case "skills":
        handleSkills();
        break;
      case "cowsay":
        await handleCowsay(argsArray);
        break;
      case "cowthink":
        await handleCowsay(argsArray, true);
        break;
      case "echo":
      case "date": {
        const text = getCommandText(cmd, argsArray);
        pushLine(`<span class="text-gray-300">${escapeHtml(text)}</span>`);
        break;
      }
      case "clear":
        outputLines.value = [];
        break;
      default: {
        const suggestion = findClosestCommand(cmd);
        pushLine(`<span class="text-red-400">bash: ${escapeHtml(cmd)}: command not found</span>`);
        if (suggestion) {
          pushLine(`<span class="text-gray-400">Did you mean: <span class="text-term-user">${suggestion}</span>?</span>`);
        }
        break;
      }
    }
  } finally {
    isProcessing.value = false;
  }
}
function historyUp() {
  if (commandHistory.value.length === 0) return;
  if (historyIndex.value < commandHistory.value.length - 1) {
    historyIndex.value++;
    currentInput.value = commandHistory.value[historyIndex.value];
  }
}
function historyDown() {
  if (historyIndex.value > 0) {
    historyIndex.value--;
    currentInput.value = commandHistory.value[historyIndex.value];
  } else if (historyIndex.value === 0) {
    historyIndex.value = -1;
    currentInput.value = "";
  }
}
function useTerminal() {
  return {
    outputLines,
    currentInput,
    isBooting,
    isProcessing,
    executeCommand,
    runBootSequence,
    historyUp,
    historyDown
  };
}
const _sfc_main$1 = {
  __name: "TerminalWindow",
  __ssrInlineRender: true,
  setup(__props) {
    const {
      outputLines: outputLines2,
      currentInput: currentInput2,
      isBooting: isBooting2
    } = useTerminal();
    ref(null);
    const scrollContainer = ref(null);
    const scrollTop = ref(0);
    const scrollHeight = ref(1);
    const clientHeight = ref(1);
    const canScroll = computed(() => scrollHeight.value > clientHeight.value);
    const thumbHeight = computed(() => {
      if (!canScroll.value) return 0;
      return Math.max(24, clientHeight.value / scrollHeight.value * clientHeight.value);
    });
    const thumbTop = computed(() => {
      if (!canScroll.value) return 0;
      const maxScroll = scrollHeight.value - clientHeight.value;
      const maxThumb = clientHeight.value - thumbHeight.value;
      return maxScroll > 0 ? scrollTop.value / maxScroll * maxThumb : 0;
    });
    function updateScrollMetrics() {
      const el = scrollContainer.value;
      if (!el) return;
      scrollTop.value = el.scrollTop;
      scrollHeight.value = el.scrollHeight;
      clientHeight.value = el.clientHeight;
    }
    function scrollToBottom() {
      nextTick(() => {
        if (scrollContainer.value) {
          scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
          updateScrollMetrics();
        }
      });
    }
    watch(outputLines2, scrollToBottom, { deep: true });
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "w-full rounded-lg overflow-hidden shadow-lg" }, _attrs))} data-v-84e35bcd><div class="relative bg-term-bg" data-v-84e35bcd><div class="font-mono text-sm text-white p-4 h-[340px] overflow-y-scroll pr-6" style="${ssrRenderStyle({ "-ms-overflow-style": "none", "scrollbar-width": "none" })}" role="log" aria-live="polite" data-v-84e35bcd><!--[-->`);
      ssrRenderList(unref(outputLines2), (line, i) => {
        _push(`<div data-v-84e35bcd>${line.html ?? ""}</div>`);
      });
      _push(`<!--]-->`);
      if (!unref(isBooting2)) {
        _push(`<div class="flex font-mono" data-v-84e35bcd><span class="flex text-gray-300 shrink-0" data-v-84e35bcd><span class="text-term-user" data-v-84e35bcd>konsta@erez.ac</span><span data-v-84e35bcd>:</span><span class="text-term-dir" data-v-84e35bcd>~</span><span class="mr-[1ch]" data-v-84e35bcd>$</span></span><span class="text-white whitespace-pre" data-v-84e35bcd>${ssrInterpolate(unref(currentInput2))}</span><span class="block self-center h-[1em] w-[0.6em] cursor-blink shrink-0" data-v-84e35bcd></span></div>`);
      } else {
        _push(`<!---->`);
      }
      _push(`</div><div class="absolute top-2 bottom-2 right-1.5 w-1.5 rounded-full" style="${ssrRenderStyle({ "background": "#1a1a1a" })}" aria-hidden="true" data-v-84e35bcd>`);
      if (canScroll.value) {
        _push(`<div class="w-1.5 rounded-full" style="${ssrRenderStyle({
          background: "#555",
          height: thumbHeight.value + "px",
          marginTop: thumbTop.value + "px"
        })}" data-v-84e35bcd></div>`);
      } else {
        _push(`<!---->`);
      }
      _push(`</div></div><input${ssrRenderAttr("value", unref(currentInput2))} class="sr-only" type="text" autocapitalize="off" autocorrect="off" spellcheck="false" aria-label="Terminal input" data-v-84e35bcd></div>`);
    };
  }
};
const _sfc_setup$1 = _sfc_main$1.setup;
_sfc_main$1.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/TerminalWindow.vue");
  return _sfc_setup$1 ? _sfc_setup$1(props, ctx) : void 0;
};
const __nuxt_component_0 = /* @__PURE__ */ _export_sfc(_sfc_main$1, [["__scopeId", "data-v-84e35bcd"]]);
const _sfc_main = {
  __name: "index",
  __ssrInlineRender: true,
  setup(__props) {
    const { t } = useI18nStore();
    useHead({
      title: computed(() => t("home.metaTitle")),
      meta: [
        { name: "description", content: computed(() => t("home.metaDescription")) }
      ]
    });
    return (_ctx, _push, _parent, _attrs) => {
      const _component_TerminalWindow = __nuxt_component_0;
      const _component_NuxtLink = __nuxt_component_0$1;
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "flex flex-col items-center py-12" }, _attrs))}><h1 class="text-5xl font-light mb-2" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(unref(t)("home.heading"))}</h1><p class="text-lg mb-10" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("home.subtitle"))}</p><div class="w-full max-w-2xl mb-10">`);
      _push(ssrRenderComponent(_component_TerminalWindow, null, null, _parent));
      _push(`</div><div class="flex gap-4">`);
      _push(ssrRenderComponent(_component_NuxtLink, {
        to: "/about",
        class: "px-6 py-2.5 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
      }, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(`${ssrInterpolate(unref(t)("home.aboutMe"))}`);
          } else {
            return [
              createTextVNode(toDisplayString(unref(t)("home.aboutMe")), 1)
            ];
          }
        }),
        _: 1
      }, _parent));
      _push(ssrRenderComponent(_component_NuxtLink, {
        to: "/contact",
        class: "px-6 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200",
        style: { border: "1px solid var(--color-border)", color: "var(--color-text-primary)" }
      }, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(`${ssrInterpolate(unref(t)("home.getInTouch"))}`);
          } else {
            return [
              createTextVNode(toDisplayString(unref(t)("home.getInTouch")), 1)
            ];
          }
        }),
        _: 1
      }, _parent));
      _push(`</div></div>`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("pages/index.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
export {
  _sfc_main as default
};
//# sourceMappingURL=index-B3TpyDW1.js.map
