<script setup>
defineProps({
  updateDate: { type: String, default: '' }
})
</script>

<template>
  <footer class="grow bg-dark px-4 py-3 h-10 border-t-3 border-light text-gray-500">
    <span v-if="updateDate">Last updated: {{ updateDate }}</span>
    <span v-else>&nbsp;</span>
  </footer>
</template>
