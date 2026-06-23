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
  // /dog gets its own rosette favicon, overriding the site-wide favicon.ico.
  link: [
    { rel: 'icon', type: 'image/svg+xml', href: '/favicon-dog.svg' },
  ],
})
</script>

<template>
  <DogBrowser />
</template>
