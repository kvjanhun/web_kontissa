<script setup>
// Home-page text blocks editor. The set of fields is fixed (only projects are
// add/remove/reorder, handled in AdminProjects); here you edit the copy of each
// block. Keys + value shapes mirror HOME_CONTENT_FIELDS in app/home_content.py.
//
// Every group maps to a visible band on the landing page and every field carries
// a `hint` describing exactly what that piece of copy is and where it shows up,
// so the editor is self-explanatory without opening the live page side by side.
// Groups are collapsible disclosure sections (default collapsed).
const LOCALES = ['en', 'fi']

const GROUPS = [
  {
    title: 'Hero',
    where: 'The top of the page — the first thing a visitor sees.',
    fields: [
      {
        key: 'home.hero.eyebrow', label: 'Eyebrow', type: 'text',
        hint: 'Small uppercase line above the headline — your role tag.',
      },
      {
        key: 'home.hero.taglines', label: 'Rotating headline', type: 'string-list',
        hint: 'The big headline cycles through these one phrase at a time. Keep them short; a trailing period is shown in the accent colour.',
        itemLabel: 'Phrase', addLabel: 'Add phrase',
      },
      {
        key: 'home.hero.titleLine2', label: 'Headline — fixed second line', type: 'text',
        hint: 'Stays put under the rotating phrase.',
      },
      {
        key: 'home.hero.body', label: 'Intro paragraph', type: 'textarea',
        hint: 'The paragraph under the headline.',
      },
      {
        key: 'home.hero.ctaPrimary', label: 'Primary button', type: 'text',
        hint: 'Solid orange button. Scrolls down to the projects section.',
      },
      {
        key: 'home.hero.ctaSecondary', label: 'Secondary button', type: 'text',
        hint: 'Outlined button. Scrolls down to the stack section.',
      },
    ],
  },
  {
    title: 'Stack',
    where: 'The “02 — The stack” section with the layered table.',
    fields: [
      {
        key: 'home.stack.label', label: 'Section title', type: 'text',
        hint: 'Shown after the number, as “02 — <this>”.',
      },
      {
        key: 'home.stack.tag', label: 'Section tag', type: 'text',
        hint: 'Small mono text to the right of the title.',
      },
      {
        key: 'home.stack.intro', label: 'Intro paragraph', type: 'textarea',
        hint: 'Sits above the layer table.',
      },
      {
        key: 'home.stack.layers', label: 'Layers', type: 'layer-list',
        hint: 'One row per layer of the table, in the order listed here (top to bottom).',
        itemLabel: 'Layer', addLabel: 'Add layer',
      },
      {
        key: 'home.stack.footnote', label: 'Footnote', type: 'textarea',
        hint: 'Small mono note under the table. The leading “//” is part of the text.',
      },
    ],
  },
  {
    title: 'Footer',
    where: 'The bottom of the page.',
    fields: [
      {
        key: 'home.footer.blurb', label: 'About blurb', type: 'textarea',
        hint: 'Short paragraph under the “erez.ac” wordmark.',
      },
      {
        key: 'home.footer.connectLinks', label: 'Connect links', type: 'link-list',
        hint: 'The “Connect” column — GitHub, LinkedIn, email and the like.',
        addLabel: 'Add link',
      },
      {
        key: 'home.footer.siteLinks', label: 'Site links', type: 'link-list',
        hint: 'The “Site” column — links to your other sites and pages.',
        addLabel: 'Add link',
      },
      {
        key: 'home.footer.nuc', label: 'Status line', type: 'text',
        hint: 'Small mono quip shown under the site links.',
      },
      {
        key: 'home.footer.copyright', label: 'Copyright line', type: 'text',
        hint: 'The bottom-most line of the page.',
      },
    ],
  },
]

const LIST_TYPES = ['string-list', 'layer-list', 'link-list']

function emptyFor(type) {
  return LIST_TYPES.includes(type) ? [] : ''
}
function newItem(type) {
  if (type === 'layer-list') return { z: '', layer: '', title: '', detail: '' }
  if (type === 'link-list') return { label: '', href: '' }
  return '' // string-list
}

