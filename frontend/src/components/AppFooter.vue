<script setup>
import { computed } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useI18n } from '../composables/useI18n.js'

const { isAuthenticated, isAdmin, logout } = useAuth()
const { t } = useI18n()

defineProps({
  updateDate: { type: String, default: '' }
})

const navLinks = computed(() => {
  const links = [
    { to: '/about',   labelKey: 'nav.about' },
    { to: '/contact', labelKey: 'nav.contact' },
    { to: '/sanakenno', labelKey: 'nav.sanakenno' },
  ]
  if (isAuthenticated.value) {
    links.push({ to: '/recipes', labelKey: 'nav.recipes' })
  }
  if (isAdmin.value) {
    links.push({ to: '/admin', labelKey: 'nav.admin' })
  }
  if (isAuthenticated.value) {
    links.push({ to: '/login', labelKey: 'nav.logout', action: () => logout() })
  } else {
    links.push({ to: '/login', labelKey: 'nav.login' })
  }
  return links
})
</script>

<template>
  <footer
    class="px-6 py-5"
    :style="{
      backgroundColor: 'var(--color-header-bg)',
      borderTop: '2px solid var(--color-header-border)',
    }"
  >
    <!-- Row 1: nav links -->
    <nav class="flex flex-wrap gap-x-5 gap-y-2 text-sm mb-3" aria-label="Footer">
      <router-link
        v-for="link in navLinks"
        :key="link.to"
        :to="link.to"
        class="!text-stone-400 hover:!text-accent transition-colors"
        @click="link.action && link.action()"
      >
        {{ t(link.labelKey) }}
      </router-link>
    </nav>

    <!-- Row 2: last updated -->
    <div class="text-sm" style="color: var(--color-text-tertiary);">
      <span v-if="updateDate">{{ t('footer.lastUpdated', { date: updateDate }) }}</span>
    </div>
  </footer>
</template>
