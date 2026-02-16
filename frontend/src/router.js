import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './views/HomePage.vue'
import NotFound from './views/NotFound.vue'

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
    { path: '/:pathMatch(.*)*', component: NotFound, meta: { title: '404 - erez.ac' } }
  ]
})

router.afterEach((to) => {
  document.title = to.meta.title || 'erez.ac'
})

export default router
