import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './views/HomePage.vue'
import NotFound from './views/NotFound.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomePage },
    { path: '/:pathMatch(.*)*', component: NotFound }
  ]
})

export default router
