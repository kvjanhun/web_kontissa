<script setup>
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
