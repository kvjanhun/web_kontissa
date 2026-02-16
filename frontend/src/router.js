import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './views/HomePage.vue'
import NotFound from './views/NotFound.vue'
import { useAuth } from './composables/useAuth'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 }
  },
  routes: [
    { path: '/', component: HomePage, meta: { title: 'erez.ac' } },
    {
      path: '/about',
      component: () => import('./views/AboutPage.vue'),
      meta: { title: 'About - erez.ac' }
    },
    {
      path: '/contact',
      component: () => import('./views/ContactPage.vue'),
      meta: { title: 'Contact - erez.ac' }
    },
    {
      path: '/login',
      component: () => import('./views/LoginPage.vue'),
      meta: { title: 'Login - erez.ac' }
    },
    {
      path: '/admin',
      component: () => import('./views/AdminPage.vue'),
      meta: { title: 'Admin - erez.ac', requiresAdmin: true }
    },
    { path: '/:pathMatch(.*)*', component: NotFound, meta: { title: '404 - erez.ac' } }
  ]
})

router.beforeEach((to) => {
  if (to.meta.requiresAdmin) {
    const { isAdmin } = useAuth()
    if (!isAdmin.value) return '/login'
  }
})

router.afterEach((to) => {
  document.title = to.meta.title || 'erez.ac'
})

export default router
