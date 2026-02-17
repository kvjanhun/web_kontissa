import HomePage from './views/HomePage.vue'
import NotFound from './views/NotFound.vue'

export const routes = [
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
