<script setup>
import { computed } from 'vue'
import { useHead } from '@unhead/vue'
import { useI18n } from '../composables/useI18n.js'
import TerminalWindow from '../components/TerminalWindow.vue'

const { t } = useI18n()

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
      <router-link
        to="/about"
        class="px-6 py-2.5 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
      >
        {{ t('home.aboutMe') }}
      </router-link>
      <router-link
        to="/contact"
        class="px-6 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200"
        :style="{ border: '1px solid var(--color-border)', color: 'var(--color-text-primary)' }"
      >
        {{ t('home.getInTouch') }}
      </router-link>
    </div>
  </div>
</template>
