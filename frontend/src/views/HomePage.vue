<script setup>
import { useHead } from '@unhead/vue'
import TerminalWindow from '../components/TerminalWindow.vue'

useHead({
  title: 'erez.ac — Konsta Janhunen',
  meta: [
    { name: 'description', content: 'Konsta Janhunen — Developer & tinkerer. Integration developer, CS student, and technology enthusiast.' }
  ]
})
</script>

<template>
  <div class="flex flex-col items-center py-12">
    <h1 class="text-5xl font-light mb-2" :style="{ color: 'var(--color-text-primary)' }">Konsta Janhunen</h1>
    <p class="text-lg mb-10" :style="{ color: 'var(--color-text-secondary)' }">Developer &amp; tinkerer</p>

    <div class="w-full max-w-2xl mb-10">
      <TerminalWindow />
    </div>

    <div class="flex gap-4">
      <router-link
        to="/about"
        class="px-6 py-2.5 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
      >
        About me
      </router-link>
      <router-link
        to="/contact"
        class="px-6 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200"
        :style="{ border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
      >
        Get in touch
      </router-link>
    </div>
  </div>
</template>
