import HomePage from './views/HomePage.vue'
import NotFound from './views/NotFound.vue'

export const routes = [
  { path: '/', component: HomePage, meta: { titleKey: 'title.home' } },
  {
    path: '/about',
    component: () => import('./views/AboutPage.vue'),
    meta: { titleKey: 'title.about' }
  },
  {
    path: '/contact',
    component: () => import('./views/ContactPage.vue'),
    meta: { titleKey: 'title.contact' }
  },
  {
    path: '/login',
    component: () => import('./views/LoginPage.vue'),
    meta: { titleKey: 'title.login' }
  },
  {
    path: '/admin',
    component: () => import('./views/AdminPage.vue'),
    meta: { titleKey: 'title.admin', requiresAdmin: true }
  },
  {
    path: '/recipes',
    component: () => import('./views/RecipeListPage.vue'),
    meta: { titleKey: 'title.recipes', requiresAuth: true }
  },
  {
    path: '/recipes/new',
    component: () => import('./views/RecipeFormPage.vue'),
    meta: { titleKey: 'title.newRecipe', requiresAuth: true }
  },
  {
    path: '/recipes/:slug',
    component: () => import('./views/RecipeDetailPage.vue'),
    meta: { titleKey: 'title.recipe', requiresAuth: true }
  },
  {
    path: '/recipes/:slug/edit',
    component: () => import('./views/RecipeFormPage.vue'),
    meta: { titleKey: 'title.editRecipe', requiresAuth: true }
  },
  { path: '/:pathMatch(.*)*', component: NotFound, meta: { titleKey: 'title.notFound' } }
]
