<script setup>
import { ref, onMounted, shallowRef, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { useHead } from '@unhead/vue'
import { useAuth } from '../composables/useAuth'
import { useI18n } from '../composables/useI18n.js'

import AdminSections from '../components/admin/AdminSections.vue'
import AdminPageViews from '../components/admin/AdminPageViews.vue'
import AdminRecipes from '../components/admin/AdminRecipes.vue'
import AdminHealth from '../components/admin/AdminHealth.vue'
import AdminBeeStats from '../components/admin/AdminBeeStats.vue'
import AdminBlockedWords from '../components/admin/AdminBlockedWords.vue'

useHead({
  meta: [
    { name: 'robots', content: 'noindex' }
  ]
})

const router = useRouter()
const { isAdmin } = useAuth()
const { t } = useI18n()

const categories = [
  {
    name: 'Site Admin',
    key: 'site',
    panels: [
      { name: 'Sections', key: 'sections', component: markRaw(AdminSections) },
      { name: 'Page Views', key: 'pageviews', component: markRaw(AdminPageViews) },
      { name: 'Recipes', key: 'recipes', component: markRaw(AdminRecipes) },
      { name: 'System Health', key: 'health', component: markRaw(AdminHealth) },
    ]
  },
  {
    name: 'Sanakenno Admin',
    key: 'sanakenno',
    panels: [
      { name: 'Stats', key: 'stats', component: markRaw(AdminBeeStats) },
      { name: 'Blocked Words', key: 'blocked', component: markRaw(AdminBlockedWords) },
    ]
  },
]

const expandedCategories = ref({})
const expandedPanels = ref({})

function toggleCategory(key) {
  expandedCategories.value[key] = !expandedCategories.value[key]
}

function togglePanel(key) {
  expandedPanels.value[key] = !expandedPanels.value[key]
}

onMounted(() => {
  if (!isAdmin.value) {
    router.push('/login')
    return
  }
})
</script>

<template>
  <div class="max-w-3xl mx-auto mt-8">
    <h1 class="text-3xl font-light mb-8" :style="{ color: 'var(--color-text-primary)' }">{{ t('admin.heading') }}</h1>

    <div v-for="category in categories" :key="category.key" class="mb-6">
      <!-- Category header -->
      <button
        @click="toggleCategory(category.key)"
        class="w-full flex justify-between items-center p-3 rounded-lg text-left text-lg font-medium"
        :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)', cursor: 'pointer' }"
        :aria-expanded="!!expandedCategories[category.key]"
      >
        <span>{{ category.name }}</span>
        <span :style="{ color: 'var(--color-text-tertiary)' }">{{ expandedCategories[category.key] ? '\u25B2' : '\u25BC' }}</span>
      </button>

      <!-- Category content -->
      <div v-if="expandedCategories[category.key]" class="mt-2 ml-4 space-y-3">
        <div v-for="panel in category.panels" :key="panel.key">
          <!-- Panel header -->
          <button
            @click="togglePanel(panel.key)"
            class="w-full flex justify-between items-center p-3 rounded-lg text-left text-base font-medium"
            :style="{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)', cursor: 'pointer' }"
            :aria-expanded="!!expandedPanels[panel.key]"
          >
            <span>{{ panel.name }}</span>
            <span :style="{ color: 'var(--color-text-tertiary)' }">{{ expandedPanels[panel.key] ? '\u25B2' : '\u25BC' }}</span>
          </button>

          <!-- Panel content (lazy rendered) -->
          <div v-if="expandedPanels[panel.key]" class="mt-2 p-4 rounded-lg" :style="{ border: '1px solid var(--color-border)' }">
            <component :is="panel.component" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
