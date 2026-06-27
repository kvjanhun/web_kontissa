<script setup>
// The projects collection — the only home content that supports
// add / remove / hide / reorder. Backed by /api/admin/projects.
const LOCALES = ['en', 'fi']

const projects = ref([])
const error = ref('')
const success = ref('')

const drawerOpen = ref(false)
const drawerLocale = ref('en')
const draft = ref(null)

onMounted(load)

function emptyTranslation() {
  return { name: '', kind: '', tagline: '', description: '', shot: '', tech: [], links: [] }
}
function emptyDraft() {
  return { id: null, image: '', hidden: false, translations: { en: emptyTranslation(), fi: emptyTranslation() } }
}

async function load() {
  error.value = ''
  try {
    const res = await fetch('/api/admin/projects')
    if (!res.ok) { error.value = 'Failed to load projects'; return }
    projects.value = await res.json()
  } catch {
    error.value = 'Failed to load projects'
  }
}

const ordered = computed(() => [...projects.value].sort((a, b) => a.position - b.position))

function displayName(p) {
  return p.translations?.en?.name || p.translations?.fi?.name || '(untitled)'
}

function openNew() {
  draft.value = emptyDraft()
  drawerLocale.value = 'en'
  drawerOpen.value = true
}
function openEdit(p) {
  const d = { id: p.id, image: p.image || '', hidden: !!p.hidden, translations: {} }
  for (const loc of LOCALES) {
    d.translations[loc] = { ...emptyTranslation(), ...(p.translations?.[loc] || {}) }
    d.translations[loc].tech = [...(p.translations?.[loc]?.tech || [])]
    d.translations[loc].links = (p.translations?.[loc]?.links || []).map(l => ({ ...l }))
  }
  draft.value = d
  drawerLocale.value = 'en'
  drawerOpen.value = true
}
function closeDrawer() { drawerOpen.value = false; draft.value = null }

function techText(loc) { return draft.value.translations[loc].tech.join(', ') }
function setTech(loc, text) {
  draft.value.translations[loc].tech = text.split(',').map(s => s.trim()).filter(Boolean)
}
function addLink(loc) { draft.value.translations[loc].links.push({ label: '', href: '' }) }
function removeLink(loc, i) { draft.value.translations[loc].links.splice(i, 1) }

async function saveDraft() {
  error.value = ''
  success.value = ''
  const d = draft.value
  if (!d.translations.en.name.trim()) { error.value = 'English name is required'; return }

  // Only send a locale's translation if it has a name.
  const translations = {}
  for (const loc of LOCALES) {
    if (d.translations[loc].name.trim()) translations[loc] = d.translations[loc]
  }
  const payload = { image: d.image, hidden: d.hidden, translations }

  const url = d.id == null ? '/api/admin/projects' : `/api/admin/projects/${d.id}`
  const method = d.id == null ? 'POST' : 'PUT'
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    error.value = data.error || 'Save failed'
    return
  }
  success.value = d.id == null ? 'Project created' : 'Project updated'
  closeDrawer()
  await load()
}

