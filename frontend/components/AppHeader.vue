<script setup>
const { logout } = useAuthStore()
const { t } = useI18nStore()
const router = useRouter()
const menuOpen = ref(false)

async function handleLogout() {
  await logout()
  router.push('/login')
}

const { navLinks } = useNavLinks(handleLogout)

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
    class="sticky top-0 z-50"
    :style="{
      backgroundColor: 'var(--color-bg-primary)',
      paddingTop: 'env(safe-area-inset-top)',
    }"
  >
    <div class="px-6 h-16 flex justify-between items-center">
    <div class="flex gap-6 items-center">
      <NuxtLink
        to="/"
        class="text-2xl font-normal tracking-tight"
        :style="{
          color: 'var(--color-text-primary)',
          textDecoration: 'underline',
          textDecorationColor: 'var(--color-accent, #ff643e)',
          textDecorationThickness: '2px',
          textUnderlineOffset: '4px',
        }"
      >erez.ac</NuxtLink>
    </div>

    <div class="flex items-center gap-2">
      <LangToggle />
      <ThemeToggle />

      <!-- Hamburger — always visible -->
      <button
        class="p-2 transition-colors duration-200"
        :style="{ color: menuOpen ? 'var(--color-accent, #ff643e)' : 'var(--color-text-secondary)' }"
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
    </div>

    <!-- Dropdown nav -->
    <nav
      v-if="menuOpen"
      class="absolute top-full right-0 flex flex-col py-2 rounded-br-lg min-w-33 text-right"
      :style="{
        backgroundColor: 'var(--color-bg-primary)',
        border: '2px solid var(--color-accent, #ff643e)',
      }"
      aria-label="Main"
      @keydown="handleDropdownKeydown"
    >
      <NuxtLink
        v-for="link in navLinks"
        :key="link.to"
        :to="link.action ? '' : link.to"
        class="px-6 py-3 text-sm transition-colors duration-200 cursor-pointer text-[var(--color-text-secondary)] hover:text-[var(--color-accent,#ff643e)]"
        @click.prevent="closeMenu(); link.action ? link.action() : router.push(link.to)"
      >
        {{ t(link.labelKey) }}
      </NuxtLink>
    </nav>
  </header>
</template>
