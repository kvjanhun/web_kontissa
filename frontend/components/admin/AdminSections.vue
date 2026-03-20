<script setup>
const { t } = useI18nStore()

const sections = ref([])
const editingId = ref(null)
const error = ref('')
const success = ref('')
const activeLocale = ref('en')
const showHiddenPanel = ref(false)

const TYPE_COLORS = {
  text: 'bg-stone-500/20 text-stone-400',
  pills: 'bg-blue-500/20 text-blue-400',
  quote: 'bg-purple-500/20 text-purple-400',
  currently: 'bg-green-500/20 text-green-400',
  intro: 'bg-amber-500/20 text-amber-400',
  project: 'bg-cyan-500/20 text-cyan-400',
  git_stats: 'bg-indigo-500/20 text-indigo-400',
  timeline: 'bg-violet-500/20 text-violet-400',
}

const SECTION_TYPES = ['text', 'pills', 'quote', 'currently', 'intro', 'project', 'git_stats', 'timeline']

// Card types that use the position-based layout (0–9 full, 10–19 left, 20–29 right)
const CARD_TYPES = new Set(['text', 'currently', 'project', 'git_stats', 'timeline'])

const PLACEMENT_OPTIONS = [
  { value: 'full', label: 'Full width', min: 0, max: 9 },
  { value: 'left', label: 'Left column', min: 10, max: 19 },
  { value: 'right', label: 'Right column', min: 20, max: 29 },
]

const PLACEHOLDERS = {
  text: 'Content (Markdown). Use **bold**, *italic*, [link text](url). Blank lines create new paragraphs.',
  pills: 'Comma-separated values, e.g. Python, Flask, Vue.js',
  quote: 'A short tagline or quote',
  currently: 'One item per line, e.g.\nPlaying: Elden Ring\nReading: SICP',
  intro: 'Plain text intro paragraph',
  project: 'One project per line: Name|URL|Description\ne.g. Sanakenno|/sanakenno|Finnish word puzzle game',
  git_stats: 'Optional description shown below the title (leave empty to show only the live stats grid)',
  timeline: 'One entry per line: YYYY-MM-DD|Title|Description\ne.g.\n2025-04-06|Born on a NUC|Flask + Docker from day one',
}

const form = ref({ title: '', slug: '', content: '', section_type: 'text', placement: 'left', collapsible: false })
const editForm = ref({ title: '', slug: '', content: '', section_type: 'text', placement: 'left', collapsible: false })

onMounted(() => loadSections())

function clearMessages() {
  error.value = ''
  success.value = ''
}

function switchLocale(loc) {
  activeLocale.value = loc
  loadSections()
}

// Visible and hidden sections
const visibleSections = computed(() => sections.value.filter(s => !s.hidden))
const hiddenSections = computed(() => sections.value.filter(s => s.hidden))

// Determine placement label from position number
function placementFromPosition(pos) {
  if (pos == null || pos < 10) return 'full'
  if (pos < 20) return 'left'
  return 'right'
}

// Find next available position in a placement range (only checks visible sections)
function nextPosition(placement, excludeId = null) {
  const opt = PLACEMENT_OPTIONS.find(o => o.value === placement)
  if (!opt) return null
  const used = new Set(
    visibleSections.value
      .filter(s => s.id !== excludeId && (s.position ?? 0) >= opt.min && (s.position ?? 0) <= opt.max)
      .map(s => s.position)
  )
  for (let i = opt.min; i <= opt.max; i++) {
    if (!used.has(i)) return i
  }
  return null
}

function isCardType(type) {
  return CARD_TYPES.has(type)
}


const pillsSections = computed(() =>
  visibleSections.value
    .filter(s => s.section_type === 'pills')
    .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
)

const otherSections = computed(() =>
  visibleSections.value.filter(s => s.section_type !== 'pills')
)

const cardGroups = computed(() => {
  const cards = otherSections.value.filter(s => isCardType(s.section_type))
  return PLACEMENT_OPTIONS
    .map(opt => ({
      ...opt,
      sections: cards
        .filter(s => { const pos = s.position ?? 0; return pos >= opt.min && pos <= opt.max })
        .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
    }))
    .filter(g => g.sections.length > 0)
})

const singletonSections = computed(() =>
  otherSections.value.filter(s => !isCardType(s.section_type))
)

