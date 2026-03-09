<script setup>
import { useDarkModeStore } from '~/stores/darkMode.js'

const darkModeStore = useDarkModeStore()

onMounted(() => {
  darkModeStore.init()
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
