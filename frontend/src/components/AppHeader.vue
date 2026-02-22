<script setup>
import { ref, computed } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useI18n } from '../composables/useI18n.js'
import ThemeToggle from './ThemeToggle.vue'
import LangToggle from './LangToggle.vue'

const { isAuthenticated, isAdmin, logout } = useAuth()
const { t } = useI18n()
const menuOpen = ref(false)

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
    links.push({ to: '/login', labelKey: 'nav.logout', action: handleLogout })
  } else {
    links.push({ to: '/login', labelKey: 'nav.login' })
  }
  return links
})

async function handleLogout() {
  await logout()
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function closeMenu() {
  menuOpen.value = false
}

function handleDropdownKeydown(e) {
  if (e.key === 'Escape') {
    closeMenu()
  }
}
</script>

<template>
  <header
    class="sticky top-0 z-50 px-6 h-16 flex justify-between items-center"
    :style="{
      backgroundColor: 'var(--color-header-bg)',
      borderBottom: '2px solid var(--color-header-border)'
    }"
  >
    <div class="flex gap-6 items-center">
      <router-link to="/" class="!text-white text-2xl font-normal tracking-tight">erez.ac</router-link>
      <span class="font-light text-stone-400 text-sm max-sm:hidden">Konsta Janhunen</span>
    </div>

    <div class="flex items-center gap-2">
      <LangToggle />
      <ThemeToggle class="text-stone-400" />

      <!-- Hamburger — always visible -->
      <button
        class="p-2 text-stone-400 hover:text-white"
        @click="toggleMenu"
        :aria-label="t('nav.toggleMenu')"
        :aria-expanded="menuOpen"
      >
        <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" class="size-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path v-if="!menuOpen" stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16"/>
          <path v-else stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <!-- Dropdown nav — universal (desktop + mobile) -->
    <nav
      v-if="menuOpen"
      class="absolute top-16 right-0 flex flex-col py-2 shadow-lg rounded-bl-lg min-w-44"
      :style="{
        backgroundColor: 'var(--color-header-bg)',
        borderBottom: '2px solid var(--color-header-border)',
        borderLeft: '2px solid var(--color-header-border)'
      }"
      aria-label="Main"
      @keydown="handleDropdownKeydown"
    >
      <router-link
        v-for="link in navLinks"
        :key="link.to"
        :to="link.to"
        class="!text-stone-400 px-6 py-3 text-sm transition-colors duration-200 hover:!text-accent hover:bg-white/10"
        @click="closeMenu(); link.action && link.action()"
      >
        {{ t(link.labelKey) }}
      </router-link>
    </nav>
  </header>
</template>
