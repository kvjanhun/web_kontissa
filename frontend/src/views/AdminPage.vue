<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHead } from '@unhead/vue'
import { useAuth } from '../composables/useAuth'
import { useI18n } from '../composables/useI18n.js'

useHead({
  meta: [
    { name: 'robots', content: 'noindex' }
  ]
})

const router = useRouter()
const { isAdmin } = useAuth()
const { t } = useI18n()

const sections = ref([])
const editingId = ref(null)
const error = ref('')
const success = ref('')

const form = ref({ title: '', slug: '', content: '' })
const editForm = ref({ title: '', slug: '', content: '' })

onMounted(() => {
  if (!isAdmin.value) {
    router.push('/login')
    return
  }
  loadSections()
})

async function loadSections() {
  const res = await fetch('/api/sections')
  sections.value = await res.json()
}

function clearMessages() {
  error.value = ''
  success.value = ''
}

async function createSection() {
  clearMessages()
  const res = await fetch('/api/sections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form.value)
  })
  const data = await res.json()
  if (!res.ok) {
    error.value = data.error
    return
  }
  form.value = { title: '', slug: '', content: '' }
  success.value = t('admin.created')
  await loadSections()
}

function startEdit(section) {
  editingId.value = section.id
  editForm.value = { title: section.title, slug: section.slug, content: section.content }
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit(id) {
  clearMessages()
  const res = await fetch(`/api/sections/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(editForm.value)
  })
  const data = await res.json()
  if (!res.ok) {
    error.value = data.error
    return
  }
  editingId.value = null
  success.value = t('admin.updated')
  await loadSections()
}

async function deleteSection(id) {
  if (!confirm(t('admin.confirmDelete'))) return
  clearMessages()
  const res = await fetch(`/api/sections/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const data = await res.json()
    error.value = data.error
    return
  }
  success.value = t('admin.deleted')
  await loadSections()
}
</script>

<template>
  <div class="max-w-3xl mx-auto mt-8">
    <h1 class="text-3xl font-light mb-8" :style="{ color: 'var(--color-text-primary)' }">{{ t('admin.heading') }}</h1>

    <!-- Messages -->
    <div v-if="error" role="alert" class="mb-4 p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">
      {{ error }}
    </div>
    <div v-if="success" role="status" class="mb-4 p-3 rounded-lg text-sm bg-green-500/10 text-green-400 border border-green-500/20">
      {{ success }}
    </div>

    <!-- Add new section -->
    <div class="mb-8 p-4 rounded-lg" :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }">
      <h2 class="text-lg font-medium mb-3" :style="{ color: 'var(--color-text-primary)' }">{{ t('admin.addSection') }}</h2>
      <form @submit.prevent="createSection" class="space-y-3">
        <div class="flex gap-3">
          <input
            v-model="form.title"
            :placeholder="t('admin.title')"
            required
            class="flex-1 px-3 py-2 rounded-lg text-sm outline-none"
            :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
          />
          <input
            v-model="form.slug"
            :placeholder="t('admin.slug')"
            required
            class="flex-1 px-3 py-2 rounded-lg text-sm outline-none"
            :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
          />
        </div>
        <textarea
          v-model="form.content"
          :placeholder="t('admin.contentHtml')"
          required
          rows="4"
          class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y"
          :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
        ></textarea>
        <button
          type="submit"
          class="bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
        >
          {{ t('admin.addSection') }}
        </button>
      </form>
    </div>

    <!-- Existing sections -->
    <div class="space-y-4">
      <div
        v-for="section in sections"
        :key="section.id"
        class="p-4 rounded-lg"
        :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }"
      >
        <!-- View mode -->
        <div v-if="editingId !== section.id">
          <div class="flex justify-between items-start mb-2">
            <div>
              <h3 class="text-base font-medium" :style="{ color: 'var(--color-text-primary)' }">{{ section.title }}</h3>
              <span class="text-xs" :style="{ color: 'var(--color-text-secondary)' }">slug: {{ section.slug }} | id: {{ section.id }}</span>
            </div>
            <div class="flex gap-2">
              <button
                @click="startEdit(section)"
                class="text-xs px-3 py-1 rounded transition-colors duration-200 hover:bg-white/10"
                :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }"
              >
                {{ t('admin.edit') }}
              </button>
              <button
                @click="deleteSection(section.id)"
                class="text-xs px-3 py-1 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10"
                :style="{ border: '1px solid var(--color-border)' }"
              >
                {{ t('admin.delete') }}
              </button>
            </div>
          </div>
          <p class="text-sm truncate" :style="{ color: 'var(--color-text-secondary)' }">{{ section.content.substring(0, 200) }}</p>
        </div>

        <!-- Edit mode -->
        <form v-else @submit.prevent="saveEdit(section.id)" class="space-y-3">
          <div class="flex gap-3">
            <input
              v-model="editForm.title"
              required
              class="flex-1 px-3 py-2 rounded-lg text-sm outline-none"
              :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
            />
            <input
              v-model="editForm.slug"
              required
              class="flex-1 px-3 py-2 rounded-lg text-sm outline-none"
              :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
            />
          </div>
          <textarea
            v-model="editForm.content"
            required
            rows="4"
            class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y"
            :style="{ backgroundColor: 'var(--color-bg-primary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
          ></textarea>
          <div class="flex gap-2">
            <button
              type="submit"
              class="bg-accent text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
            >
              {{ t('admin.save') }}
            </button>
            <button
              type="button"
              @click="cancelEdit"
              class="px-4 py-1.5 rounded-lg text-sm transition-colors duration-200 hover:bg-white/10"
              :style="{ color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }"
            >
              {{ t('admin.cancel') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <p v-if="!sections.length" class="text-center py-8" :style="{ color: 'var(--color-text-secondary)' }">
      {{ t('admin.noSections') }}
    </p>
  </div>
</template>
