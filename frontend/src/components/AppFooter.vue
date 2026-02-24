<script setup>
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useI18n } from '../composables/useI18n.js'
import { useNavLinks } from '../composables/useNavLinks.js'

const { logout } = useAuth()
const { t } = useI18n()
const router = useRouter()

defineProps({
  updateDate: { type: String, default: '' }
})

async function handleLogout() {
  await logout()
  router.push('/login')
}

const { navLinks } = useNavLinks(handleLogout)
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
        :to="link.action ? '' : link.to"
        class="!text-stone-400 hover:!text-accent transition-colors"
        @click.prevent="link.action ? link.action() : router.push(link.to)"
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
