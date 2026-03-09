<script setup>
const props = defineProps({
  variations: { type: Array, required: true },
  activeCenter: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showTarget: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])
</script>

<template>
  <div class="grid grid-cols-7 gap-1">
    <button
      v-for="v in variations"
      :key="v.center"
      class="flex flex-col items-center py-1.5 px-0.5 rounded text-xs leading-tight"
      :style="{
        background: activeCenter === v.center ? 'var(--color-accent)' : 'var(--color-bg-secondary)',
        color: activeCenter === v.center ? 'white' : 'var(--color-text-secondary)',
        border: '1px solid ' + (activeCenter === v.center ? 'var(--color-accent)' : 'var(--color-border)'),
        cursor: activeCenter === v.center ? 'default' : disabled ? 'wait' : 'pointer',
        opacity: disabled && activeCenter !== v.center ? '0.6' : '1',
      }"
      :disabled="activeCenter === v.center || disabled"
      @click="activeCenter !== v.center && emit('select', v.center)"
    >
      <span class="font-semibold text-sm">{{ v.center.toUpperCase() }}</span>
      <span>{{ v.word_count }}w</span>
      <span>{{ v.max_score }}p</span>
      <span v-if="showTarget" class="text-xs" :style="{ color: activeCenter === v.center ? 'rgba(255,255,255,0.8)' : 'var(--color-text-tertiary)' }">70%: {{ Math.ceil(v.max_score * 0.7) }}</span>
      <span>{{ v.pangram_count }}pg</span>
    </button>
  </div>
</template>
