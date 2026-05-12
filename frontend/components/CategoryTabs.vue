<script setup lang="ts">
import type { PhotoCategory } from '~/types/api'

defineProps<{
  active?: PhotoCategory | 'all'
}>()

const tabs: Array<{ label: string, to: string, value: PhotoCategory | 'all' }> = [
  { label: 'All', to: '/gallery', value: 'all' },
  { label: '生活照', to: '/gallery/life', value: 'life' },
  { label: '摄影照', to: '/gallery/photography', value: 'photography' },
  { label: '宠物照', to: '/gallery/pet', value: 'pet' },
]
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <NuxtLink
      v-for="tab in tabs"
      :key="tab.value"
      :to="tab.to"
      class="focus-ring rounded-md border px-3 py-2 text-sm font-medium"
      :class="active === tab.value
        ? 'border-moss bg-moss text-white'
        : 'border-stone-200 bg-white text-stone-700 hover:bg-mist/60'"
    >
      {{ tab.label }}
    </NuxtLink>
  </div>
</template>
