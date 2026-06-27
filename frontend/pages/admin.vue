<script setup>
definePageMeta({
  layout: 'standalone',
  titleKey: 'title.admin',
  requiresAdmin: true,
})

useHead({
  meta: [{ name: 'robots', content: 'noindex' }],
  bodyAttrs: { class: 'admin-body' },
})

const authStore = useAuthStore()
const { user } = storeToRefs(authStore)

const nav = [
  { key: 'dashboard', label: 'Dashboard', icon: 'flat-color-icons:home', component: resolveComponent('AdminDashboard') },
  { key: 'home', label: 'Home content', icon: 'flat-color-icons:document', component: resolveComponent('AdminHomeContent') },
  { key: 'projects', label: 'Projects', icon: 'flat-color-icons:gallery', component: resolveComponent('AdminProjects') },
  { key: 'recipes', label: 'Recipes', icon: 'flat-color-icons:news', component: resolveComponent('AdminRecipes') },
  { key: 'analytics', label: 'Analytics', icon: 'flat-color-icons:combo-chart', component: resolveComponent('AdminPageViews') },
  { key: 'health', label: 'Server health', icon: 'flat-color-icons:services', component: resolveComponent('AdminHealth') },
]

const activeKey = ref('dashboard')
const activeNav = computed(() => nav.find(n => n.key === activeKey.value) || nav[0])

function select(key) {
  activeKey.value = key
}

// Dashboard cards deep-link into a section (e.g. "Manage projects")
provide('adminNavigate', select)

async function doLogout() {
  await authStore.logout()
  navigateTo('/login')
}

const userInitials = computed(() => {
  const name = user.value?.username || 'KJ'
  return name.slice(0, 2).toUpperCase()
})
</script>

<template>
  <div class="admin-shell">
    <!-- SIDEBAR -->
    <aside class="as-sidebar">
      <div class="as-brand">
        <span class="as-brand__name">erez<span class="as-brand__dot">.ac</span></span>
        <span class="as-brand__tag">admin</span>
      </div>

      <nav class="as-nav">
        <span class="as-nav__label">Manage</span>
        <button
          v-for="n in nav"
          :key="n.key"
          class="as-nav__item"
          :class="{ 'as-nav__item--active': activeKey === n.key }"
          @click="select(n.key)"
        >
          <span class="as-nav__bar" />
          <Icon :name="n.icon" class="as-nav__icon" />
          <span class="as-nav__text">{{ n.label }}</span>
        </button>
      </nav>

      <div class="as-user">
        <span class="as-user__avatar">{{ userInitials }}</span>
        <div class="as-user__meta">
          <div class="as-user__name">{{ user?.username || 'Admin' }}</div>
          <div class="as-user__role">{{ user?.role || 'admin' }}</div>
        </div>
        <button class="as-user__logout" title="Sign out" @click="doLogout">
          <Icon name="flat-color-icons:export" />
        </button>
      </div>
    </aside>

    <!-- MAIN -->
    <div class="as-main">
      <header class="as-topbar">
        <div class="as-crumb">
          <span>admin</span><span class="as-crumb__sep">/</span>
          <span class="as-crumb__current">{{ activeNav?.label }}</span>
        </div>
        <a href="/" class="as-viewsite"><Icon name="flat-color-icons:globe" /> View site</a>
      </header>

      <main class="as-content">
        <component :is="activeNav.component" :key="activeKey" />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-shell {
  /* Warm-stone, light-only palette scoped to the admin (matches the mockup). */
  --as-bg: #f4f4f1;
  --as-panel: #ffffff;
  --as-sidebar: #fbfbf9;
  --as-line: #e7e7e1;
  --as-line-2: #ededE7;
  --as-tx: #15171c;
  --as-tx-2: #6b7079;
  --as-tx-3: #a4a8b0;
  --as-accent: #ff6a3d;

  display: grid;
  grid-template-columns: 236px 1fr;
  min-height: 100vh;
  background: var(--as-bg);
  color: var(--as-tx);
  font-family: var(--font-sans), system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* Sidebar */
.as-sidebar {
  background: var(--as-sidebar);
  border-right: 1px solid var(--as-line);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
}
.as-brand {
  padding: 18px 20px 16px;
  border-bottom: 1px solid var(--as-line-2);
  display: flex;
  align-items: baseline;
  gap: 9px;
}
.as-brand__name { font-family: var(--font-mono, monospace); font-weight: 600; font-size: 15px; }
.as-brand__dot { color: var(--as-accent); }
.as-brand__tag {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  color: var(--as-tx-3);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.as-nav { flex: 1; padding: 14px 12px; overflow-y: auto; }
.as-nav__label {
  display: block;
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  color: var(--as-tx-3);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 6px 10px 8px;
}
.as-nav__item {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 10px;
  margin-bottom: 2px;
  border: none;
  background: transparent;
  color: var(--as-tx-2);
  border-radius: 8px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
}
.as-nav__item:hover { background: rgba(0, 0, 0, 0.03); }
.as-nav__item--active { background: rgba(255, 106, 61, 0.1); color: var(--as-tx); font-weight: 600; }
.as-nav__bar {
  position: absolute;
  left: -12px;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: transparent;
}
.as-nav__item--active .as-nav__bar { background: var(--as-accent); }
.as-nav__icon { font-size: 19px; }
.as-nav__text { flex: 1; }

.as-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-top: 1px solid var(--as-line-2);
}
.as-user__avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--as-tx);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono, monospace);
  font-weight: 600;
  font-size: 13px;
}
.as-user__meta { flex: 1; min-width: 0; }
.as-user__name { font-size: 13px; font-weight: 600; line-height: 1.2; }
.as-user__role { font-size: 11px; color: var(--as-tx-3); font-family: var(--font-mono, monospace); }
.as-user__logout {
  border: none;
  background: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  font-size: 18px;
}
.as-user__logout:hover { background: rgba(0, 0, 0, 0.05); }

/* Main */
.as-main { display: flex; flex-direction: column; min-width: 0; }
.as-topbar {
  height: 60px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--as-line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 26px;
  position: sticky;
  top: 0;
  z-index: 30;
}
.as-crumb {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13px;
  color: var(--as-tx-3);
  font-family: var(--font-mono, monospace);
}
.as-crumb__sep { color: #cfcfc8; }
.as-crumb__current { color: var(--as-tx); font-weight: 500; }
.as-viewsite {
  height: 36px;
  padding: 0 13px;
  border: 1px solid var(--as-line);
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 500;
  color: #3c4047;
  text-decoration: none;
}
.as-viewsite:hover { background: #f3f3ee; }
.as-content { flex: 1; padding: 26px; overflow-y: auto; }

@media (max-width: 720px) {
  .admin-shell { grid-template-columns: 1fr; }
  .as-sidebar {
    position: static;
    height: auto;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
  }
  .as-nav { display: flex; flex-wrap: wrap; gap: 4px; width: 100%; }
  .as-nav__label { display: none; }
  .as-nav__item { width: auto; }
  .as-user { width: 100%; }
  .as-content { padding: 16px; }
}
</style>
