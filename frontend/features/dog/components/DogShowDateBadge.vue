<script setup>
import { showDateBadgeParts } from '../dogResults.js'

const props = defineProps({
  date: {
    type: String,
    default: '',
  },
  month: {
    type: String,
    default: '',
  },
})

const parts = computed(() => showDateBadgeParts({ date: props.date, month: props.month }))
</script>

<template>
  <span class="dog-show-date">
    <span :class="['dog-show-date-day', parts.range && 'dog-show-date-day-range']">{{ parts.day }}</span>
    <span class="dog-show-date-month">{{ parts.month }}</span>
  </span>
</template>
