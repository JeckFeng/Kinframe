<script setup lang="ts">
import type { Photo, PhotoCategory, PresignedUrlResponse } from '~/types/api'

const route = useRoute()
const { apiFetch } = useApi()
const { displayCategory } = usePhotoCategories()
const allowed = ['life', 'travel', 'photography', 'pet']
const category = computed(() => String(route.params.category || '') as PhotoCategory)
const photos = ref<Photo[]>([])
const thumbnails = ref<Record<string, string>>({})
const errorMessage = ref('')
const pending = ref(true)

async function loadPhotos() {
  pending.value = true
  errorMessage.value = ''
  if (!allowed.includes(category.value)) {
    errorMessage.value = 'Unknown category'
    pending.value = false
    return
  }
  try {
    photos.value = await apiFetch<Photo[]>(`/photos?category=${category.value}`)
    const readyPhotos = photos.value.filter(photo => photo.status === 'ready')
    thumbnails.value = Object.fromEntries(
      await Promise.all(readyPhotos.map(async (photo) => {
        const response = await apiFetch<PresignedUrlResponse>(`/photos/${photo.id}/thumbnail-url`)
        return [photo.id, response.url] as const
      })),
    )
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

watch(() => route.params.category, loadPhotos)
onMounted(loadPhotos)
</script>

<template>
  <section class="space-y-5">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 class="text-2xl font-semibold">{{ displayCategory(category) }}</h1>
        <p class="text-sm text-stone-600">{{ photos.length }} photos</p>
      </div>
      <CategoryTabs :active="category" />
    </div>

    <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>
    <div v-if="pending" class="rounded-lg border border-stone-200 bg-white p-8 text-center text-sm text-stone-600">
      Loading photos
    </div>
    <PhotoGrid v-else :photos="photos" :thumbnails="thumbnails" />
  </section>
</template>
