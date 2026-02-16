<template>
  <div class="flex flex-col items-center justify-center py-20 text-center">
    <h1 class="text-7xl font-bold text-accent mb-4">404</h1>
    <p class="text-xl mb-8" :style="{ color: 'var(--color-text-secondary)' }">Page not found</p>
    <router-link
      to="/"
      class="px-6 py-2.5 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
    >
      Back to home
    </router-link>
  </div>
</template>
