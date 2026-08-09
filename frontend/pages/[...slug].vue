<script setup>
definePageMeta({ titleKey: 'title.notFound' })

const { t } = useI18nStore()

// Belt-and-braces with the 404 status the Flask catch-all now returns: this shell is
// also what a crawler receives for any unknown path, so keep it out of the index.
useHead({ meta: [{ name: 'robots', content: 'noindex' }] })
</script>

<template>
  <div class="flex flex-col items-center justify-center py-20 text-center">
    <h1 class="text-7xl font-bold text-accent mb-4">404</h1>
    <p class="text-xl mb-8" :style="{ color: 'var(--color-text-secondary)' }">{{ t('notFound.heading') }}</p>
    <NuxtLink
      to="/"
      class="px-6 py-2.5 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
    >
      {{ t('notFound.backHome') }}
    </NuxtLink>
  </div>
</template>
