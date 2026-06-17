<script setup>
defineProps({
  label: {
    type: String,
    default: 'Tyhjennä haku',
  },
})

defineEmits(['clear'])
</script>

<template>
  <button
    type="button"
    class="dog-search-clear"
    :aria-label="label"
    :title="label"
    @click="$emit('clear')"
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 256 256"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <line x1="72" y1="72" x2="184" y2="184" />
      <line x1="184" y1="72" x2="72" y2="184" />
    </svg>
  </button>
</template>
