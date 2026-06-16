<script setup>
defineProps({
  mode: {
    type: String,
    required: true,
  },
  message: {
    type: String,
    default: '',
  },
  rows: {
    type: Number,
    default: 6,
  },
  tall: {
    type: Boolean,
    default: false,
  },
  retryLabel: {
    type: String,
    default: '',
  },
})

defineEmits(['retry'])
</script>

<template>
  <div v-if="mode === 'loading'" class="dog-skeleton-list">
    <div
      v-for="i in rows"
      :key="i"
      :class="['dog-skeleton-row', tall && 'dog-skeleton-tall']"
    />
  </div>

  <div v-else-if="mode === 'error'" class="dog-error">
    <p>{{ message }}</p>
    <button v-if="retryLabel" class="dog-btn" @click="$emit('retry')">{{ retryLabel }}</button>
  </div>

  <div v-else class="dog-empty">
    <p>{{ message }}</p>
  </div>
</template>
