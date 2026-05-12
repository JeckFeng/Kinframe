<script setup lang="ts">
import type { Photo } from '~/types/api'

defineProps<{
  photos: Photo[]
  thumbnails: Record<string, string>
}>()

const { formatDate } = useFormat()
const { displayCategory } = usePhotoCategories()

function statusLabel(status: string) {
  if (status === 'failed') {
    return 'Processing failed'
  }
  if (status === 'ready') {
    return 'No thumbnail'
  }
  return 'Processing'
}
</script>

<template>
  <div v-if="photos.length" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
    <NuxtLink
      v-for="photo in photos"
      :key="photo.id"
      :to="`/photo/${photo.id}`"
      class="group overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div class="aspect-[4/3] bg-stone-100">
        <img
          v-if="thumbnails[photo.id]"
          :src="thumbnails[photo.id]"
          :alt="photo.final_caption || photo.category"
          class="h-full w-full object-cover"
          loading="lazy"
        >
        <div v-else class="flex h-full items-center justify-center px-4 text-center text-sm text-stone-500">
          {{ statusLabel(photo.status) }}
        </div>
      </div>
      <div class="space-y-2 p-3">
        <div class="flex items-center justify-between gap-3">
          <span class="rounded-md bg-mist px-2 py-1 text-xs font-semibold uppercase tracking-normal text-moss">
            {{ displayCategory(photo.category) }}
          </span>
          <span class="text-xs text-stone-500">{{ formatDate(photo.taken_at) }}</span>
        </div>
        <p class="line-clamp-2 text-sm text-stone-700">
          {{ photo.final_caption || photo.user_message || 'Untitled photo' }}
        </p>
      </div>
    </NuxtLink>
  </div>
  <div v-else class="rounded-lg border border-dashed border-stone-300 bg-white p-8 text-center text-sm text-stone-600">
    No photos found.
  </div>
</template>
