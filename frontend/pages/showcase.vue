<script setup lang="ts">
import { ChevronLeft, ChevronRight, Grid3X3, Images, LogOut, Upload, Users } from 'lucide-vue-next'
import type {
  Photo,
  PhotoCategoryDefinition,
  PresignedUrlResponse,
  ShowcaseCategory,
} from '~/types/api'

const { apiFetch } = useApi()
const { currentUser, loadMe, logout } = useAuth()
const { formatDate } = useFormat()
const { displayCategory } = usePhotoCategories()

const categories = ref<PhotoCategoryDefinition[]>([])
const photos = ref<Photo[]>([])
const previewUrls = ref<Record<string, string>>({})
const activeCategory = ref<ShowcaseCategory>('life')
const activeIndex = ref(0)
const pending = ref(true)
const errorMessage = ref('')
const categoryNavPinned = ref(false)

function matchesCategory(photo: Photo, category: ShowcaseCategory) {
  if (category === 'photography') {
    return photo.category === 'photography' || photo.category === 'travel'
  }
  return photo.category === category
}

const activePhotos = computed(() =>
  photos.value
    .filter(photo => photo.include_in_showcase && photo.status === 'ready' && matchesCategory(photo, activeCategory.value))
    .sort((left, right) => new Date(right.taken_at).getTime() - new Date(left.taken_at).getTime()),
)

const currentPhoto = computed(() => activePhotos.value[activeIndex.value] || null)
const currentPreviewUrl = computed(() => currentPhoto.value ? previewUrls.value[currentPhoto.value.id] : '')
const activeCategoryMeta = computed(() =>
  categories.value.find(category => category.slug === activeCategory.value) || null,
)
const categoryCounts = computed(() => Object.fromEntries(
  categories.value.map(category => [
    category.slug,
    photos.value.filter(photo =>
      photo.include_in_showcase && photo.status === 'ready' && matchesCategory(photo, category.slug),
    ).length,
  ]),
))

