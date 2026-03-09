import { _ as __nuxt_component_0 } from './nuxt-link-CgzrXG5R.mjs';
import { _ as _sfc_main$2 } from './ThemeToggle-xR7Kb5x1.mjs';
import { ssrRenderStyle, ssrRenderComponent, ssrInterpolate, ssrRenderAttr, ssrRenderList, ssrRenderClass, ssrRenderTeleport } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/server-renderer/index.mjs';
import { ref, computed, withCtx, createTextVNode, unref, useSSRContext } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/index.mjs';
import { _ as _export_sfc } from './_plugin-vue_export-helper-1tPrXgE0.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ufo/dist/index.mjs';
import './server.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ofetch/dist/node.mjs';
import '../_/renderer.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue-bundle-renderer/dist/runtime.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/h3/dist/index.mjs';
import '../nitro/nitro.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/destr/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/hookable/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/node-mock-http/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/drivers/fs.mjs';
import 'node:crypto';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/drivers/fs-lite.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/drivers/lru-cache.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ohash/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/klona/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/defu/dist/defu.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/scule/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unctx/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/radix3/dist/index.mjs';
import 'node:fs';
import 'node:url';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/pathe/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unhead/dist/server.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/devalue/index.js';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unhead/dist/utils.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unhead/dist/plugins.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/pinia/dist/pinia.prod.cjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue-router/vue-router.node.mjs';