const activeLocale = ref('en')
const draft = ref({ en: {}, fi: {} })
const original = ref({ en: {}, fi: {} })
const loaded = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')
const collapsed = ref(Object.fromEntries(GROUPS.map(g => [g.title, true])))

function toggleGroup(title) {
  collapsed.value[title] = !collapsed.value[title]
}

onMounted(load)

async function load() {
  error.value = ''
  try {
    const res = await fetch('/api/admin/home-content')
    if (!res.ok) { error.value = 'Failed to load content'; return }
    const data = await res.json()
    for (const loc of LOCALES) {
      const filled = {}
      for (const group of GROUPS) {
        for (const f of group.fields) {
          const v = data[loc]?.[f.key]
          filled[f.key] = v !== undefined ? v : emptyFor(f.type)
        }
      }
      draft.value[loc] = filled
      original.value[loc] = JSON.parse(JSON.stringify(filled))
    }
    loaded.value = true
  } catch {
    error.value = 'Failed to load content'
  }
}

function isDirty(loc, key) {
  return JSON.stringify(draft.value[loc][key]) !== JSON.stringify(original.value[loc][key])
}

const dirtyKeys = computed(() => {
  const out = []
  for (const loc of LOCALES) {
    for (const key of Object.keys(draft.value[loc] || {})) {
      if (isDirty(loc, key)) out.push({ loc, key })
    }
  }
  return out
})

// Does the active locale have unsaved edits in a different locale? (Heads-up so a
// save that touches both is not a surprise.)
const dirtyOtherLocale = computed(() =>
  dirtyKeys.value.some(d => d.loc !== activeLocale.value),
)

// Unsaved fields within a group (across both locales) — surfaced on the header
// when the group is collapsed so hidden edits are never a surprise.
function groupDirtyCount(group) {
  let n = 0
  for (const loc of LOCALES) {
    for (const f of group.fields) {
      if (isDirty(loc, f.key)) n++
    }
  }
  return n
}

async function save() {
  error.value = ''
  success.value = ''
  saving.value = true
  try {
    for (const { loc, key } of dirtyKeys.value) {
      const res = await fetch('/api/admin/home-content', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, locale: loc, value: draft.value[loc][key] }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        const field = GROUPS.flatMap(g => g.fields).find(f => f.key === key)
        error.value = `${field?.label || key} (${loc.toUpperCase()}): ${data.error || 'save failed'}`
        return
      }
    }
    original.value = JSON.parse(JSON.stringify(draft.value))
    success.value = 'Saved — changes are live.'
  } finally {
    saving.value = false
  }
}

// --- active-locale value accessors + list mutations ------------------------ //
function val(key) {
  return draft.value[activeLocale.value][key]
}
function setVal(key, v) {
  draft.value[activeLocale.value][key] = v
}
function addItem(f) {
  val(f.key).push(newItem(f.type))
}
function removeItem(f, i) {
  val(f.key).splice(i, 1)
}
function moveItem(f, i, dir) {
  const arr = val(f.key)
  const j = dir === 'up' ? i - 1 : i + 1
  if (j < 0 || j >= arr.length) return
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
}
</script>

