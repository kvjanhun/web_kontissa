<script setup>
import { ref, onMounted } from 'vue'

const navLinks = ref([])

onMounted(async () => {
  try {
    const res = await fetch('/api/sections')
    const sections = await res.json()
    navLinks.value = sections.map(s => ({ slug: s.slug, label: s.title }))
  } catch {
    navLinks.value = [
      { slug: 'who', label: 'Who' },
      { slug: 'what', label: 'What' },
      { slug: 'where', label: 'Where' }
    ]
  }
})
</script>

<template>
  <header class="flex justify-between items-baseline bg-dark px-6 h-22 border-b-3 border-light">
    <div class="flex gap-10 items-baseline font-normal text-2xl leading-6">
      <router-link to="/" class="!text-white text-4xl">erez.ac</router-link>
      <span class="font-light text-gray-400 max-sm:hidden">Konsta Janhunen</span>
    </div>
    <nav class="flex h-full items-center">
      <a v-for="link in navLinks" :key="link.slug" :href="'#' + link.slug"
         class="!text-white px-4 flex items-center justify-center h-full
                transition-colors duration-300 hover:bg-[#222] hover:!text-accent">
        {{ link.label }}
      </a>
    </nav>
  </header>
</template>
