<script setup lang="ts">
import type { ShowcaseCategorySidebarProps } from '~/types/showcase'

const props = defineProps<ShowcaseCategorySidebarProps>()

const emit = defineEmits<{
  select: [category: import('~/types/api').ShowcaseCategory]
}>()
</script>

<template>
  <aside
    class="showcase-category-sidebar"
    :data-visible="props.visible ? 'true' : 'false'"
  >
    <button
      v-for="category in props.categories"
      :key="category.id"
      type="button"
      class="showcase-category-sidebar-item"
      :data-active="category.slug === props.activeCategory ? 'true' : 'false'"
      @click="emit('select', category.slug)"
    >
      {{ category.name }}
    </button>
  </aside>
</template>
