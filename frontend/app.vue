<script setup lang="ts">
const route = useRoute()
const isShowcase = computed(() => route.path === '/showcase')
const showHeader = computed(() => route.path !== '/login' && !isShowcase.value)
</script>

<template>
  <div class="min-h-screen bg-paper text-ink">
    <AppHeader v-if="showHeader" />
    <main :class="isShowcase ? 'min-h-screen' : 'mx-auto max-w-6xl px-4 py-6 sm:px-6'">
      <NuxtPage />
    </main>
  </div>
</template>
