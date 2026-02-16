<script setup>
defineProps({
  section: { type: Object, required: true }
})
</script>

<template>
  <article class="text-base leading-relaxed mb-6" :id="section.slug">
    <h2 class="text-2xl leading-loose m-0" :style="{ borderBottom: '1px solid var(--color-border)' }">{{ section.title }}</h2>
    <div class="py-1 px-4" v-html="section.content"></div>
  </article>
</template>
