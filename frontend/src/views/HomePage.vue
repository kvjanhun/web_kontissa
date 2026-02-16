<script setup>
import TerminalWindow from '../components/TerminalWindow.vue'
import SectionBlock from '../components/SectionBlock.vue'

defineProps({
  sections: { type: Array, default: () => [] },
  loading: { type: Boolean, default: true },
  error: { type: Object, default: null }
})
</script>

<template>
  <div>
    <TerminalWindow />
    <div v-if="loading" class="space-y-6">
      <div v-for="n in 3" :key="n" class="animate-pulse">
        <div class="h-8 bg-gray-200 rounded w-1/4 mb-3"></div>
        <div class="h-4 bg-gray-100 rounded w-full mb-2"></div>
        <div class="h-4 bg-gray-100 rounded w-3/4"></div>
      </div>
    </div>
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
      <p class="text-red-600 mb-2">Failed to load content.</p>
      <p class="text-gray-500 text-sm">Please try refreshing the page.</p>
    </div>
    <template v-else>
      <SectionBlock v-for="section in sections" :key="section.id" :section="section" />
    </template>
  </div>
</template>
