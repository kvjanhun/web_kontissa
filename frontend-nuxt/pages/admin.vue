<script setup>
import { useAuthStore } from '~/stores/auth.js'
import { useI18nStore } from '~/stores/i18n.js'

definePageMeta({
  titleKey: 'title.admin',
  requiresAdmin: true,
})

useHead({
  meta: [
    { name: 'robots', content: 'noindex' }
  ]
})

const router = useRouter()
const { isAdmin } = storeToRefs(useAuthStore())
const { t } = useI18nStore()

const tabs = [
  { key: 'sections', labelKey: 'admin.tab.sections', component: resolveComponent('AdminSections') },
  { key: 'analytics', labelKey: 'admin.tab.analytics', component: resolveComponent('AdminPageViews') },
  { key: 'recipes', labelKey: 'admin.tab.recipes', component: resolveComponent('AdminRecipes') },
  { key: 'health', labelKey: 'admin.tab.health', component: resolveComponent('AdminHealth') },
  { key: 'sanakenno', labelKey: 'admin.tab.sanakenno', components: [resolveComponent('AdminKennoStats'), resolveComponent('AdminBlockedWords')] },
  { key: 'kennotyokalu', labelKey: 'admin.tab.kennotyokalu', component: resolveComponent('AdminKennoPuzzleTool') },
]

const activeTab = ref('sections')
const mountedTabs = ref(new Set(['sections']))

function selectTab(key) {
  activeTab.value = key
  mountedTabs.value.add(key)
}
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
