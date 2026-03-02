<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from '../../composables/useI18n.js'

const { t } = useI18n()

const sections = ref([])
const editingId = ref(null)
const error = ref('')
const success = ref('')

const form = ref({ title: '', slug: '', content: '', section_type: 'text' })
const editForm = ref({ title: '', slug: '', content: '', section_type: 'text' })

onMounted(() => loadSections())

function clearMessages() {
  error.value = ''
  success.value = ''
}

async function loadSections() {
  const res = await fetch('/api/sections')
  sections.value = await res.json()
}

async function createSection() {
  clearMessages()
  const res = await fetch('/api/sections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form.value)
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
    body: JSON.stringify({ order })
  })
  if (res.ok) await loadSections()
}
</script>

<template>
  <div class="space-y-4">
    <!-- Messages -->
    <div v-if="error" role="alert" class="p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">{{ error }}</div>
    <div v-if="success" role="status" class="p-3 rounded-lg text-sm bg-green-500/10 text-green-400 border border-green-500/20">{{ success }}</div>

    <!-- Add new section -->
    <div class="p-4 rounded-lg" :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }">
      <h2 class="text-lg font-medium mb-3" :style="{ color: 'var(--color-text-primary)' }">{{ t('admin.addSection') }}</h2>
      <form @submit.prevent="createSection" class="space-y-3">
        <div class="flex gap-3">
          <input v-model="form.title" :placeholder="t('admin.title')" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <input v-model="form.slug" :placeholder="t('admin.slug')" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <select v-model="form.section_type" class="px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }">
            <option value="text">Text</option>
            <option value="pills">Pills</option>
            <option value="quote">Quote</option>
            <option value="currently">Currently</option>
          </select>
        </div>
        <textarea v-model="form.content" :placeholder="form.section_type === 'pills' ? 'Comma-separated values, e.g. Python, Flask, Vue.js' : form.section_type === 'quote' ? 'A short tagline or quote' : form.section_type === 'currently' ? 'One item per line, e.g.\nPlaying: Elden Ring\nReading: SICP' : t('admin.contentHtml')" required rows="4" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"></textarea>
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
            <span class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">slug: {{ section.slug }} | id: {{ section.id }} | pos: {{ section.position }} | type: {{ section.section_type || 'text' }}</span>
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
        <div class="flex gap-3">
          <input v-model="editForm.title" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <input v-model="editForm.slug" required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }" />
          <select v-model="editForm.section_type" class="px-3 py-2 rounded-lg text-sm outline-none" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }">
            <option value="text">Text</option>
            <option value="pills">Pills</option>
            <option value="quote">Quote</option>
            <option value="currently">Currently</option>
          </select>
        </div>
        <textarea v-model="editForm.content" :placeholder="editForm.section_type === 'pills' ? 'Comma-separated values, e.g. Python, Flask, Vue.js' : editForm.section_type === 'quote' ? 'A short tagline or quote' : editForm.section_type === 'currently' ? 'One item per line, e.g.\nPlaying: Elden Ring\nReading: SICP' : t('admin.contentHtml')" required rows="4" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"></textarea>
        <div class="flex gap-2">
          <button type="submit" class="bg-accent text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">{{ t('admin.save') }}</button>
          <button type="button" @click="cancelEdit" class="px-4 py-1.5 rounded-lg text-sm transition-colors duration-200 hover:bg-white/10" :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }">{{ t('admin.cancel') }}</button>
        </div>
      </form>
    </div>

    <p v-if="!sections.length" class="text-center py-8" :style="{ color: 'var(--color-text-secondary)' }">{{ t('admin.noSections') }}</p>
  </div>
</template>
