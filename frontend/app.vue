<script setup lang="ts">
const route = useRoute()
const isFullBleedRoute = computed(() => route.path === '/showcase' || route.path === '/login')
const showHeader = computed(() => !isFullBleedRoute.value)
const appShellClass = computed(() => (
  route.path === '/login'
    ? 'min-h-screen bg-black text-white'
    : 'min-h-screen bg-paper text-ink'
))
</script>

<template>
  <div :class="appShellClass">
    <AppHeader v-if="showHeader" />
    <main :class="isFullBleedRoute ? 'min-h-screen' : 'mx-auto max-w-6xl px-4 py-6 sm:px-6'">
      <NuxtPage />
    </main>
  </div>
</template>