async function toggleHidden(p) {
  error.value = ''
  const res = await fetch(`/api/admin/projects/${p.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hidden: !p.hidden }),
  })
  if (!res.ok) { error.value = 'Update failed'; return }
  await load()
}

async function remove(p) {
  if (!confirm(`Delete project "${displayName(p)}"?`)) return
  error.value = ''
  const res = await fetch(`/api/admin/projects/${p.id}`, { method: 'DELETE' })
  if (!res.ok) { error.value = 'Delete failed'; return }
  success.value = 'Project deleted'
  await load()
}

async function move(p, dir) {
  const list = [...ordered.value]
  const idx = list.findIndex(x => x.id === p.id)
  const swap = dir === 'up' ? idx - 1 : idx + 1
  if (swap < 0 || swap >= list.length) return
  ;[list[idx], list[swap]] = [list[swap], list[idx]]
  const order = list.map(x => x.id)
  const res = await fetch('/api/admin/projects/reorder', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order }),
  })
  if (!res.ok) { error.value = 'Reorder failed'; return }
  await load()
}
</script>

<template>
  <div class="pr">
    <div class="pr__head">
      <div>
        <h1 class="pr__title"><Icon name="flat-color-icons:gallery" /> Projects</h1>
        <p class="pr__sub">The “Selected projects” list on the home page. Drag order, hide, add or remove.</p>
      </div>
      <button class="btn btn--new" @click="openNew"><Icon name="flat-color-icons:plus" /> New project</button>
    </div>

    <div v-if="error" class="pr__msg pr__msg--err" role="alert">{{ error }}</div>
    <div v-if="success" class="pr__msg pr__msg--ok" role="status">{{ success }}</div>

    <div class="card">
      <div v-if="!ordered.length" class="pr__empty">No projects yet. Add one above.</div>
      <div v-for="(p, idx) in ordered" :key="p.id" class="row" :class="{ 'row--hidden': p.hidden }">
        <div class="row__reorder">
          <button class="ico" :disabled="idx === 0" title="Move up" @click="move(p, 'up')">▲</button>
          <button class="ico" :disabled="idx === ordered.length - 1" title="Move down" @click="move(p, 'down')">▼</button>
        </div>
        <span class="row__pos">{{ String(p.position).padStart(2, '0') }}</span>
        <div class="row__main">
          <div class="row__name">{{ displayName(p) }}</div>
          <div class="row__meta">{{ p.translations?.en?.kind || p.translations?.fi?.kind || '' }}</div>
        </div>
        <button class="row__vis" :class="{ 'row__vis--hidden': p.hidden }" @click="toggleHidden(p)">
          <Icon :name="p.hidden ? 'flat-color-icons:no-idea' : 'flat-color-icons:ok'" /> {{ p.hidden ? 'Hidden' : 'Live' }}
        </button>
        <div class="row__actions">
          <button class="ico ico--btn" title="Edit" @click="openEdit(p)"><Icon name="flat-color-icons:edit-image" /></button>
          <button class="ico ico--btn" title="Delete" @click="remove(p)"><Icon name="flat-color-icons:full-trash" /></button>
        </div>
      </div>
    </div>

    <!-- Editor drawer -->
    <div v-if="drawerOpen" class="drawer">
      <div class="drawer__scrim" @click="closeDrawer" />
      <div class="drawer__panel">
        <div class="drawer__head">
          <div>
            <h2 class="drawer__title">{{ draft.id == null ? 'New project' : 'Edit project' }}</h2>
            <div class="drawer__sub">{{ displayName(draft) }}</div>
          </div>
          <button class="ico ico--btn" @click="closeDrawer">✕</button>
        </div>

        <div class="drawer__body">
          <!-- parent fields -->
          <div class="field">
            <label class="field__label">Image path <span class="field__hint">(upload handled separately)</span></label>
            <input class="inp" v-model="draft.image" placeholder="/projects/name/cover.webp" />
          </div>
          <label class="check">
            <input type="checkbox" v-model="draft.hidden" /> Hidden (not shown on the public site)
          </label>

          <!-- locale toggle -->
          <div class="drawer__locales">
            <button
              v-for="loc in LOCALES"
              :key="loc"
              class="hc__loc"
              :class="{ 'hc__loc--active': drawerLocale === loc }"
              @click="drawerLocale = loc"
            >{{ loc.toUpperCase() }}</button>
          </div>

          <template v-for="loc in LOCALES" :key="loc">
            <div v-show="drawerLocale === loc" class="locale-fields">
              <div class="field">
                <label class="field__label">Name</label>
                <input class="inp" v-model="draft.translations[loc].name" />
              </div>
              <div class="field">
                <label class="field__label">Kind</label>
                <input class="inp" v-model="draft.translations[loc].kind" placeholder="product · tool · infra" />
              </div>
              <div class="field">
                <label class="field__label">Tagline</label>
                <input class="inp" v-model="draft.translations[loc].tagline" />
              </div>
              <div class="field">
                <label class="field__label">Description</label>
                <textarea class="inp inp--area" rows="4" v-model="draft.translations[loc].description"></textarea>
              </div>
              <div class="field">
                <label class="field__label">Screenshot caption</label>
                <input class="inp" v-model="draft.translations[loc].shot" />
              </div>
              <div class="field">
                <label class="field__label">Tech <span class="field__hint">(comma-separated)</span></label>
                <input class="inp" :value="techText(loc)" @input="setTech(loc, $event.target.value)" />
              </div>
              <div class="field">
                <label class="field__label">Links</label>
                <div class="links">
                  <div v-for="(link, i) in draft.translations[loc].links" :key="i" class="link">
                    <input class="inp" v-model="link.label" placeholder="Label" />
                    <input class="inp" v-model="link.href" placeholder="https://… or /path" />
                    <button class="ico ico--btn" title="Remove" @click="removeLink(loc, i)">✕</button>
                  </div>
                  <button class="btn btn--ghost" @click="addLink(loc)"><Icon name="flat-color-icons:plus" /> Add link</button>
                </div>
              </div>
            </div>
          </template>
        </div>

        <div class="drawer__foot">
          <button class="btn btn--ghost" @click="closeDrawer">Cancel</button>
          <button class="btn btn--save" @click="saveDraft"><Icon name="flat-color-icons:ok" /> Save project</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pr { max-width: 1000px; margin: 0 auto; }
.pr__head { display: flex; align-items: flex-end; justify-content: space-between; gap: 14px; margin-bottom: 18px; flex-wrap: wrap; }
.pr__title { margin: 0 0 4px; font-size: 23px; font-weight: 600; display: flex; align-items: center; gap: 9px; }
.pr__sub { margin: 0; font-size: 14px; color: var(--as-tx-2); }

.pr__msg { padding: 10px 14px; border-radius: 9px; font-size: 13px; margin-bottom: 14px; }
.pr__msg--err { background: #fdece5; color: #c0392b; }
.pr__msg--ok { background: #e7f5e8; color: #2e7d32; }

.card { background: var(--as-panel); border: 1px solid var(--as-line); border-radius: 13px; overflow: hidden; }
.pr__empty { padding: 28px; text-align: center; color: var(--as-tx-2); font-size: 14px; }

.row { display: grid; grid-template-columns: 40px 44px 1fr auto auto; gap: 14px; align-items: center; padding: 12px 18px; border-bottom: 1px solid #f3f3ec; }
.row:last-child { border-bottom: none; }
.row--hidden { opacity: 0.6; }
.row__reorder { display: flex; flex-direction: column; gap: 2px; }
.row__pos { font-family: var(--font-mono, monospace); font-size: 13px; color: var(--as-tx-3); }
.row__name { font-size: 14px; font-weight: 600; }
.row__meta { font-size: 11.5px; color: var(--as-tx-3); font-family: var(--font-mono, monospace); margin-top: 2px; }
.row__vis { display: inline-flex; align-items: center; gap: 6px; border: none; background: none; cursor: pointer; font-size: 12.5px; font-weight: 500; color: #43a047; }
.row__vis--hidden { color: var(--as-tx-3); }
.row__actions { display: flex; gap: 4px; }

.ico { border: none; background: none; cursor: pointer; color: var(--as-tx-3); font-size: 11px; line-height: 1; padding: 2px; }
.ico:disabled { opacity: 0.25; cursor: not-allowed; }
.ico--btn { width: 30px; height: 30px; border: 1px solid var(--as-line); border-radius: 7px; display: inline-flex; align-items: center; justify-content: center; font-size: 15px; color: var(--as-tx-2); }
.ico--btn:hover { background: #f3f3ee; }

.btn { display: inline-flex; align-items: center; gap: 8px; height: 40px; padding: 0 16px; border-radius: 8px; font-size: 13.5px; font-weight: 600; cursor: pointer; border: none; }
.btn--new { background: var(--as-accent); color: #fff; }
.btn--save { background: var(--as-tx); color: #fff; }
.btn--ghost { background: #fff; border: 1px solid #dcdcd6; color: #3c4047; }

/* Drawer */
.drawer { position: fixed; inset: 0; z-index: 90; display: flex; justify-content: flex-end; }
.drawer__scrim { position: absolute; inset: 0; background: rgba(20, 22, 27, 0.32); }
.drawer__panel { position: relative; width: 480px; max-width: 94vw; height: 100%; background: #fff; box-shadow: -12px 0 40px rgba(0, 0, 0, 0.16); display: flex; flex-direction: column; }
.drawer__head { padding: 18px 22px; border-bottom: 1px solid var(--as-line-2); display: flex; align-items: center; justify-content: space-between; }
.drawer__title { margin: 0; font-size: 17px; font-weight: 600; }
.drawer__sub { font-size: 11.5px; color: var(--as-tx-3); font-family: var(--font-mono, monospace); }
.drawer__body { flex: 1; overflow-y: auto; padding: 20px 22px; }
.drawer__foot { padding: 14px 22px; border-top: 1px solid var(--as-line-2); display: flex; gap: 10px; justify-content: flex-end; }
.drawer__locales { display: inline-flex; gap: 4px; background: var(--as-bg); border: 1px solid var(--as-line); border-radius: 9px; padding: 4px; margin: 8px 0 16px; }
.hc__loc { font-family: var(--font-mono, monospace); font-size: 12px; font-weight: 500; padding: 6px 13px; border: none; border-radius: 6px; cursor: pointer; background: transparent; color: var(--as-tx-2); }
.hc__loc--active { background: var(--as-tx); color: #fff; }

.field { margin-bottom: 14px; }
.field__label { display: block; font-size: 12px; font-weight: 600; color: #3c4047; margin-bottom: 6px; }
.field__hint { color: var(--as-tx-3); font-weight: 400; }
.inp { width: 100%; min-height: 38px; padding: 8px 12px; border: 1px solid #dcdcd6; border-radius: 8px; font-size: 14px; background: #fff; outline: none; color: var(--as-tx); }
.inp:focus { border-color: var(--as-accent); box-shadow: 0 0 0 3px rgba(255, 106, 61, 0.13); }
.inp--area { resize: vertical; line-height: 1.5; }
.check { display: flex; align-items: center; gap: 8px; font-size: 13.5px; color: #3c4047; margin-bottom: 6px; cursor: pointer; }
.links { display: flex; flex-direction: column; gap: 8px; }
.link { display: grid; grid-template-columns: 1fr 1fr 30px; gap: 8px; align-items: center; }

@media (max-width: 720px) {
  .row { grid-template-columns: 36px 1fr auto; }
  .row__pos, .row__vis { display: none; }
}
</style>