async function loadShowcase() {
  pending.value = true
  errorMessage.value = ''
  try {
    categories.value = await apiFetch<PhotoCategoryDefinition[]>('/photos/categories')
    photos.value = await apiFetch<Photo[]>('/photos')
    const readyPhotos = photos.value.filter(photo => photo.status === 'ready')
    previewUrls.value = Object.fromEntries(
      await Promise.all(readyPhotos.map(async (photo) => {
        try {
          const response = await apiFetch<PresignedUrlResponse>(`/photos/${photo.id}/preview-url`)
          return [photo.id, response.url] as const
        } catch {
          return [photo.id, ''] as const
        }
      })),
    )
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

function selectCategory(category: ShowcaseCategory) {
  activeCategory.value = category
  activeIndex.value = 0
}

function nextPhoto() {
  if (!activePhotos.value.length) {
    return
  }
  activeIndex.value = (activeIndex.value + 1) % activePhotos.value.length
}

function previousPhoto() {
  if (!activePhotos.value.length) {
    return
  }
  activeIndex.value = (activeIndex.value - 1 + activePhotos.value.length) % activePhotos.value.length
}

function moveCategory(offset: number) {
  if (!categories.value.length) {
    return
  }
  const index = categories.value.findIndex(category => category.slug === activeCategory.value)
  const nextIndex = (index + offset + categories.value.length) % categories.value.length
  selectCategory(categories.value[nextIndex].slug)
  categoryNavPinned.value = true
}

function onKeydown(event: KeyboardEvent) {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
    return
  }
  if (event.key === 'ArrowRight') {
    event.preventDefault()
    nextPhoto()
  } else if (event.key === 'ArrowLeft') {
    event.preventDefault()
    previousPhoto()
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveCategory(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveCategory(-1)
  } else if (event.key.toLowerCase() === 'c') {
    categoryNavPinned.value = !categoryNavPinned.value
  }
}

if (!currentUser.value) {
  await loadMe()
}

if (!currentUser.value) {
  await navigateTo('/login')
} else {
  await loadShowcase()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <section class="relative h-screen overflow-hidden bg-neutral-950 text-white">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.06),transparent_55%)]" />

    <div class="group/menu fixed inset-x-0 top-0 z-40">
      <div class="h-3" />
      <div
        class="mx-auto flex max-w-6xl translate-y-[-0.75rem] items-center justify-between gap-4 px-4 py-3 opacity-0 transition duration-200 group-hover/menu:translate-y-0 group-hover/menu:opacity-100 focus-within:translate-y-0 focus-within:opacity-100 sm:px-6"
      >
        <NuxtLink to="/showcase" class="focus-ring inline-flex items-center gap-2 rounded-md bg-black/55 px-3 py-2 text-sm font-semibold backdrop-blur">
          <Images class="h-4 w-4 text-moss" aria-hidden="true" />
          KinFrame
        </NuxtLink>
        <nav class="flex items-center gap-2 rounded-md bg-black/55 px-2 py-2 backdrop-blur">
          <NuxtLink to="/gallery" class="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-white/10" title="Gallery">
            <Grid3X3 class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink to="/upload" class="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-white/10" title="Upload">
            <Upload class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink
            v-if="currentUser?.role === 'admin'"
            to="/admin/users"
            class="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-white/10"
            title="Users"
          >
            <Users class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <button
            type="button"
            class="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-white/10"
            title="Log out"
            @click="logout"
          >
            <LogOut class="h-4 w-4" aria-hidden="true" />
          </button>
        </nav>
      </div>
    </div>

    <div class="group/categories fixed inset-y-0 left-0 z-30 flex items-center">
      <div class="h-28 w-2 rounded-r bg-white/10 group-hover/categories:bg-white/25" />
      <aside
        class="ml-0 w-64 -translate-x-full rounded-r border-y border-r border-white/10 bg-black/60 p-3 shadow-2xl backdrop-blur transition duration-200 group-hover/categories:translate-x-0"
        :class="categoryNavPinned ? 'translate-x-0' : ''"
      >
        <div class="mb-2 flex items-center justify-between">
          <p class="text-sm font-semibold">分类</p>
          <button
            type="button"
            class="focus-ring rounded-md px-2 py-1 text-sm text-white/75 hover:bg-white/10"
            @click="categoryNavPinned = !categoryNavPinned"
          >
            C
          </button>
        </div>
        <button
          v-for="category in categories"
          :key="category.slug"
          type="button"
          class="focus-ring mb-2 flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition last:mb-0"
          :class="activeCategory === category.slug ? 'bg-white text-neutral-950' : 'text-white/80 hover:bg-white/10'"
          @click="selectCategory(category.slug)"
        >
          <span>{{ category.name }}</span>
          <span class="text-xs opacity-70">{{ categoryCounts[category.slug] || 0 }}</span>
        </button>
      </aside>
    </div>

    <div class="relative z-10 flex h-full items-center justify-center px-4 py-16 sm:px-8">
      <div v-if="pending" class="text-sm text-white/70">Loading showcase</div>
      <p v-else-if="errorMessage" class="max-w-md rounded-md border border-red-300/40 bg-red-950/60 px-4 py-3 text-sm text-red-50">
        {{ errorMessage }}
      </p>
      <div v-else-if="currentPhoto && currentPreviewUrl" class="flex h-full w-full items-center justify-center">
        <img
          :src="currentPreviewUrl"
          :alt="currentPhoto.final_caption || displayCategory(currentPhoto.category)"
          class="max-h-full max-w-full object-contain shadow-[0_20px_80px_rgba(0,0,0,0.45)]"
        >
      </div>
      <div v-else class="text-center">
        <h1 class="text-2xl font-semibold">{{ activeCategoryMeta?.name || 'KinFrame' }}</h1>
        <p class="mt-2 text-sm text-white/65">还没有可放映的照片</p>
      </div>
    </div>

    <div class="pointer-events-none fixed inset-x-0 bottom-0 z-20 bg-gradient-to-t from-black/70 to-transparent px-4 pb-5 pt-16 sm:px-8">
      <div class="mx-auto flex max-w-6xl items-end justify-between gap-4">
        <div>
          <p class="text-sm font-semibold">{{ activeCategoryMeta?.name || displayCategory(activeCategory) }}</p>
          <p v-if="currentPhoto" class="mt-1 max-w-xl text-sm text-white/70">
            {{ currentPhoto.final_caption || currentPhoto.user_message || formatDate(currentPhoto.taken_at) }}
          </p>
        </div>
        <div class="flex items-center gap-3 text-sm text-white/70">
          <ChevronLeft class="h-4 w-4" aria-hidden="true" />
          <span>{{ activePhotos.length ? activeIndex + 1 : 0 }} / {{ activePhotos.length }}</span>
          <ChevronRight class="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
    </div>
  </section>
</template>