<template>
  <div class="hc">
    <div class="hc__head">
      <div>
        <h1 class="hc__title"><Icon name="flat-color-icons:document" /> Home content</h1>
        <p class="hc__sub">
          Edit the text on the landing page. Pick a language, make your changes, and save —
          edits go live straight away. Projects are managed under <strong>Projects</strong>.
        </p>
      </div>
      <div class="hc__locales" role="group" aria-label="Language">
        <button
          v-for="loc in LOCALES"
          :key="loc"
          class="hc__loc"
          :class="{ 'hc__loc--active': activeLocale === loc }"
          @click="activeLocale = loc"
        >{{ loc === 'en' ? 'English' : 'Suomi' }}</button>
      </div>
    </div>

    <div v-if="error" class="hc__msg hc__msg--err" role="alert">{{ error }}</div>
    <div v-if="success" class="hc__msg hc__msg--ok" role="status">{{ success }}</div>

    <div v-if="!loaded && !error" class="hc__loading">Loading…</div>

    <template v-else>
      <div v-for="group in GROUPS" :key="group.title" class="card group">
        <div class="group__head" :class="{ 'group__head--collapsed': collapsed[group.title] }">
          <div class="group__bar">
            <h2 class="group__title">
              <button
                class="group__toggle"
                :aria-expanded="!collapsed[group.title]"
                @click="toggleGroup(group.title)"
              >
                <Icon
                  name="solar:alt-arrow-down-bold"
                  class="group__chev"
                  :class="{ 'group__chev--collapsed': collapsed[group.title] }"
                  aria-hidden="true"
                />
                {{ group.title }}
              </button>
            </h2>
            <span v-if="collapsed[group.title] && groupDirtyCount(group)" class="group__badge">
              {{ groupDirtyCount(group) }} unsaved
            </span>
          </div>
          <p class="group__where">{{ group.where }}</p>
        </div>

        <div v-show="!collapsed[group.title]" class="group__fields">
          <div
            v-for="f in group.fields"
            :key="f.key"
            class="field"
            :class="{ 'field--dirty': isDirty(activeLocale, f.key) }"
          >
            <label class="field__label">
              {{ f.label }}
              <span v-if="isDirty(activeLocale, f.key)" class="field__badge">unsaved</span>
            </label>
            <p class="field__hint">{{ f.hint }}</p>

            <!-- scalar -->
            <input
              v-if="f.type === 'text'"
              class="inp"
              :value="val(f.key)"
              @input="setVal(f.key, $event.target.value)"
            />
            <textarea
              v-else-if="f.type === 'textarea'"
              class="inp inp--area"
              rows="3"
              :value="val(f.key)"
              @input="setVal(f.key, $event.target.value)"
            ></textarea>

            <!-- string list (rotating headline phrases) -->
            <div v-else-if="f.type === 'string-list'" class="list">
              <div v-for="(s, i) in val(f.key)" :key="i" class="item item--row">
                <span class="item__num">{{ i + 1 }}</span>
                <input
                  class="inp"
                  :value="s"
                  :placeholder="f.itemLabel"
                  @input="val(f.key)[i] = $event.target.value"
                />
                <div class="item__ctl">
                  <button class="ico" :disabled="i === 0" title="Move up" @click="moveItem(f, i, 'up')">▲</button>
                  <button class="ico" :disabled="i === val(f.key).length - 1" title="Move down" @click="moveItem(f, i, 'down')">▼</button>
                  <button class="ico ico--del" title="Remove" @click="removeItem(f, i)"><Icon name="flat-color-icons:full-trash" /></button>
                </div>
              </div>
              <button class="btn btn--add" @click="addItem(f)"><Icon name="flat-color-icons:plus" /> {{ f.addLabel }}</button>
            </div>

            <!-- stack layers -->
            <div v-else-if="f.type === 'layer-list'" class="list">
              <div v-for="(layer, i) in val(f.key)" :key="i" class="item item--card">
                <div class="item__bar">
                  <span class="item__num">{{ f.itemLabel }} {{ i + 1 }}</span>
                  <div class="item__ctl">
                    <button class="ico" :disabled="i === 0" title="Move up" @click="moveItem(f, i, 'up')">▲</button>
                    <button class="ico" :disabled="i === val(f.key).length - 1" title="Move down" @click="moveItem(f, i, 'down')">▼</button>
                    <button class="ico ico--del" title="Remove" @click="removeItem(f, i)"><Icon name="flat-color-icons:full-trash" /></button>
                  </div>
                </div>
                <div class="layer-grid">
                  <div class="sub">
                    <label class="sub__label">Level</label>
                    <input class="inp inp--z" :value="layer.z" placeholder="L7" @input="layer.z = $event.target.value" />
                  </div>
                  <div class="sub">
                    <label class="sub__label">Layer</label>
                    <input class="inp" :value="layer.layer" placeholder="Interface" @input="layer.layer = $event.target.value" />
                  </div>
                  <div class="sub">
                    <label class="sub__label">Title</label>
                    <input class="inp" :value="layer.title" placeholder="Frontend" @input="layer.title = $event.target.value" />
                  </div>
                  <div class="sub sub--full">
                    <label class="sub__label">Detail</label>
                    <textarea class="inp inp--area" rows="2" :value="layer.detail" placeholder="What this layer does…" @input="layer.detail = $event.target.value"></textarea>
                  </div>
                </div>
              </div>
              <button class="btn btn--add" @click="addItem(f)"><Icon name="flat-color-icons:plus" /> {{ f.addLabel }}</button>
            </div>

            <!-- link list -->
            <div v-else-if="f.type === 'link-list'" class="list">
              <div v-for="(link, i) in val(f.key)" :key="i" class="item item--card">
                <div class="link-grid">
                  <div class="sub">
                    <label class="sub__label">Text</label>
                    <input class="inp" :value="link.label" placeholder="GitHub" @input="link.label = $event.target.value" />
                  </div>
                  <div class="sub">
                    <label class="sub__label">Link</label>
                    <input class="inp" :value="link.href" placeholder="https://… or /path" @input="link.href = $event.target.value" />
                  </div>
                  <div class="item__ctl item__ctl--end">
                    <button class="ico" :disabled="i === 0" title="Move up" @click="moveItem(f, i, 'up')">▲</button>
                    <button class="ico" :disabled="i === val(f.key).length - 1" title="Move down" @click="moveItem(f, i, 'down')">▼</button>
                    <button class="ico ico--del" title="Remove" @click="removeItem(f, i)"><Icon name="flat-color-icons:full-trash" /></button>
                  </div>
                </div>
              </div>
              <button class="btn btn--add" @click="addItem(f)"><Icon name="flat-color-icons:plus" /> {{ f.addLabel }}</button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div class="hc__bar">
      <span class="hc__dirty">
        <template v-if="dirtyKeys.length">
          {{ dirtyKeys.length }} unsaved {{ dirtyKeys.length === 1 ? 'change' : 'changes' }}<template v-if="dirtyOtherLocale"> (both languages)</template>
        </template>
        <template v-else>No unsaved changes</template>
      </span>
      <button class="btn btn--save" :disabled="!dirtyKeys.length || saving" @click="save">
        <Icon name="flat-color-icons:ok" /> {{ saving ? 'Saving…' : 'Save changes' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.hc { max-width: 820px; margin: 0 auto; padding-bottom: 80px; }
.hc__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 18px; flex-wrap: wrap; }
.hc__title { margin: 0 0 6px; font-size: 23px; font-weight: 600; display: flex; align-items: center; gap: 9px; }
.hc__sub { margin: 0; max-width: 52ch; font-size: 13.5px; line-height: 1.55; color: var(--as-tx-2); }
.hc__sub strong { color: var(--as-tx); font-weight: 600; }
.hc__locales { display: flex; gap: 4px; background: var(--as-panel); border: 1px solid var(--as-line); border-radius: 9px; padding: 4px; flex: none; }
.hc__loc { font-size: 12.5px; font-weight: 500; padding: 6px 14px; border: none; border-radius: 6px; cursor: pointer; background: transparent; color: var(--as-tx-2); }
.hc__loc--active { background: var(--as-tx); color: #fff; }

.hc__msg { padding: 10px 14px; border-radius: 9px; font-size: 13px; margin-bottom: 14px; }
.hc__msg--err { background: #fdece5; color: #c0392b; }
.hc__msg--ok { background: #e7f5e8; color: #2e7d32; }
.hc__loading { padding: 40px; text-align: center; color: var(--as-tx-3); font-size: 14px; }

.card { background: var(--as-panel); border: 1px solid var(--as-line); border-radius: 13px; padding: 20px; margin-bottom: 14px; }

/* Collapsible group header (disclosure) */
.group__head { margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid var(--as-line-2); }
.group__head--collapsed { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
.group__bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.group__title { margin: 0; font-size: 16px; font-weight: 600; }
.group__toggle {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  background: none;
  border: none;
  font: inherit;
  color: inherit;
  cursor: pointer;
  padding: 4px 8px;
  margin-left: -8px;
  border-radius: 7px;
}
.group__toggle:hover { color: var(--as-accent); background: rgba(0, 0, 0, 0.03); }
.group__chev { font-size: 17px; color: var(--as-tx-3); flex: none; transition: transform 0.18s ease; }
.group__chev--collapsed { transform: rotate(-90deg); }
.group__toggle:hover .group__chev { color: var(--as-accent); }
.group__badge { font-size: 11px; font-weight: 600; color: var(--as-accent); background: rgba(255, 106, 61, 0.12); padding: 3px 9px; border-radius: 20px; flex: none; white-space: nowrap; }
.group__where { margin: 6px 0 0; padding-left: 2px; font-size: 12.5px; color: var(--as-tx-3); }

.field { margin-bottom: 22px; }
.field:last-child { margin-bottom: 0; }
.field__label { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: #3c4047; margin-bottom: 3px; }
.field__badge { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--as-accent); background: rgba(255, 106, 61, 0.12); padding: 2px 7px; border-radius: 20px; }
.field__hint { margin: 0 0 9px; font-size: 12px; line-height: 1.45; color: var(--as-tx-2); }

.inp {
  width: 100%;
  min-height: 38px;
  padding: 8px 12px;
  border: 1px solid #dcdcd6;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
  outline: none;
  color: var(--as-tx);
}
.inp:focus { border-color: var(--as-accent); box-shadow: 0 0 0 3px rgba(255, 106, 61, 0.13); }
.inp--area { resize: vertical; line-height: 1.5; }
.inp--z { font-family: var(--font-mono, monospace); text-align: center; }

/* List items (phrases / layers / links) */
.list { display: flex; flex-direction: column; gap: 10px; }
.item__num { font-size: 12px; font-weight: 600; color: var(--as-tx-3); font-family: var(--font-mono, monospace); }

.item--row { display: grid; grid-template-columns: 22px 1fr auto; gap: 10px; align-items: center; }
.item--row .item__num { text-align: center; }

.item--card { border: 1px solid var(--as-line); border-radius: 10px; padding: 12px; background: #fbfbf9; }
.item__bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }

.item__ctl { display: flex; align-items: center; gap: 2px; }
.item__ctl--end { align-self: end; padding-bottom: 1px; }

.layer-grid { display: grid; grid-template-columns: 70px 1fr 1fr; gap: 10px; }
.layer-grid .sub--full { grid-column: 1 / -1; }
.link-grid { display: grid; grid-template-columns: 1fr 1.6fr auto; gap: 10px; align-items: end; }

.sub { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.sub__label { font-size: 11px; font-weight: 600; color: var(--as-tx-2); text-transform: uppercase; letter-spacing: 0.04em; }

.ico { border: none; background: none; cursor: pointer; color: var(--as-tx-3); font-size: 11px; line-height: 1; padding: 5px; border-radius: 6px; display: inline-flex; align-items: center; justify-content: center; }
.ico:hover:not(:disabled) { background: rgba(0, 0, 0, 0.05); color: var(--as-tx-2); }
.ico:disabled { opacity: 0.25; cursor: not-allowed; }
.ico--del { font-size: 15px; }

.btn { display: inline-flex; align-items: center; gap: 8px; height: 40px; padding: 0 16px; border-radius: 8px; font-size: 13.5px; font-weight: 600; cursor: pointer; border: none; }
.btn--add { align-self: flex-start; height: 34px; padding: 0 13px; font-size: 12.5px; background: #fff; border: 1px dashed #cfcfc8; color: #3c4047; }
.btn--add:hover { border-color: var(--as-accent); color: var(--as-accent); }
.btn--save { background: var(--as-tx); color: #fff; }
.btn--save:disabled { opacity: 0.45; cursor: not-allowed; }

.hc__bar {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  padding: 14px 0;
  background: linear-gradient(transparent, var(--as-bg) 40%);
}
.hc__dirty { font-size: 12.5px; color: var(--as-tx-2); font-family: var(--font-mono, monospace); }

@media (max-width: 720px) {
  .layer-grid { grid-template-columns: 70px 1fr; }
  .layer-grid .sub--full { grid-column: 1 / -1; }
  .link-grid { grid-template-columns: 1fr auto; }
}
</style>