async function moveCard(section, direction) {
  clearMessages()
  const placement = placementFromPosition(section.position)
  const group = cardGroups.value.find(g => g.value === placement)
  if (!group) return
  const idx = group.sections.findIndex(s => s.id === section.id)
  const swapIdx = direction === 'up' ? idx - 1 : idx + 1
  if (swapIdx < 0 || swapIdx >= group.sections.length) return
  const other = group.sections[swapIdx]
  await Promise.all([
    fetch(`/api/sections/${section.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position: other.position ?? 0 })
    }),
    fetch(`/api/sections/${other.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position: section.position ?? 0 })
    })
  ])
  await loadSections()
}

async function movePill(section, direction) {
  clearMessages()
  const pills = pillsSections.value
  const idx = pills.findIndex(s => s.id === section.id)
  const swapIdx = direction === 'up' ? idx - 1 : idx + 1
  if (swapIdx < 0 || swapIdx >= pills.length) return
  const other = pills[swapIdx]
  const posA = section.position ?? idx
  const posB = other.position ?? swapIdx
  await Promise.all([
    fetch(`/api/sections/${section.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position: posB })
    }),
    fetch(`/api/sections/${other.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position: posA })
    })
  ])
  await loadSections()
}

async function loadSections() {
  const res = await fetch(`/api/sections?locale=${activeLocale.value}&include_hidden=1`)
  sections.value = await res.json()
}

async function createSection() {
  clearMessages()
  const payload = { ...form.value, locale: activeLocale.value }
  if (isCardType(payload.section_type)) {
    const pos = nextPosition(payload.placement)
    if (pos === null) { error.value = `No slots available in "${payload.placement}" placement (max 10)`; return }
    payload.position = pos
  }
  if (payload.section_type !== 'text') delete payload.collapsible
  delete payload.placement
  const res = await fetch('/api/sections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  const data = await res.json()
  if (!res.ok) { error.value = data.error; return }
  form.value = { title: '', slug: '', content: '', section_type: 'text', placement: 'left', collapsible: false }
  success.value = t('admin.created')
  await loadSections()
}

function startEdit(section) {
  editingId.value = section.id
  editForm.value = {
    title: section.title,
    slug: section.slug,
    content: section.content,
    section_type: section.section_type || 'text',
    placement: placementFromPosition(section.position),
    collapsible: section.collapsible || false
  }
}

function cancelEdit() { editingId.value = null }

async function saveEdit(id) {
  clearMessages()
  const payload = { ...editForm.value }
  if (payload.section_type !== 'text') delete payload.collapsible
  if (isCardType(payload.section_type)) {
    const section = sections.value.find(s => s.id === id)
    const oldPlacement = placementFromPosition(section?.position)
    if (payload.placement !== oldPlacement) {
      const pos = nextPosition(payload.placement, id)
      if (pos === null) { error.value = `No slots available in "${payload.placement}" placement (max 10)`; return }
      payload.position = pos
    } else {
      payload.position = section?.position ?? 0
    }
  }
  delete payload.placement
  const res = await fetch(`/api/sections/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  const data = await res.json()
  if (!res.ok) { error.value = data.error; return }
  editingId.value = null
  success.value = t('admin.updated')
  await loadSections()
}

async function deleteSection(id) {
  if (!confirm(t('admin.confirmDelete'))) return
  clearMessages()
  const res = await fetch(`/api/sections/${id}`, { method: 'DELETE' })
  if (!res.ok) { const data = await res.json(); error.value = data.error; return }
  success.value = t('admin.deleted')
  await loadSections()
}

async function toggleHidden(section) {
  clearMessages()
  const res = await fetch(`/api/sections/${section.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hidden: !section.hidden })
  })
  if (!res.ok) { const data = await res.json(); error.value = data.error; return }
  success.value = section.hidden ? t('admin.restored') : t('admin.hidden')
  await loadSections()
}

function placeholderFor(type) {
  return PLACEHOLDERS[type] || PLACEHOLDERS.text
}