const _sfc_main$1 = {
  __name: "SanakennoRulesModal",
  __ssrInlineRender: true,
  props: {
    show: { type: Boolean, required: true }
  },
  emits: ["close"],
  setup(__props, { emit: __emit }) {
    return (_ctx, _push, _parent, _attrs) => {
      ssrRenderTeleport(_push, (_push2) => {
        if (__props.show) {
          _push2(`<div class="fixed inset-0 z-50 flex items-center justify-center p-4" style="${ssrRenderStyle({ "background": "rgba(0,0,0,0.6)" })}"><div class="w-full max-w-sm rounded-xl p-6 overflow-y-auto max-h-[90vh]" style="${ssrRenderStyle({ "background": "var(--color-bg-primary)", "border": "1px solid var(--color-border)" })}" role="dialog" aria-modal="true" aria-label="S\xE4\xE4nn\xF6t"><div class="flex justify-between items-center mb-4"><h2 class="text-lg font-semibold" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}">Ohjeet</h2><button class="p-1 rounded hover:bg-white/10 text-xl leading-none" style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)" })}" aria-label="Sulje">\u2715</button></div><div class="text-sm space-y-4" style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}"><p>L\xF6yd\xE4 mahdollisimman monta sanaa seitsem\xE4st\xE4 annetusta kirjaimesta.</p><div><p class="font-medium mb-1" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}">Jokaisen sanan t\xE4ytyy:</p><ul class="space-y-1 list-none pl-0"><li>\u2726 Sis\xE4lt\xE4\xE4 <span style="${ssrRenderStyle({ "color": "var(--color-accent)" })}">oranssin keskikirjaimen</span></li><li>\u2726 Olla v\xE4hint\xE4\xE4n 4 kirjainta pitk\xE4</li><li>\u2726 Koostua vain annetuista kirjaimista \u2014 samaa kirjainta voi k\xE4ytt\xE4\xE4 useasti</li><li>\u2726 L\xF6yty\xE4 suomen kielen sanakirjasta (<a href="https://kaino.kotus.fi/sanat/nykysuomi/" target="_blank" rel="noopener" style="${ssrRenderStyle({ "color": "var(--color-accent)", "text-decoration": "underline" })}">Kotus</a>)</li></ul></div><div><p class="font-medium mb-1" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}">Pisteytys:</p><ul class="space-y-1 list-none pl-0"><li>\u2726 4-kirjaiminen sana = 1 piste</li><li>\u2726 Pidempi sana = pisteit\xE4 sanan pituuden verran</li><li>\u2726 Pangrammi (kaikki 7 kirjainta k\xE4ytetty) = +7 lis\xE4pistett\xE4</li></ul></div><div><p class="font-medium mb-1" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}">Yhdyssanat:</p><p>Yhdysviivallisen sanan voi kirjoittaa my\xF6s ilman viivaa \u2014 esim. <span style="${ssrRenderStyle({ "font-family": "var(--font-mono)" })}">palo-ovi</span> tai <span style="${ssrRenderStyle({ "font-family": "var(--font-mono)" })}">paloovi</span>.</p></div><div><p class="font-medium mb-1" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}">Tasot:</p><p>Pisteesi m\xE4\xE4ritt\xE4v\xE4t tason. Tavoittele tasoa <span style="${ssrRenderStyle({ "color": "var(--color-accent)" })}">\xC4llistytt\xE4v\xE4</span>!</p></div><div><p class="font-medium mb-1" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}">\u{1F4A1} Avut:</p><p>Nelj\xE4 vihjett\xE4, jotka j\xE4\xE4v\xE4t auki koko pelin ajaksi.</p></div></div></div></div>`);
        } else {
          _push2(`<!---->`);
        }
      }, "body", false, _parent);
    };
  }
};
const _sfc_setup$1 = _sfc_main$1.setup;
_sfc_main$1.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/SanakennoRulesModal.vue");
  return _sfc_setup$1 ? _sfc_setup$1(props, ctx) : void 0;
};
function useGameTimer() {
  const startedAt = ref(null);
  const totalPausedMs = ref(0);
  function start() {
    if (!startedAt.value) startedAt.value = Date.now();
  }
  function getElapsedMs() {
    if (!startedAt.value) return 0;
    return Date.now() - startedAt.value - totalPausedMs.value;
  }
  function reset() {
    startedAt.value = null;
    totalPausedMs.value = 0;
  }
  return { startedAt, totalPausedMs, start, getElapsedMs, reset };
}
function useHintData(puzzle, foundWords, outerLetters, center) {
  const foundByLetter = computed(() => {
    const map = {};
    for (const word of foundWords.value) {
      const l = word[0];
      map[l] = (map[l] || 0) + 1;
    }
    return map;
  });
  const foundByLength = computed(() => {
    const map = {};
    for (const word of foundWords.value) {
      const k = String(word.length);
      map[k] = (map[k] || 0) + 1;
    }
    return map;
  });
  const foundByPair = computed(() => {
    const map = {};
    for (const word of foundWords.value) {
      const pair = word.slice(0, 2);
      map[pair] = (map[pair] || 0) + 1;
    }
    return map;
  });
  const letterMap = computed(() => {
    var _a;
    const hd = (_a = puzzle.value) == null ? void 0 : _a.hint_data;
    if (!hd) return [];
    return Object.entries(hd.by_letter).map(([letter, total]) => ({ letter, remaining: total - (foundByLetter.value[letter] || 0) })).sort((a, b) => a.letter.localeCompare(b.letter));
  });
  const unfoundLengths = computed(() => {
    var _a;
    const hd = (_a = puzzle.value) == null ? void 0 : _a.hint_data;
    if (!hd) return null;
    const remaining = hd.word_count - foundWords.value.size;
    if (remaining === 0) return null;
    let longest = 0;
    const uniqueLengths = /* @__PURE__ */ new Set();
    for (const [len, total] of Object.entries(hd.by_length)) {
      const found = foundByLength.value[len] || 0;
      if (total - found > 0) {
        uniqueLengths.add(parseInt(len));
        if (parseInt(len) > longest) longest = parseInt(len);
      }
    }
    return { longest, uniqueLengths: uniqueLengths.size };
  });
  const pangramStats = computed(() => {
    var _a;
    const hd = (_a = puzzle.value) == null ? void 0 : _a.hint_data;
    if (!hd) return { total: 0, found: 0, remaining: 0 };
    const letterSet = /* @__PURE__ */ new Set([center.value, ...outerLetters.value]);
    const foundPangrams = [...foundWords.value].filter((w) => [...letterSet].every((c) => w.includes(c))).length;
    return { total: hd.pangram_count, found: foundPangrams, remaining: hd.pangram_count - foundPangrams };
  });
  const lengthDistribution = computed(() => {
    var _a;
    const hd = (_a = puzzle.value) == null ? void 0 : _a.hint_data;
    if (!hd) return [];
    return Object.entries(hd.by_length).map(([len, total]) => ({ len: parseInt(len), total, remaining: total - (foundByLength.value[len] || 0) })).sort((a, b) => a.len - b.len);
  });
  const pairMap = computed(() => {
    var _a;
    const hd = (_a = puzzle.value) == null ? void 0 : _a.hint_data;
    if (!hd) return [];
    return Object.entries(hd.by_pair).map(([pair, total]) => ({ pair, remaining: total - (foundByPair.value[pair] || 0) })).sort((a, b) => a.pair.localeCompare(b.pair));
  });
  return { letterMap, unfoundLengths, pangramStats, lengthDistribution, pairMap };
}
const RANKS = [
  { pct: 100, name: "T\xE4ysi kenno" },
  { pct: 70, name: "\xC4llistytt\xE4v\xE4" },
  { pct: 40, name: "Sanavalmis" },
  { pct: 20, name: "Onnistuja" },
  { pct: 10, name: "Nyt menn\xE4\xE4n!" },
  { pct: 2, name: "Hyv\xE4 alku" },
  { pct: 0, name: "Etsi sanoja!" }
];
function rankForScore(score, maxScore) {
  if (maxScore === 0) return RANKS[RANKS.length - 1].name;
  const pct = score / maxScore * 100;
  for (const r of RANKS) {
    if (pct >= r.pct) return r.name;
  }
  return RANKS[RANKS.length - 1].name;
}
function rankThresholds(currentRank, maxScore) {
  const visible = currentRank === "T\xE4ysi kenno" ? RANKS : RANKS.filter((r) => r.name !== "T\xE4ysi kenno");
  return [...visible].reverse().map((r) => ({
    name: r.name,
    points: Math.ceil(r.pct / 100 * maxScore),
    isCurrent: currentRank === r.name
  }));
}
function progressToNextRank(score, maxScore) {
  if (maxScore === 0) return 0;
  const scorePct = score / maxScore * 100;
  const currentIdx = RANKS.findIndex((r) => scorePct >= r.pct);
  if (currentIdx === -1) return 0;
  if (currentIdx === 0) return 100;
  const currentRankPts = Math.ceil(RANKS[currentIdx].pct / 100 * maxScore);
  const nextRankPts = Math.ceil(RANKS[currentIdx - 1].pct / 100 * maxScore);
  if (nextRankPts <= currentRankPts) return 100;
  return Math.min(100, (score - currentRankPts) / (nextRankPts - currentRankPts) * 100);
}
function colorizeWord(word, center, allLetters) {
  return [...word].map((char) => {
    if (char === "-") return { char, color: "tertiary" };
    if (char === center) return { char, color: "accent" };
    if (allLetters.has(char)) return { char, color: "primary" };
    return { char, color: "tertiary" };
  });
}
function toColumns(words, perColumn = 10) {
  const cols = [];
  for (let i = 0; i < words.length; i += perColumn) {
    cols.push(words.slice(i, i + perColumn));
  }
  return cols;
}
const _sfc_main = {
  __name: "sanakenno",
  __ssrInlineRender: true,
  setup(__props) {
    const puzzle = ref(null);
    const outerLetters = ref([]);
    const currentWord = ref("");
    const foundWords = ref(/* @__PURE__ */ new Set());
    const score = ref(0);
    const message = ref("");
    const messageType = ref("ok");
    const loading = ref(true);
    const fetchError = ref("");
    const puzzleNumber = ref(null);
    const showRanks = ref(false);
    const showHints = ref(false);
    const showRules = ref(false);
    const hintsUnlocked = ref(/* @__PURE__ */ new Set());
    const celebration = ref(null);
    const hintsCollapsed = ref(/* @__PURE__ */ new Set());
    const showAllFoundWords = ref(false);
    const recentFoundWords = computed(() => [...foundWords.value].slice(-6).reverse());
    const wordShake = ref(false);
    ref(false);
    const pressedHexIndex = ref(null);
    const lastResubmittedWord = ref(null);
    const shareCopied = ref(false);
    useGameTimer();
    const center = computed(() => {
      var _a, _b;
      return (_b = (_a = puzzle.value) == null ? void 0 : _a.center) != null ? _b : "";
    });
    computed(() => {
      var _a, _b;
      return new Set((_b = (_a = puzzle.value) == null ? void 0 : _a.word_hashes) != null ? _b : []);
    });
    const allLetters = computed(() => /* @__PURE__ */ new Set([center.value, ...outerLetters.value]));
    const HINT_SVG = {
      bulb: '<svg xmlns="http://www.w3.org/2000/svg" width="1.15em" height="1.15em" viewBox="-1 -1 40 64" fill="none" stroke="currentColor" aria-hidden="true" style="vertical-align: -0.3em;" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.6,48l20.6-3c0-6.5,8.8-14.6,8.8-25.6C38,8.7,29.5,0,19,0S0,8.7,0,19.4c0,10.9,8.6,19,8.6,25.5V48z"/><path d="M10,52.3l18.8-2.9"/><path d="M10,56.2l18.8-2.9"/><path d="M26.3,59.1c0,1.6-3.1,2.9-7,2.9s-7-1.3-7-2.9"/><path d="M16.4,40.8c0-12.4-3.5-16.8-3.5-16.8s1.4,3.1,3,3.1c1.7,0,3-1.4,3-3.1c0,1.7,1.4,3.1,3,3.1c1.7,0,3-3.1,3-3.1s-2.8,6.7-2.8,16.8"/></svg>',
      summary: '<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 512 512" fill="currentColor" stroke="none" aria-hidden="true"><path d="M332.998,291.918c52.2-71.895,45.941-173.338-18.834-238.123c-71.736-71.728-188.468-71.728-260.195,0c-71.746,71.745-71.746,188.458,0,260.204c64.775,64.775,166.218,71.034,238.104,18.844l14.222,14.203l40.916-40.916L332.998,291.918z M278.488,278.333c-52.144,52.134-136.699,52.144-188.852,0c-52.152-52.153-52.152-136.717,0-188.861c52.154-52.144,136.708-52.144,188.852,0C330.64,141.616,330.64,226.18,278.488,278.333z"/><path d="M109.303,119.216c-27.078,34.788-29.324,82.646-6.756,119.614c2.142,3.489,6.709,4.603,10.208,2.46c3.49-2.142,4.594-6.709,2.462-10.198v0.008c-19.387-31.7-17.45-72.962,5.782-102.771c2.526-3.228,1.946-7.898-1.292-10.405C116.48,115.399,111.811,115.979,109.303,119.216z"/><path d="M501.499,438.591L363.341,315.178l-47.98,47.98l123.403,138.168c12.548,16.234,35.144,13.848,55.447-6.456C514.505,474.576,517.743,451.138,501.499,438.591z"/></svg>',
      letters: '<span aria-hidden="true" style="font-weight:450;font-size:1.1em;line-height:1;">A</span>',
      distribution: '<svg xmlns="http://www.w3.org/2000/svg" width="1.15em" height="1em" viewBox="0 0 20 14" fill="currentColor" stroke="currentColor" aria-hidden="true"><rect x="0.5" y="0.5" width="19" height="13" rx="1" fill="none" stroke-width="1.3"/><line x1="4" y1="0.5" x2="4" y2="5" stroke-width="1"/><line x1="8" y1="0.5" x2="8" y2="7.5" stroke-width="1"/><line x1="12" y1="0.5" x2="12" y2="5" stroke-width="1"/><line x1="16" y1="0.5" x2="16" y2="7.5" stroke-width="1"/></svg>',
      pairs: '<span aria-hidden="true" style="font-weight:450;font-size:1.1em;line-height:1;">AB</span>'
    };
    const rank = computed(() => {
      var _a, _b;
      return rankForScore(score.value, (_b = (_a = puzzle.value) == null ? void 0 : _a.max_score) != null ? _b : 0);
    });
    const rankThresholds$1 = computed(() => {
      var _a, _b;
      return rankThresholds(rank.value, (_b = (_a = puzzle.value) == null ? void 0 : _a.max_score) != null ? _b : 0);
    });
    const progressToNextRank$1 = computed(() => {
      var _a, _b;
      return progressToNextRank(score.value, (_b = (_a = puzzle.value) == null ? void 0 : _a.max_score) != null ? _b : 0);
    });
    const allFound = computed(() => {
      var _a;
      if (!((_a = puzzle.value) == null ? void 0 : _a.hint_data)) return false;
      return foundWords.value.size === puzzle.value.hint_data.word_count;
    });
    const COLOR_MAP = { accent: "var(--color-accent)", primary: "var(--color-text-primary)", tertiary: "var(--color-text-tertiary)" };
    const currentWordChars = computed(
      () => colorizeWord(currentWord.value, center.value, allLetters.value).map(({ char, color }) => ({ char, color: COLOR_MAP[color] }))
    );
    const sortedFoundWords = computed(
      () => [...foundWords.value].sort((a, b) => a.localeCompare(b) || a.length - b.length)
    );
    const wordColumns = computed(() => toColumns(sortedFoundWords.value));
    const { letterMap, unfoundLengths, pangramStats, lengthDistribution, pairMap } = useHintData(puzzle, foundWords, outerLetters, center);
    const hexes = computed(() => {
      var _a, _b, _c, _d, _e, _f;
      const R = 50;
      const dx = R * Math.sqrt(3);
      const dy = R * 1.5;
      const cx = 150, cy = 150;
      const ol = outerLetters.value;
      return [
        { x: cx - dx / 2, y: cy - dy, letter: (_a = ol[0]) != null ? _a : "", isCenter: false },
        // top-left
        { x: cx + dx / 2, y: cy - dy, letter: (_b = ol[1]) != null ? _b : "", isCenter: false },
        // top-right
        { x: cx - dx, y: cy, letter: (_c = ol[2]) != null ? _c : "", isCenter: false },
        // mid-left
        { x: cx, y: cy, letter: center.value, isCenter: true },
        // center
        { x: cx + dx, y: cy, letter: (_d = ol[3]) != null ? _d : "", isCenter: false },
        // mid-right
        { x: cx - dx / 2, y: cy + dy, letter: (_e = ol[4]) != null ? _e : "", isCenter: false },
        // bot-left
        { x: cx + dx / 2, y: cy + dy, letter: (_f = ol[5]) != null ? _f : "", isCenter: false }
        // bot-right
      ];
    });
    function hexPoints(cx, cy, r) {
      const pts = [];
      for (let i = 0; i < 6; i++) {
        const a = Math.PI / 180 * (60 * i - 30);
        pts.push(`${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`);
      }
      return pts.join(" ");
    }
    return (_ctx, _push, _parent, _attrs) => {
      const _component_NuxtLink = __nuxt_component_0;
      const _component_ThemeToggle = _sfc_main$2;
      const _component_SanakennoRulesModal = _sfc_main$1;
      _push(`<!--[--><div style="${ssrRenderStyle({ "position": "fixed", "top": "0", "left": "0", "right": "0", "z-index": "50", "background-color": "var(--color-bg-primary)", "padding-top": "env(safe-area-inset-top)" })}" data-v-6b5c3829><div class="max-w-sm mx-auto px-6 h-12 flex justify-between items-center" data-v-6b5c3829>`);
      _push(ssrRenderComponent(_component_NuxtLink, {
        to: "/",
        class: "text-sm",
        style: { "color": "var(--color-text-tertiary)" }
      }, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(`\u2190 erez.ac`);
          } else {
            return [
              createTextVNode("\u2190 erez.ac")
            ];
          }
        }),
        _: 1
      }, _parent));
      _push(`<h1 class="text-lg font-semibold" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}" data-v-6b5c3829>Sanakenno`);
      if (unref(puzzleNumber) != null) {
        _push(`<span style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)" })}" data-v-6b5c3829> \u2014 #${ssrInterpolate(unref(puzzleNumber) + 1)}</span>`);
      } else {
        _push(`<!---->`);
      }
      _push(`</h1><div class="flex items-center gap-1" data-v-6b5c3829><button class="p-2 rounded-lg transition-colors duration-200 hover:bg-white/10 text-sm font-semibold" style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)" })}" aria-label="S\xE4\xE4nn\xF6t" data-v-6b5c3829>?</button>`);
      _push(ssrRenderComponent(_component_ThemeToggle, { style: { "color": "var(--color-text-tertiary)" } }, null, _parent));
      _push(`</div></div></div>`);
      _push(ssrRenderComponent(_component_SanakennoRulesModal, {
        show: unref(showRules),
        onClose: ($event) => showRules.value = false
      }, null, _parent));
      _push(`<div class="max-w-sm mx-auto" style="${ssrRenderStyle({ "touch-action": "manipulation" })}" data-v-6b5c3829><div style="${ssrRenderStyle({ "height": "calc(env(safe-area-inset-top) + 1.5rem)" })}" aria-hidden="true" data-v-6b5c3829></div>`);
      if (unref(loading)) {
        _push(`<div class="text-center py-16" style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829> Ladataan... </div>`);
      } else if (unref(fetchError)) {
        _push(`<div class="text-center py-16 text-red-400" role="alert" data-v-6b5c3829>${ssrInterpolate(unref(fetchError))}</div>`);
      } else if (unref(puzzle)) {
        _push(`<!--[--><div class="sticky-score-bar" style="${ssrRenderStyle({ "position": "sticky", "top": "calc(env(safe-area-inset-top) + 3rem)", "z-index": "10", "background-color": "var(--color-bg-primary)", "padding-top": "0.5rem", "padding-bottom": "0.25rem" })}" data-v-6b5c3829><div class="flex items-center gap-2 mb-1" data-v-6b5c3829><span class="text-base font-medium" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}" data-v-6b5c3829> Pisteet: ${ssrInterpolate(unref(score))}</span><button class="px-2 py-0.5 rounded-full text-xs font-medium" style="${ssrRenderStyle({ "background": "var(--color-accent)", "color": "white", "border": "none", "cursor": "pointer" })}"${ssrRenderAttr("aria-expanded", unref(showRanks))} aria-label="N\xE4yt\xE4 tasorajat" data-v-6b5c3829>${ssrInterpolate(unref(rank))}</button><div class="flex items-center gap-2 ml-auto" data-v-6b5c3829>`);
        if (unref(shareCopied)) {
          _push(`<span class="text-xs" style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829>Kopioitu!</span>`);
        } else {
          _push(`<!---->`);
        }
        _push(`<button class="text-xs px-2 py-1 rounded" style="${ssrRenderStyle({ "background": "var(--color-bg-secondary)", "color": "var(--color-text-secondary)", "border": "1px solid var(--color-border)", "cursor": "pointer" })}" data-v-6b5c3829>Jaa tulos</button></div></div><div class="w-full h-1 rounded-full mb-1" style="${ssrRenderStyle({ background: "var(--color-bg-secondary)" })}" data-v-6b5c3829><div class="h-full rounded-full" style="${ssrRenderStyle({ background: "var(--color-accent)", width: unref(progressToNextRank$1) + "%", transition: "width 0.5s ease" })}" data-v-6b5c3829></div></div></div>`);
        if (unref(showRanks)) {
          _push(`<div class="mb-2 p-3 rounded-lg text-sm" style="${ssrRenderStyle({ "background": "var(--color-bg-secondary)", "border": "1px solid var(--color-border)" })}" data-v-6b5c3829><!--[-->`);
          ssrRenderList(unref(rankThresholds$1), (r) => {
            _push(`<div class="flex justify-between py-0.5" style="${ssrRenderStyle({ color: r.isCurrent ? "var(--color-accent)" : "var(--color-text-secondary)", fontWeight: r.isCurrent ? "600" : "400" })}" data-v-6b5c3829><span data-v-6b5c3829>${ssrInterpolate(r.name)}</span><span data-v-6b5c3829>${ssrInterpolate(r.points)}</span></div>`);
          });
          _push(`<!--]--></div>`);
        } else {
          _push(`<!---->`);
        }
        _push(`<div class="mb-2" data-v-6b5c3829><button class="text-sm font-medium" style="${ssrRenderStyle({ "color": "var(--color-text-secondary)", "background": "none", "border": "none", "cursor": "pointer", "padding": "0" })}"${ssrRenderAttr("aria-expanded", unref(showHints))} data-v-6b5c3829><span class="inline-block" style="${ssrRenderStyle({ "vertical-align": "-0.15em" })}" data-v-6b5c3829>${HINT_SVG.bulb}</span> Avut ${ssrInterpolate(unref(showHints) ? "\u25B2" : "\u25BC")}</button>`);
        if (unref(showHints)) {
          _push(`<div class="mt-2 p-3 rounded-lg text-sm space-y-3" style="${ssrRenderStyle({ "background": "var(--color-bg-secondary)", "border": "1px solid var(--color-border)" })}" data-v-6b5c3829><div data-v-6b5c3829><div class="flex items-center justify-between mb-1" style="${ssrRenderStyle(unref(hintsUnlocked).has("summary") ? "cursor:pointer" : "")}" data-v-6b5c3829><span style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829>Yleiskuva <span class="inline-block align-middle ml-1" data-v-6b5c3829>${HINT_SVG.summary}</span></span>`);
          if (!unref(hintsUnlocked).has("summary")) {
            _push(`<button class="text-xs px-2 py-0.5 rounded" style="${ssrRenderStyle({ "background": "var(--color-accent)", "color": "white", "border": "none", "cursor": "pointer" })}" data-v-6b5c3829>Aktivoi</button>`);
          } else {
            _push(`<span class="text-xs" style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)" })}" data-v-6b5c3829>${ssrInterpolate(unref(hintsCollapsed).has("summary") ? "\u25BC" : "\u25B2")}</span>`);
          }
          _push(`</div>`);
          if (unref(hintsUnlocked).has("summary") && !unref(hintsCollapsed).has("summary")) {
            _push(`<div style="${ssrRenderStyle({ "font-family": "var(--font-mono)" })}" data-v-6b5c3829>`);
            if (unref(unfoundLengths)) {
              _push(`<div data-v-6b5c3829><span style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}" data-v-6b5c3829>${ssrInterpolate(unref(puzzle).hint_data.word_count - unref(foundWords).size)}/${ssrInterpolate(unref(puzzle).hint_data.word_count)} sanaa j\xE4ljell\xE4 </span><span style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829>(${ssrInterpolate(Math.round(unref(foundWords).size / unref(puzzle).hint_data.word_count * 100))}%) \xB7 ${ssrInterpolate(unref(pangramStats).remaining)}/${ssrInterpolate(unref(pangramStats).total)} ${ssrInterpolate(unref(pangramStats).total === 1 ? "pangrammi" : "pangrammia")}</span></div>`);
            } else {
              _push(`<!---->`);
            }
            if (unref(unfoundLengths)) {
              _push(`<div style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829>${ssrInterpolate(unref(unfoundLengths).uniqueLengths)} eri ${ssrInterpolate(unref(unfoundLengths).uniqueLengths === 1 ? "sanapituus" : "sanapituutta")} \xB7 Pisin sana ${ssrInterpolate(unref(unfoundLengths).longest)}\xA0merkki\xE4</div>`);
            } else {
              _push(`<div style="${ssrRenderStyle({ "color": "var(--color-accent)" })}" data-v-6b5c3829>kaikki l\xF6ydetty</div>`);
            }
            _push(`</div>`);
          } else {
            _push(`<!---->`);
          }
          _push(`</div><div data-v-6b5c3829><div class="flex items-center justify-between mb-1" style="${ssrRenderStyle(unref(hintsUnlocked).has("letters") ? "cursor:pointer" : "")}" data-v-6b5c3829><span style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829>Alkukirjaimet <span class="inline-block align-middle ml-1" data-v-6b5c3829>${HINT_SVG.letters}</span></span>`);
          if (!unref(hintsUnlocked).has("letters")) {
            _push(`<button class="text-xs px-2 py-0.5 rounded" style="${ssrRenderStyle({ "background": "var(--color-accent)", "color": "white", "border": "none", "cursor": "pointer" })}" data-v-6b5c3829>Aktivoi</button>`);
          } else {
            _push(`<span class="text-xs" style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)" })}" data-v-6b5c3829>${ssrInterpolate(unref(hintsCollapsed).has("letters") ? "\u25BC" : "\u25B2")}</span>`);
          }
          _push(`</div>`);
          if (unref(hintsUnlocked).has("letters") && !unref(hintsCollapsed).has("letters")) {
            _push(`<div class="flex flex-wrap gap-x-3 gap-y-0.5" style="${ssrRenderStyle({ "font-family": "var(--font-mono)" })}" data-v-6b5c3829><!--[-->`);
            ssrRenderList(unref(letterMap), (item) => {
              _push(`<span class="text-sm" style="${ssrRenderStyle({ color: item.remaining === 0 ? "var(--color-text-tertiary)" : "var(--color-text-primary)" })}" data-v-6b5c3829>${ssrInterpolate(item.letter.toUpperCase())}\xA0${ssrInterpolate(item.remaining)}</span>`);
            });
            _push(`<!--]--></div>`);
          } else {
            _push(`<!---->`);
          }
          _push(`</div><div data-v-6b5c3829><div class="flex items-center justify-between mb-1" style="${ssrRenderStyle(unref(hintsUnlocked).has("distribution") ? "cursor:pointer" : "")}" data-v-6b5c3829><span style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829>Pituusjakauma <span class="inline-block align-middle ml-1" data-v-6b5c3829>${HINT_SVG.distribution}</span></span>`);
          if (!unref(hintsUnlocked).has("distribution")) {
            _push(`<button class="text-xs px-2 py-0.5 rounded" style="${ssrRenderStyle({ "background": "var(--color-accent)", "color": "white", "border": "none", "cursor": "pointer" })}" data-v-6b5c3829>Aktivoi</button>`);
          } else {
            _push(`<span class="text-xs" style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)" })}" data-v-6b5c3829>${ssrInterpolate(unref(hintsCollapsed).has("distribution") ? "\u25BC" : "\u25B2")}</span>`);
          }
          _push(`</div>`);
          if (unref(hintsUnlocked).has("distribution") && !unref(hintsCollapsed).has("distribution")) {
            _push(`<div class="flex flex-wrap gap-x-4 gap-y-0.5" style="${ssrRenderStyle({ "font-family": "var(--font-mono)" })}" data-v-6b5c3829><!--[-->`);
            ssrRenderList(unref(lengthDistribution), (item) => {
              _push(`<span class="text-sm" style="${ssrRenderStyle({ color: item.remaining === 0 ? "var(--color-text-tertiary)" : "var(--color-text-primary)" })}" data-v-6b5c3829>${ssrInterpolate(item.len)}: ${ssrInterpolate(item.remaining)}</span>`);
            });
            _push(`<!--]--></div>`);
          } else {
            _push(`<!---->`);
          }
          _push(`</div><div data-v-6b5c3829><div class="flex items-center justify-between mb-1" style="${ssrRenderStyle(unref(hintsUnlocked).has("pairs") ? "cursor:pointer" : "")}" data-v-6b5c3829><span style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829>Alkuparit <span class="inline-block align-middle ml-1" data-v-6b5c3829>${HINT_SVG.pairs}</span></span>`);
          if (!unref(hintsUnlocked).has("pairs")) {
            _push(`<button class="text-xs px-2 py-0.5 rounded" style="${ssrRenderStyle({ "background": "var(--color-accent)", "color": "white", "border": "none", "cursor": "pointer" })}" data-v-6b5c3829>Aktivoi</button>`);
          } else {
            _push(`<span class="text-xs" style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)" })}" data-v-6b5c3829>${ssrInterpolate(unref(hintsCollapsed).has("pairs") ? "\u25BC" : "\u25B2")}</span>`);
          }
          _push(`</div>`);
          if (unref(hintsUnlocked).has("pairs") && !unref(hintsCollapsed).has("pairs")) {
            _push(`<div class="flex flex-wrap gap-x-3 gap-y-0.5" style="${ssrRenderStyle({ "font-family": "var(--font-mono)" })}" data-v-6b5c3829><!--[-->`);
            ssrRenderList(unref(pairMap), (item) => {
              _push(`<span class="text-sm" style="${ssrRenderStyle({ color: item.remaining === 0 ? "var(--color-text-tertiary)" : "var(--color-text-primary)" })}" data-v-6b5c3829>${ssrInterpolate(item.pair.toUpperCase())}\xA0${ssrInterpolate(item.remaining)}</span>`);
            });
            _push(`<!--]--></div>`);
          } else {
            _push(`<!---->`);
          }
          _push(`</div></div>`);
        } else {
          _push(`<!---->`);
        }
        _push(`</div><div class="${ssrRenderClass([{ "word-shake": unref(wordShake) }, "text-center text-2xl mb-2 min-h-[2.5rem] font-light"])}" style="${ssrRenderStyle({ "font-family": "var(--font-mono)", "letter-spacing": "0.15em" })}" data-v-6b5c3829>`);
        if (unref(currentWord)) {
          _push(`<!--[-->`);
          ssrRenderList(unref(currentWordChars), (c, i) => {
            _push(`<span style="${ssrRenderStyle({ color: c.color })}" data-v-6b5c3829>${ssrInterpolate(c.char.toUpperCase())}</span>`);
          });
          _push(`<!--]-->`);
        } else {
          _push(`<span style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)" })}" data-v-6b5c3829>\u2014</span>`);
        }
        _push(`</div><div class="text-center text-sm font-medium mb-2 min-h-[1.25rem]" style="${ssrRenderStyle({
          color: unref(messageType) === "error" ? "#ef4444" : unref(messageType) === "special" ? "var(--color-accent)" : "var(--color-text-secondary)",
          opacity: unref(message) ? 1 : 0,
          transition: "opacity 0.2s"
        })}" role="status" aria-live="polite" data-v-6b5c3829>${ssrInterpolate(unref(message) || "\xA0")}</div><div class="flex justify-center mb-3" data-v-6b5c3829><svg viewBox="18 18 264 264" width="264" height="264" role="group" aria-label="Kirjainkenno" class="select-none" style="${ssrRenderStyle({ "touch-action": "none" })}" data-v-6b5c3829><!--[-->`);
        ssrRenderList(unref(hexes), (hex, i) => {
          _push(`<g role="button"${ssrRenderAttr("aria-label", `Lis\xE4\xE4 kirjain ${hex.letter.toUpperCase()}`)} tabindex="-1" style="${ssrRenderStyle({ "cursor": "pointer" })}" data-v-6b5c3829><polygon${ssrRenderAttr("points", hexPoints(hex.x, hex.y, 47))} style="${ssrRenderStyle({
            fill: hex.isCenter ? "var(--color-accent)" : "var(--color-bg-secondary)",
            stroke: hex.isCenter ? "var(--color-accent)" : "var(--color-border)",
            strokeWidth: "1.5",
            transform: unref(pressedHexIndex) === i ? "scale(0.92)" : "scale(1)",
            transformOrigin: `${hex.x}px ${hex.y}px`,
            transition: "transform 0.08s ease"
          })}" data-v-6b5c3829></polygon><text${ssrRenderAttr("x", hex.x)}${ssrRenderAttr("y", hex.y)} text-anchor="middle" dominant-baseline="central" style="${ssrRenderStyle({
            fill: hex.isCenter ? "#ffffff" : "var(--color-text-primary)",
            fontSize: "20px",
            fontWeight: hex.isCenter ? "700" : "500",
            fontFamily: "var(--font-sans)",
            pointerEvents: "none",
            userSelect: "none"
          })}" data-v-6b5c3829>${ssrInterpolate(hex.letter.toUpperCase())}</text></g>`);
        });
        _push(`<!--]--></svg></div><div class="flex justify-center gap-3 mb-3" data-v-6b5c3829><button class="px-4 py-2 rounded-lg text-sm font-medium" style="${ssrRenderStyle({ "background": "var(--color-bg-secondary)", "color": "var(--color-text-primary)", "border": "1px solid var(--color-border)" })}" data-v-6b5c3829> Poista </button><button class="px-4 py-2 rounded-lg text-sm font-medium" style="${ssrRenderStyle({ "background": "var(--color-bg-secondary)", "color": "var(--color-text-primary)", "border": "1px solid var(--color-border)" })}" data-v-6b5c3829> Sekoita </button><button class="px-4 py-2 rounded-lg text-sm font-medium" style="${ssrRenderStyle({ "background": "var(--color-accent)", "color": "white", "border": "1px solid var(--color-accent)" })}" data-v-6b5c3829> OK </button></div>`);
        if (unref(allFound)) {
          _push(`<div class="text-center py-3 rounded-lg mb-3" style="${ssrRenderStyle({ "background": "var(--color-bg-secondary)", "border": "1px solid var(--color-border)" })}" data-v-6b5c3829><p class="text-2xl mb-1" data-v-6b5c3829>\u{1F389}</p><p class="font-semibold" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}" data-v-6b5c3829>Kaikki ${ssrInterpolate(unref(puzzle).hint_data.word_count)} sanaa l\xF6ydetty!</p></div>`);
        } else {
          _push(`<!---->`);
        }
        if (unref(foundWords).size > 0) {
          _push(`<div data-v-6b5c3829><div class="flex items-center justify-between mb-1" data-v-6b5c3829><p class="text-sm" style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829> L\xF6ydetyt sanat (${ssrInterpolate(unref(foundWords).size)}): </p>`);
          if (unref(foundWords).size > 6 || unref(showAllFoundWords)) {
            _push(`<button class="text-xs" style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)", "background": "none", "border": "none", "cursor": "pointer", "padding": "0" })}" data-v-6b5c3829>${ssrInterpolate(unref(showAllFoundWords) ? "V\xE4hemm\xE4n \u25B2" : "Kaikki \u25BC")}</button>`);
          } else {
            _push(`<!---->`);
          }
          _push(`</div>`);
          if (!unref(showAllFoundWords)) {
            _push(`<div class="flex gap-x-4" style="${ssrRenderStyle({
              overflow: "hidden",
              flexWrap: "nowrap",
              cursor: unref(foundWords).size > 6 ? "pointer" : "default"
            })}" data-v-6b5c3829><!--[-->`);
            ssrRenderList(unref(recentFoundWords), (word) => {
              _push(`<span class="text-sm" style="${ssrRenderStyle({
                color: unref(lastResubmittedWord) === word ? "var(--color-accent)" : "var(--color-text-primary)",
                fontFamily: "var(--font-mono)",
                transition: "color 0.3s"
              })}" data-v-6b5c3829>${ssrInterpolate(word)}</span>`);
            });
            _push(`<!--]--></div>`);
          } else {
            _push(`<div class="flex flex-wrap gap-x-6 gap-y-2" data-v-6b5c3829><!--[-->`);
            ssrRenderList(unref(wordColumns), (col, ci) => {
              _push(`<ul data-v-6b5c3829><!--[-->`);
              ssrRenderList(col, (word) => {
                _push(`<li class="text-sm py-0.5" style="${ssrRenderStyle({
                  color: unref(lastResubmittedWord) === word ? "var(--color-accent)" : "var(--color-text-primary)",
                  fontFamily: "var(--font-mono)",
                  transition: "color 0.3s"
                })}" data-v-6b5c3829>${ssrInterpolate(word)}</li>`);
              });
              _push(`<!--]--></ul>`);
            });
            _push(`<!--]--></div>`);
          }
          _push(`</div>`);
        } else {
          _push(`<!---->`);
        }
        _push(`<!--]-->`);
      } else {
        _push(`<!---->`);
      }
      _push(`</div>`);
      ssrRenderTeleport(_push, (_push2) => {
        var _a, _b, _c, _d;
        if (unref(celebration)) {
          _push2(`<div class="fixed inset-0 z-50 flex items-center justify-center p-4" style="${ssrRenderStyle({ "background": "rgba(0,0,0,0.5)" })}" data-v-6b5c3829><div class="${ssrRenderClass([unref(celebration) === "taysikenno" ? "celebration-card-intense" : "celebration-card", "w-full max-w-sm rounded-xl p-8 text-center"])}" style="${ssrRenderStyle({ "background": "var(--color-bg-primary)" })}" data-v-6b5c3829>`);
          if (unref(celebration) === "taysikenno") {
            _push2(`<p class="text-4xl mb-3" data-v-6b5c3829>\u{1F3C6}</p>`);
          } else {
            _push2(`<p class="text-3xl mb-3" data-v-6b5c3829>\u{1F389}</p>`);
          }
          _push2(`<h2 class="${ssrRenderClass([unref(celebration) === "taysikenno" ? "text-2xl" : "text-xl", "font-bold mb-2"])}" style="${ssrRenderStyle({ "color": "var(--color-accent)" })}" data-v-6b5c3829>${ssrInterpolate(unref(celebration) === "taysikenno" ? "T\xE4ysi kenno!" : "\xC4llistytt\xE4v\xE4!")}</h2><p class="text-sm mb-4" style="${ssrRenderStyle({ "color": "var(--color-text-secondary)" })}" data-v-6b5c3829>`);
          if (unref(celebration) === "taysikenno") {
            _push2(`<!--[--> T\xE4ydellinen tulos! L\xF6ysit kaikki sanat. <!--]-->`);
          } else {
            _push2(`<!--[--> Huikea suoritus! Olet saavuttanut huipputason. <!--]-->`);
          }
          _push2(`</p><p class="text-lg font-semibold" style="${ssrRenderStyle({ "color": "var(--color-text-primary)" })}" data-v-6b5c3829>`);
          if (unref(celebration) === "taysikenno") {
            _push2(`<!--[-->${ssrInterpolate((_a = unref(puzzle)) == null ? void 0 : _a.max_score)} / ${ssrInterpolate((_b = unref(puzzle)) == null ? void 0 : _b.max_score)} pistett\xE4 <!--]-->`);
          } else {
            _push2(`<!--[-->${ssrInterpolate(unref(score))} / ${ssrInterpolate(Math.ceil(0.7 * ((_d = (_c = unref(puzzle)) == null ? void 0 : _c.max_score) != null ? _d : 0)))} pistett\xE4 <!--]-->`);
          }
          _push2(`</p><div class="flex justify-center gap-2 mt-4" data-v-6b5c3829><button class="px-4 py-2 rounded-lg text-sm font-medium" style="${ssrRenderStyle({ "background": "var(--color-bg-secondary)", "color": "var(--color-text-secondary)", "border": "1px solid var(--color-border)", "cursor": "pointer" })}" data-v-6b5c3829> \u{1F4CB} Jaa tulos </button><button class="px-4 py-2 rounded-lg text-sm font-medium" style="${ssrRenderStyle({ "background": "var(--color-accent)", "color": "white", "border": "none", "cursor": "pointer" })}" data-v-6b5c3829>${ssrInterpolate(unref(celebration) === "taysikenno" ? "OK" : "Jatka pelaamista")}</button></div></div></div>`);
        } else {
          _push2(`<!---->`);
        }
      }, "body", false, _parent);
      _push(`<!--]-->`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("pages/sanakenno.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const sanakenno = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-6b5c3829"]]);

export { sanakenno as default };
//# sourceMappingURL=sanakenno-BL0jKzWC.mjs.map
