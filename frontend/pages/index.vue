<script setup>
definePageMeta({ titleKey: 'title.home' })

const { t } = useI18nStore()

useHead({
  title: computed(() => t('home.metaTitle')),
  meta: [
    { name: 'description', content: computed(() => t('home.metaDescription')) }
  ]
})
</script>

<template>
  <div class="flex flex-col items-center py-12">
    <h1 class="text-5xl font-light mb-2" :style="{ color: 'var(--color-text-primary)' }">{{ t('home.heading') }}</h1>
    <p class="text-lg mb-10" :style="{ color: 'var(--color-text-secondary)' }">{{ t('home.subtitle') }}</p>

    <div class="w-full max-w-2xl mb-10">
      <TerminalWindow />
    </div>

    <div class="flex gap-4">
      <NuxtLink
        to="/about"
        class="px-6 py-2.5 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
      >
        {{ t('home.aboutMe') }}
      </NuxtLink>
      <NuxtLink
        to="/contact"
        class="px-6 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200"
        :style="{ border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
      >
        {{ t('home.getInTouch') }}
      </NuxtLink>
    </div>
  </div>
</template>
