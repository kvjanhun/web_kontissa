<script setup>
import DogBrowser from '~/features/dog/DogBrowser.vue'

definePageMeta({
  layout: 'standalone',
})

useHead({
  title: 'Näyttelytulokset | erez.ac',
  meta: [
    { name: 'description', content: 'Selaa koiranäyttelyiden tuloksia. Hae rodun tai näyttelyn mukaan.' },
    { property: 'og:title', content: 'Näyttelytulokset | erez.ac' },
    { property: 'og:description', content: 'Selaa koiranäyttelyiden tuloksia.' },
    { property: 'og:url', content: 'https://erez.ac/dog' },
  ],
})
</script>

<template>
  <DogBrowser />
</template>
