<script setup>
const { t } = useI18nStore()

const sections = ref([])
const editingId = ref(null)
const error = ref('')
const success = ref('')
const activeLocale = ref('en')

const TYPE_COLORS = {
  text: 'bg-stone-500/20 text-stone-400',
  pills: 'bg-blue-500/20 text-blue-400',
  quote: 'bg-purple-500/20 text-purple-400',
  currently: 'bg-green-500/20 text-green-400',
  intro: 'bg-amber-500/20 text-amber-400',
  project: 'bg-cyan-500/20 text-cyan-400',
}

const SECTION_TYPES = ['text', 'pills', 'quote', 'currently', 'intro', 'project']

const PLACEHOLDERS = {
  text: 'Content (HTML)',
  pills: 'Comma-separated values, e.g. Python, Flask, Vue.js',
  quote: 'A short tagline or quote',
  currently: 'One item per line, e.g.\nPlaying: Elden Ring\nReading: SICP',
  intro: 'Plain text intro paragraph',
  project: 'One project per line: Name|URL|Description\ne.g. Sanakenno|/sanakenno|Finnish word puzzle game',
}

const form = ref({ title: '', slug: '', content: '', section_type: 'text' })
const editForm = ref({ title: '', slug: '', content: '', section_type: 'text' })

onMounted(() => loadSections())

function clearMessages() {
  error.value = ''
  success.value = ''
}

function switchLocale(loc) {
  activeLocale.value = loc
  loadSections()
}

async function loadSections() {
  const res = await fetch(`/api/sections?locale=${activeLocale.value}`)
  sections.value = await res.json()
}

async function createSection() {
  clearMessages()
  const res = await fetch('/api/sections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...form.value, locale: activeLocale.value })
  })
  const data = await res.json()
  if (!res.ok) { error.value = data.error; return }
  form.value = { title: '', slug: '', content: '', section_type: 'text' }
  success.value = t('admin.created')
  await loadSections()
}

function startEdit(section) {
  editingId.value = section.id
  editForm.value = { title: section.title, slug: section.slug, content: section.content, section_type: section.section_type || 'text' }
}

function cancelEdit() { editingId.value = null }

async function saveEdit(id) {
  clearMessages()
  const res = await fetch(`/api/sections/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(editForm.value)
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

async function moveSection(index, direction) {
  const newIndex = index + direction
  if (newIndex < 0 || newIndex >= sections.value.length) return
  const order = sections.value.map(s => s.id)
  ;[order[index], order[newIndex]] = [order[newIndex], order[index]]
  const res = await fetch('/api/sections/reorder', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order, locale: activeLocale.value })
  })
  if (res.ok) await loadSections()
}

function placeholderFor(type) {
  return PLACEHOLDERS[type] || PLACEHOLDERS.text
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
        </div>
        <textarea v-model="form.content" :placeholder="placeholderFor(form.section_type)" required rows="4" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"></textarea>
        <button type="submit" class="bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">{{ t('admin.addSection') }}</button>
      </form>
    </div>

    <!-- Existing sections -->
    <div
      v-for="(section, idx) in sections"
      :key="section.id"
      class="p-4 rounded-lg"
      :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }"
    >
      <!-- View mode -->
      <div v-if="editingId !== section.id">
        <div class="flex justify-between items-start mb-2">
          <div>
            <h3 class="text-base font-medium" :style="{ color: 'var(--color-text-primary)' }">{{ section.title }}</h3>
            <span class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">slug: {{ section.slug }} | id: {{ section.id }} | pos: {{ section.position }}</span>
              <span class="text-xs px-1.5 py-0.5 rounded-full ml-2" :class="TYPE_COLORS[section.section_type || 'text']">{{ section.section_type || 'text' }}</span>
          </div>
          <div class="flex gap-2">
            <button @click="moveSection(idx, -1)" :disabled="idx === 0" class="text-xs px-2 py-1 rounded transition-colors duration-200 hover:bg-white/10 disabled:opacity-30" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }" aria-label="Move up">&uarr;</button>
            <button @click="moveSection(idx, 1)" :disabled="idx === sections.length - 1" class="text-xs px-2 py-1 rounded transition-colors duration-200 hover:bg-white/10 disabled:opacity-30" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }" aria-label="Move down">&darr;</button>
            <button @click="startEdit(section)" class="text-xs px-3 py-1 rounded transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">{{ t('admin.edit') }}</button>
            <button @click="deleteSection(section.id)" class="text-xs px-3 py-1 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" :style="{ border: '1px solid var(--color-border)' }">{{ t('admin.delete') }}</button>
          </div>
        </div>
        <p class="text-sm truncate" :style="{ color: 'var(--color-text-secondary)' }">{{ section.content.substring(0, 200) }}</p>
      </div>

      <!-- Edit mode -->
      <form v-else @submit.prevent="saveEdit(section.id)" class="space-y-3">
        <div class="flex flex-col sm:flex-row gap-3">
          <input v-model="editForm.title" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <input v-model="editForm.slug" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <select v-model="editForm.section_type" class="px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }">
            <option v-for="st in SECTION_TYPES" :key="st" :value="st">{{ st }}</option>
          </select>
        </div>
        <textarea v-model="editForm.content" :placeholder="placeholderFor(editForm.section_type)" required rows="4" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"></textarea>
        <div class="flex gap-2">
          <button type="submit" class="bg-accent text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">{{ t('admin.save') }}</button>
          <button type="button" @click="cancelEdit" class="px-4 py-1.5 rounded-lg text-sm transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">{{ t('admin.cancel') }}</button>
        </div>
      </form>
    </div>

    <p v-if="!sections.length" class="text-center py-8" :style="{ color: 'var(--color-text-secondary)' }">{{ t('admin.noSections') }}</p>
  </div>
</template>
