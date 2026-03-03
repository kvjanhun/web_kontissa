<script setup>
import { ref, onMounted, markRaw } from 'vue'
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

const tabs = [
  { key: 'sections', labelKey: 'admin.tab.sections', component: markRaw(AdminSections) },
  { key: 'analytics', labelKey: 'admin.tab.analytics', component: markRaw(AdminPageViews) },
  { key: 'recipes', labelKey: 'admin.tab.recipes', component: markRaw(AdminRecipes) },
  { key: 'health', labelKey: 'admin.tab.health', component: markRaw(AdminHealth) },
  { key: 'sanakenno', labelKey: 'admin.tab.sanakenno', components: [markRaw(AdminBeeStats), markRaw(AdminBlockedWords)] },
]

const activeTab = ref('sections')
const mountedTabs = ref(new Set(['sections']))

function selectTab(key) {
  activeTab.value = key
  mountedTabs.value.add(key)
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

    <!-- Tab bar -->
    <div class="flex flex-wrap gap-2 mb-6" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        role="tab"
        :aria-selected="activeTab === tab.key"
        :id="`tab-${tab.key}`"
        :aria-controls="`panel-${tab.key}`"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200"
        :class="activeTab === tab.key
          ? 'bg-accent text-white'
          : 'hover:bg-white/10'"
        :style="activeTab === tab.key
          ? {}
          : { color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }"
        @click="selectTab(tab.key)"
      >
        {{ t(tab.labelKey) }}
      </button>
    </div>

    <!-- Tab panels -->
    <div
      v-for="tab in tabs"
      :key="tab.key"
      v-show="activeTab === tab.key"
      role="tabpanel"
      :id="`panel-${tab.key}`"
      :aria-labelledby="`tab-${tab.key}`"
    >
      <template v-if="mountedTabs.has(tab.key)">
        <!-- Sanakenno tab renders two components stacked -->
        <template v-if="tab.components">
          <div class="space-y-6">
            <component v-for="(comp, i) in tab.components" :key="i" :is="comp" />
          </div>
        </template>
        <component v-else :is="tab.component" />
      </template>
    </div>
  </div>
</template>
