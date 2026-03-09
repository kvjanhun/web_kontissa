<script setup>
import { useI18nStore } from '~/stores/i18n.js'
import { useAuthStore } from '~/stores/auth.js'
import AppHeader from '~/components/AppHeader.vue'
import AppFooter from '~/components/AppFooter.vue'

const authStore = useAuthStore()
const { t } = useI18nStore()
const updateDate = ref('')
const routeAnnouncement = ref('')

const router = useRouter()
router.afterEach((to) => {
  const titleKey = to.meta.titleKey
  routeAnnouncement.value = titleKey ? t(titleKey) : 'erez.ac'
})

onMounted(async () => {
  authStore.checkAuth()
  try {
    const res = await fetch('/api/meta')
    const meta = await res.json()
    updateDate.value = meta.update_date
  } catch (e) {
    console.error('Failed to load meta:', e)
  }
})
</script>

<template>
  <a href="#main-content" class="skip-link">Skip to content</a>
  <div class="flex flex-col min-h-screen">
    <AppHeader />
    <main id="main-content" class="grow p-6" :style="{
      backgroundColor: 'var(--color-bg-primary)',
      color: 'var(--color-text-primary)',
    }">
      <slot />
    </main>
    <AppFooter :update-date="updateDate" />
  </div>
  <div aria-live="polite" aria-atomic="true" class="sr-only">{{ routeAnnouncement }}</div>
</template>
