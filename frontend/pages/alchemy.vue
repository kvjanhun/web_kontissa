<script setup>
import AlchemyBrowser from '~/features/alchemy/AlchemyBrowser.vue'

definePageMeta({
  layout: 'standalone',
})

// Unlisted while the page is being built out: nothing links here, it is absent
// from the sitemap, and this keeps it out of an index if anyone finds the URL.
useHead({
  title: 'Alchemy | erez.ac',
  meta: [
    { name: 'robots', content: 'noindex' },
    { name: 'description', content: 'Kingdom Come: Deliverance II alchemy recipes and an ingredient matcher.' },
  ],
})
</script>

<template>
  <AlchemyBrowser />
</template>
