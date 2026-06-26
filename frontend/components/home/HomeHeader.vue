<script setup>
const i18n = useI18nStore()
const { t } = i18n
const { locale } = storeToRefs(i18n)

const darkMode = useDarkModeStore()
const { isDark } = storeToRefs(darkMode)

const menuOpen = ref(false)
function closeMenu() {
  menuOpen.value = false
}

const navLinks = [
  { href: '#work', key: 'home.nav.work' },
  { href: '#stack', key: 'home.nav.stack' },
  { href: '#terminal', key: 'home.nav.terminal' },
]

const langLabel = computed(() => (locale.value === 'en' ? 'EN / FI' : 'FI / EN'))
const themeLabel = computed(() => (isDark.value ? t('theme.switchToLight') : t('theme.switchToDark')))

function toggleLang() {
  i18n.setLocale(locale.value === 'en' ? 'fi' : 'en')
}
</script>

<template>
  <header class="hdr">
    <div class="hdr__bar">
      <a href="#top" class="brand" @click="closeMenu">
        <span class="brand__name">erez<span class="brand__accent">.ac</span></span>
        <span class="brand__byline">/ {{ t('home.brand.byline') }}</span>
      </a>

      <nav class="nav" :aria-label="t('home.nav.label')">
        <a
          v-for="link in navLinks"
          :key="link.href"
          :href="link.href"
          class="nav__link nav__link--desktop"
          @click="closeMenu"
        >{{ t(link.key) }}</a>

        <span class="nav__divider" aria-hidden="true"></span>

        <button class="btn-mono" type="button" :aria-label="t('home.langToggle')" @click="toggleLang">
          {{ langLabel }}
        </button>
        <button class="btn-mono btn-mono--icon" type="button" :aria-label="themeLabel" :aria-pressed="isDark" @click="darkMode.toggleDark">
          <Icon class="btn-mono__icon" :name="isDark ? 'solar:moon-bold' : 'solar:sun-2-bold'" aria-hidden="true" />
        </button>
        <button
          class="btn-mono btn-mono--menu"
          type="button"
          :aria-label="t('nav.toggleMenu')"
          :aria-expanded="menuOpen"
          @click="menuOpen = !menuOpen"
        >
          <span class="menu-bar"></span>
          <span class="menu-bar"></span>
          <span class="menu-bar"></span>
        </button>
      </nav>
    </div>

    <div class="nav-drawer" :class="{ 'nav-drawer--open': menuOpen }" :aria-hidden="!menuOpen">
      <a
        v-for="link in navLinks"
        :key="link.href"
        :href="link.href"
        class="nav-drawer__link"
        @click="closeMenu"
      >{{ t(link.key) }}</a>
    </div>
  </header>
</template>

<style scoped>
.hdr {
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(12px);
  background: color-mix(in srgb, var(--bg) 78%, transparent);
  border-bottom: 1px solid var(--line);
}
.hdr__bar {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 28px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: baseline;
  gap: 10px;
  text-decoration: none;
  color: var(--tx);
  min-width: 0;
}
.brand__name {
  font-family: var(--font-plex-mono);
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.02em;
}
.brand__accent { color: var(--accent); }
.brand__byline {
  font-family: var(--font-plex-mono);
  font-size: 11px;
  color: var(--tx-3);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.nav {
  display: flex;
  align-items: center;
  gap: 4px;
}
.nav__link {
  font-family: var(--font-plex-mono);
  font-size: 12px;
  color: var(--tx-2);
  text-decoration: none;
  padding: 8px 12px;
  letter-spacing: 0.02em;
  transition: color 0.15s ease;
}
.nav__link:hover { color: var(--tx); }
.nav__divider {
  width: 1px;
  height: 18px;
  background: var(--line);
  margin: 0 6px;
}

.btn-mono {
  font-family: var(--font-plex-mono);
  font-size: 12px;
  color: var(--tx-2);
  background: none;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 6px 10px;
  cursor: pointer;
  letter-spacing: 0.04em;
  transition: color 0.15s ease, border-color 0.15s ease;
}
.btn-mono:hover { color: var(--tx); border-color: var(--tx-3); }
.btn-mono--icon {
  min-width: 34px;
  padding: 6px 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.btn-mono__icon { font-size: 16px; }
.btn-mono--menu {
  display: none;
  flex-direction: column;
  gap: 3px;
  padding: 9px;
}
.menu-bar {
  width: 15px;
  height: 1.5px;
  background: var(--tx);
}

/* Mobile drawer (hidden on desktop) */
.nav-drawer {
  display: none;
  flex-direction: column;
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 28px;
  overflow: hidden;
  max-height: 0;
  transition: max-height 0.26s ease;
}
.nav-drawer--open { max-height: 180px; }
.nav-drawer__link {
  font-family: var(--font-plex-mono);
  font-size: 13px;
  color: var(--tx-2);
  text-decoration: none;
  padding: 12px 2px;
  border-bottom: 1px solid var(--line-2);
}
.nav-drawer__link:last-child { border-bottom: none; }

@media (max-width: 720px) {
  .hdr__bar { padding: 0 18px; }
  .brand__byline { display: none; }
  .nav__link--desktop { display: none; }
  .nav__divider { display: none; }
  .btn-mono--menu { display: flex; }
  .nav-drawer { display: flex; }
}
</style>