async function updatePosition(section, newPosition) {
  clearMessages()
  if (newPosition < 0) { error.value = 'Position must be >= 0'; return }
  if (isCardType(section.section_type) && newPosition > 29) { error.value = 'Position must be 0–29'; return }
  const res = await fetch(`/api/sections/${section.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ position: newPosition })
  })
  if (!res.ok) { const data = await res.json(); error.value = data.error; return }
  await loadSections()
}

async function updatePlacement(section, newPlacement) {
  clearMessages()
  const pos = nextPosition(newPlacement, section.id)
  if (pos === null) { error.value = `No slots available in "${newPlacement}" (max 10)`; return }
  await updatePosition(section, pos)
}

async function toggleCollapsible(section) {
  clearMessages()
  const res = await fetch(`/api/sections/${section.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ collapsible: !section.collapsible })
  })
  if (!res.ok) { const data = await res.json(); error.value = data.error; return }
  await loadSections()
}
</script>

<template>
  <div class="space-y-4">
    <!-- Locale toggle -->
    <div class="flex gap-2 mb-2">
      <button
        v-for="loc in ['en', 'fi']"
        :key="loc"
        class="px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200"
        :class="activeLocale === loc ? 'bg-accent text-white' : ''"
        :style="activeLocale !== loc ? { color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' } : {}"
        @click="switchLocale(loc)"
      >{{ loc.toUpperCase() }}</button>
    </div>

    <!-- Messages -->
    <div v-if="error" role="alert" class="p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">{{ error }}</div>
    <div v-if="success" role="status" class="p-3 rounded-lg text-sm bg-green-500/10 text-green-400 border border-green-500/20">{{ success }}</div>

    <!-- Add new section -->
    <div class="p-4 rounded-lg" :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }">
      <h2 class="text-lg font-medium mb-3" :style="{ color: 'var(--color-text-primary)' }">{{ t('admin.addSection') }} ({{ activeLocale.toUpperCase() }})</h2>
      <form @submit.prevent="createSection" class="space-y-3">
        <div class="flex flex-col sm:flex-row gap-3">
          <input v-model="form.title" :placeholder="t('admin.title')" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <input v-model="form.slug" :placeholder="t('admin.slug')" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <select v-model="form.section_type" class="px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }">
            <option v-for="st in SECTION_TYPES" :key="st" :value="st">{{ st }}</option>
          </select>
          <select
            v-if="isCardType(form.section_type)"
            v-model="form.placement"
            class="px-3 py-2 rounded-lg text-sm outline-none"
            :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
          >
            <option v-for="opt in PLACEMENT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <textarea v-model="form.content" :placeholder="placeholderFor(form.section_type)" :required="form.section_type !== 'git_stats'" rows="4" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"></textarea>
        <div class="flex items-center gap-4">
          <button type="submit" class="bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">{{ t('admin.addSection') }}</button>
          <label v-if="form.section_type === 'text'" class="flex items-center gap-1.5 text-xs cursor-pointer" :style="{ color: 'var(--color-text-secondary)' }">
            <input type="checkbox" v-model="form.collapsible" class="accent-[#ff643e]" />
            Collapsible
          </label>
        </div>
      </form>
    </div>

    <!-- Singleton sections (quote, intro) -->
    <div
      v-for="section in singletonSections"
      :key="section.id"
      class="p-4 rounded-lg"
      :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }"
    >
      <div v-if="editingId !== section.id">
        <div class="flex justify-between items-start mb-2">
          <div>
            <h3 class="text-base font-medium" :style="{ color: 'var(--color-text-primary)' }">{{ section.title }}</h3>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">slug: {{ section.slug }}</span>
              <span class="text-xs px-1.5 py-0.5 rounded-full" :class="TYPE_COLORS[section.section_type || 'text']">{{ section.section_type || 'text' }}</span>
            </div>
          </div>
          <div class="flex gap-2 items-center">
            <button @click="startEdit(section)" class="text-xs px-3 py-1 rounded transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">{{ t('admin.edit') }}</button>
            <button @click="toggleHidden(section)" class="text-xs px-3 py-1 rounded transition-colors duration-200 hover:bg-amber-500/10" :style="{ color: 'var(--color-text-tertiary)', border: '1px solid var(--color-border)' }">{{ t('admin.hide') }}</button>
            <button @click="deleteSection(section.id)" class="text-xs px-3 py-1 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" :style="{ border: '1px solid var(--color-border)' }">{{ t('admin.delete') }}</button>
          </div>
        </div>
        <p class="text-sm truncate" :style="{ color: 'var(--color-text-secondary)' }">{{ section.content.substring(0, 200) }}</p>
      </div>
      <form v-else @submit.prevent="saveEdit(section.id)" class="space-y-3">
        <div class="flex flex-col sm:flex-row gap-3">
          <input v-model="editForm.title" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <input v-model="editForm.slug" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <select v-model="editForm.section_type" class="px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }">
            <option v-for="st in SECTION_TYPES" :key="st" :value="st">{{ st }}</option>
          </select>
        </div>
        <textarea v-model="editForm.content" :placeholder="placeholderFor(editForm.section_type)" required rows="4" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"></textarea>
        <div class="flex gap-2 items-center">
          <button type="submit" class="bg-accent text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">{{ t('admin.save') }}</button>
          <button type="button" @click="cancelEdit" class="px-4 py-1.5 rounded-lg text-sm transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">{{ t('admin.cancel') }}</button>
        </div>
      </form>
    </div>

    <!-- Pills sections group -->
    <div v-if="pillsSections.length" class="rounded-lg overflow-hidden" :style="{ border: '1px solid var(--color-border)' }">
      <div class="px-4 py-2.5 flex items-center gap-2 text-xs font-medium" :style="{ backgroundColor: 'var(--color-bg-secondary)', borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }">
        <span class="px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400">pills</span>
        Tech categories
      </div>
      <div class="divide-y" :style="{ borderColor: 'var(--color-border)' }">
        <div
          v-for="(section, idx) in pillsSections"
          :key="section.id"
          :style="{ backgroundColor: 'var(--color-bg-secondary)' }"
        >
          <!-- View mode -->
          <div v-if="editingId !== section.id" class="px-3 py-2">
            <div class="flex items-center gap-2 min-w-0">
              <div class="flex flex-col gap-px shrink-0">
                <button
                  @click="movePill(section, 'up')"
                  :disabled="idx === 0"
                  class="text-xs w-4 h-4 flex items-center justify-center rounded transition-colors hover:bg-white/10 disabled:opacity-25 disabled:cursor-not-allowed"
                  :style="{ color: 'var(--color-text-tertiary)' }"
                >▲</button>
                <button
                  @click="movePill(section, 'down')"
                  :disabled="idx === pillsSections.length - 1"
                  class="text-xs w-4 h-4 flex items-center justify-center rounded transition-colors hover:bg-white/10 disabled:opacity-25 disabled:cursor-not-allowed"
                  :style="{ color: 'var(--color-text-tertiary)' }"
                >▼</button>
              </div>
              <span class="text-sm font-medium shrink-0" :style="{ color: 'var(--color-text-primary)' }">{{ section.title }}</span>
              <span class="text-xs shrink-0 hidden sm:inline" :style="{ color: 'var(--color-text-tertiary)' }">{{ section.slug }}</span>
              <span class="text-xs truncate flex-1 min-w-0 hidden sm:block" :style="{ color: 'var(--color-text-secondary)' }">{{ section.content }}</span>
              <div class="flex gap-1 ml-auto shrink-0">
                <button @click="startEdit(section)" class="text-xs px-2 py-0.5 rounded transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">{{ t('admin.edit') }}</button>
                <button @click="toggleHidden(section)" class="text-xs px-2 py-0.5 rounded transition-colors duration-200 hover:bg-amber-500/10" :style="{ color: 'var(--color-text-tertiary)', border: '1px solid var(--color-border)' }">{{ t('admin.hide') }}</button>
                <button @click="deleteSection(section.id)" class="text-xs px-2 py-0.5 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" :style="{ border: '1px solid var(--color-border)' }">{{ t('admin.delete') }}</button>
              </div>
            </div>
            <div class="sm:hidden flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-0.5 pl-6 min-w-0">
              <span class="text-xs shrink-0" :style="{ color: 'var(--color-text-tertiary)' }">{{ section.slug }}</span>
              <span class="text-xs truncate flex-1 min-w-[8rem]" :style="{ color: 'var(--color-text-secondary)' }">{{ section.content }}</span>
            </div>
          </div>
          <!-- Edit mode -->
          <form v-else @submit.prevent="saveEdit(section.id)" class="space-y-3 p-3">
            <div class="flex flex-col sm:flex-row gap-3">
              <input v-model="editForm.title" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
              <input v-model="editForm.slug" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
            </div>
            <textarea v-model="editForm.content" :placeholder="PLACEHOLDERS.pills" required rows="3" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"></textarea>
            <div class="flex gap-2 items-center">
              <button type="submit" class="bg-accent text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">{{ t('admin.save') }}</button>
              <button type="button" @click="cancelEdit" class="px-4 py-1.5 rounded-lg text-sm transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">{{ t('admin.cancel') }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Card sections grouped by placement zone -->
    <div
      v-for="group in cardGroups"
      :key="group.value"
      class="rounded-lg overflow-hidden"
      :style="{ border: '1px solid var(--color-border)' }"
    >
      <div class="px-4 py-2.5 flex items-center gap-2 text-xs font-medium" :style="{ backgroundColor: 'var(--color-bg-secondary)', borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }">
        {{ group.label }}
      </div>
      <div class="divide-y" :style="{ borderColor: 'var(--color-border)' }">
        <div
          v-for="(section, idx) in group.sections"
          :key="section.id"
          :style="{ backgroundColor: 'var(--color-bg-secondary)' }"
        >
          <!-- View mode -->
          <div v-if="editingId !== section.id" class="px-3 py-2">
            <div class="flex items-center gap-2 min-w-0">
              <div class="flex flex-col gap-px shrink-0">
                <button
                  @click="moveCard(section, 'up')"
                  :disabled="idx === 0"
                  class="text-xs w-4 h-4 flex items-center justify-center rounded transition-colors hover:bg-white/10 disabled:opacity-25 disabled:cursor-not-allowed"
                  :style="{ color: 'var(--color-text-tertiary)' }"
                >▲</button>
                <button
                  @click="moveCard(section, 'down')"
                  :disabled="idx === group.sections.length - 1"
                  class="text-xs w-4 h-4 flex items-center justify-center rounded transition-colors hover:bg-white/10 disabled:opacity-25 disabled:cursor-not-allowed"
                  :style="{ color: 'var(--color-text-tertiary)' }"
                >▼</button>
              </div>
              <span class="text-sm font-medium shrink-0" :style="{ color: 'var(--color-text-primary)' }">{{ section.title }}</span>
              <span class="text-xs px-1.5 py-0.5 rounded-full shrink-0 hidden sm:inline-block" :class="TYPE_COLORS[section.section_type || 'text']">{{ section.section_type || 'text' }}</span>
              <span class="text-xs truncate flex-1 min-w-0 hidden sm:block" :style="{ color: 'var(--color-text-secondary)' }">{{ section.content.substring(0, 100) }}</span>
              <select
                :value="placementFromPosition(section.position)"
                @change="updatePlacement(section, $event.target.value)"
                class="text-xs px-1.5 py-0.5 rounded outline-none shrink-0 hidden sm:block"
                :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-accent, #ff643e)' }"
              >
                <option v-for="opt in PLACEMENT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <label v-if="section.section_type === 'text'" class="items-center gap-1 text-xs cursor-pointer shrink-0 hidden sm:flex" :style="{ color: 'var(--color-text-secondary)' }">
                <input type="checkbox" :checked="section.collapsible" @change="toggleCollapsible(section)" class="accent-[#ff643e]" />
                Collapsible
              </label>
              <div class="flex gap-1 ml-auto shrink-0">
                <button @click="startEdit(section)" class="text-xs px-2 py-0.5 rounded transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">{{ t('admin.edit') }}</button>
                <button @click="toggleHidden(section)" class="text-xs px-2 py-0.5 rounded transition-colors duration-200 hover:bg-amber-500/10" :style="{ color: 'var(--color-text-tertiary)', border: '1px solid var(--color-border)' }">{{ t('admin.hide') }}</button>
                <button @click="deleteSection(section.id)" class="text-xs px-2 py-0.5 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" :style="{ border: '1px solid var(--color-border)' }">{{ t('admin.delete') }}</button>
              </div>
            </div>
            <div class="sm:hidden flex flex-wrap items-center gap-x-2 gap-y-1 mt-0.5 pl-6 min-w-0">
              <span class="text-xs px-1.5 py-0.5 rounded-full shrink-0" :class="TYPE_COLORS[section.section_type || 'text']">{{ section.section_type || 'text' }}</span>
              <span class="text-xs truncate flex-1 min-w-[6rem]" :style="{ color: 'var(--color-text-secondary)' }">{{ section.content.substring(0, 100) }}</span>
              <select
                :value="placementFromPosition(section.position)"
                @change="updatePlacement(section, $event.target.value)"
                class="text-xs px-1.5 py-0.5 rounded outline-none shrink-0"
                :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-accent, #ff643e)' }"
              >
                <option v-for="opt in PLACEMENT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <label v-if="section.section_type === 'text'" class="flex items-center gap-1 text-xs cursor-pointer shrink-0" :style="{ color: 'var(--color-text-secondary)' }">
                <input type="checkbox" :checked="section.collapsible" @change="toggleCollapsible(section)" class="accent-[#ff643e]" />
                Collapsible
              </label>
            </div>
          </div>
          <!-- Edit mode -->
          <form v-else @submit.prevent="saveEdit(section.id)" class="space-y-3 p-3">
            <div class="flex flex-col sm:flex-row gap-3">
              <input v-model="editForm.title" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
              <input v-model="editForm.slug" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
              <select v-model="editForm.section_type" class="px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }">
                <option v-for="st in SECTION_TYPES" :key="st" :value="st">{{ st }}</option>
              </select>
              <select v-if="isCardType(editForm.section_type)" v-model="editForm.placement" class="px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }">
                <option v-for="opt in PLACEMENT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <textarea v-model="editForm.content" :placeholder="placeholderFor(editForm.section_type)" required rows="4" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"></textarea>
            <div class="flex gap-2 items-center">
              <button type="submit" class="bg-accent text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">{{ t('admin.save') }}</button>
              <button type="button" @click="cancelEdit" class="px-4 py-1.5 rounded-lg text-sm transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">{{ t('admin.cancel') }}</button>
              <label v-if="editForm.section_type === 'text'" class="flex items-center gap-1.5 text-xs cursor-pointer ml-2" :style="{ color: 'var(--color-text-secondary)' }">
                <input type="checkbox" v-model="editForm.collapsible" class="accent-[#ff643e]" />
                Collapsible
              </label>
            </div>
          </form>
        </div>
      </div>
    </div>

    <p v-if="!visibleSections.length" class="text-center py-8" :style="{ color: 'var(--color-text-secondary)' }">{{ t('admin.noSections') }}</p>

    <!-- Hidden sections panel -->
    <div v-if="hiddenSections.length" class="rounded-lg overflow-hidden" :style="{ border: '1px solid var(--color-border)' }">
      <button
        class="w-full flex items-center justify-between px-4 py-3 text-sm font-medium transition-colors duration-200 hover:bg-white/5"
        :style="{ backgroundColor: 'var(--color-bg-secondary)', color: 'var(--color-text-secondary)' }"
        @click="showHiddenPanel = !showHiddenPanel"
      >
        <span>{{ t('admin.hiddenSections') }} ({{ hiddenSections.length }})</span>
        <span class="text-xs" :style="{ color: 'var(--color-text-tertiary)' }">{{ showHiddenPanel ? '▲' : '▼' }}</span>
      </button>
      <div v-if="showHiddenPanel" class="divide-y" :style="{ borderColor: 'var(--color-border)' }">
        <div
          v-for="section in hiddenSections"
          :key="section.id"
          class="px-4 py-3 flex items-center justify-between gap-3"
          :style="{ backgroundColor: 'var(--color-bg-primary)' }"
        >
          <div class="min-w-0">
            <span class="text-sm font-medium mr-2" :style="{ color: 'var(--color-text-primary)' }">{{ section.title }}</span>
            <span class="text-xs px-1.5 py-0.5 rounded-full" :class="TYPE_COLORS[section.section_type || 'text']">{{ section.section_type || 'text' }}</span>
            <p class="text-xs truncate mt-0.5" :style="{ color: 'var(--color-text-tertiary)' }">{{ section.content.substring(0, 120) }}</p>
          </div>
          <div class="flex gap-2 shrink-0">
            <button @click="toggleHidden(section)" class="text-xs px-3 py-1 rounded transition-colors duration-200 hover:bg-green-500/10 text-green-400" :style="{ border: '1px solid var(--color-border)' }">{{ t('admin.restore') }}</button>
            <button @click="deleteSection(section.id)" class="text-xs px-3 py-1 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" :style="{ border: '1px solid var(--color-border)' }">{{ t('admin.delete') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
