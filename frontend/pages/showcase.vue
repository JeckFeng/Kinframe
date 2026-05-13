<script setup lang="ts">
import { ChevronLeft, ChevronRight, Grid3X3, Images, ListTodo, LogOut, Upload, Users } from 'lucide-vue-next'
import type { PhotoCategoryDefinition, ShowcaseCategory, ShowcasePhotoItem, ShowcaseResponse } from '~/types/api'
import SlideRenderer from '~/app/slide-renderer/components/SlideRenderer.vue'
import type { SlideDesign } from '~/app/slide-renderer/types'

const { apiFetch } = useApi()
const { currentUser, loadMe, logout } = useAuth()
const { formatDate } = useFormat()
const { displayCategory, showcaseDisplayName } = usePhotoCategories()

type TransitionDirection = 'next-photo' | 'prev-photo' | 'next-category' | 'prev-category' | 'initial'

const categories = ref<PhotoCategoryDefinition[]>([])
const showcasePhotos = ref<ShowcasePhotoItem[]>([])
const activeCategory = ref<ShowcaseCategory>('life')
const activeIndex = ref(0)
const pending = ref(true)
const errorMessage = ref('')
const categoryVisible = ref(false)
const transitionDirection = ref<TransitionDirection>('initial')
const transitionLocked = ref(false)
const positionMemory = ref<Partial<Record<ShowcaseCategory, number>>>({})
let hideTimer: ReturnType<typeof setTimeout> | null = null
let wheelAccumulator = 0
let wheelTimer: ReturnType<typeof setTimeout> | null = null

const orderedCategories = computed(() => {
  const items = categories.value
  if (!items.length) return { prev: null, current: null, next: null }
  const currentIdx = items.findIndex(c => c.slug === activeCategory.value)
  if (currentIdx === -1) return { prev: null, current: items[0] ?? null, next: null }
  const len = items.length
  return {
    prev: len > 1 ? items[(currentIdx - 1 + len) % len] : null,
    current: items[currentIdx],
    next: len > 1 ? items[(currentIdx + 1) % len] : null,
  }
})

const activePhotos = computed(() => {
  if (showcasePhotos.value.length === 0) return []
  return showcasePhotos.value
})

const currentItem = computed(() => activePhotos.value[activeIndex.value] || null)
const currentDesign = computed<SlideDesign | null>(() => {
  if (!currentItem.value || !currentItem.value.slide_design) return null
  return currentItem.value.slide_design as unknown as SlideDesign
})
const currentPreviewUrl = computed(() => currentItem.value?.preview_url || '')
const currentTimeText = computed(() => {
  if (!currentItem.value?.photo.taken_at) return ''
  return formatDate(currentItem.value.photo.taken_at)
})
const activeCategoryMeta = computed(() =>
  categories.value.find(c => c.slug === activeCategory.value) || null,
)
const categoryCounts = computed(() => Object.fromEntries(
  categories.value.map(c => [
    c.slug,
    c.slug === activeCategory.value ? activePhotos.value.length : null,
  ]),
))

const slideKey = computed(() => `${activeCategory.value}-${activeIndex.value}`)

const locationSummary = computed(() => {
  const p = currentItem.value?.photo
  if (!p) return ''
  const parts = [p.location_city, p.location_region, p.location_country].filter(Boolean)
  return parts.join(', ')
})

function isInteractiveElement(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return target.closest('button, a, input, textarea, [role="menuitem"], aside') !== null
}

const transitionName = computed(() => {
  switch (transitionDirection.value) {
    case 'next-photo': return 'kf-photo-next'
    case 'prev-photo': return 'kf-photo-prev'
    case 'next-category': return 'kf-category-next'
    case 'prev-category': return 'kf-category-prev'
    default: return 'kf-fade'
  }
})

function showCategories() {
  if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
  categoryVisible.value = true
}

function scheduleHideCategories(delay = 800) {
  hideTimer = setTimeout(() => {
    categoryVisible.value = false
  }, delay)
}

function toggleCategories() {
  if (categoryVisible.value) {
    categoryVisible.value = false
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
  } else {
    showCategories()
  }
}

function preloadAdjacent() {
  if (typeof Image === 'undefined') return
  const photos = activePhotos.value
  const idx = activeIndex.value
  const urls: string[] = []
  if (photos[idx - 1]?.preview_url) urls.push(photos[idx - 1].preview_url)
  if (photos[idx + 1]?.preview_url) urls.push(photos[idx + 1].preview_url)
  for (const url of urls) {
    new Image().src = url
  }
}

async function loadShowcase(category: ShowcaseCategory) {
  pending.value = true
  errorMessage.value = ''
  try {
    const data = await apiFetch<ShowcaseResponse>(`/showcase?category=${category}`)
    categories.value = data.categories
    showcasePhotos.value = data.photos
    preloadAdjacent()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

async function switchCategory(category: ShowcaseCategory) {
  positionMemory.value[activeCategory.value] = activeIndex.value
  const data = await apiFetch<ShowcaseResponse>(`/showcase?category=${category}`)
  activeCategory.value = category
  const saved = positionMemory.value[category]
  const idx = saved ?? 0
  activeIndex.value = idx < data.photos.length ? idx : 0
  showcasePhotos.value = data.photos
  categories.value = data.categories
  preloadAdjacent()
}

async function selectCategoryFade(category: ShowcaseCategory) {
  if (transitionLocked.value) return
  transitionDirection.value = 'initial'
  transitionLocked.value = true
  await switchCategory(category)
  setTimeout(() => { transitionLocked.value = false }, 500)
}

function nextPhoto() {
  if (!activePhotos.value.length || transitionLocked.value) return
  transitionDirection.value = 'next-photo'
  transitionLocked.value = true
  activeIndex.value = (activeIndex.value + 1) % activePhotos.value.length
  preloadAdjacent()
  setTimeout(() => { transitionLocked.value = false }, 500)
}

function previousPhoto() {
  if (!activePhotos.value.length || transitionLocked.value) return
  transitionDirection.value = 'prev-photo'
  transitionLocked.value = true
  activeIndex.value = (activeIndex.value - 1 + activePhotos.value.length) % activePhotos.value.length
  preloadAdjacent()
  setTimeout(() => { transitionLocked.value = false }, 500)
}

async function moveCategory(offset: number) {
  if (!categories.value.length || transitionLocked.value) return
  transitionDirection.value = offset > 0 ? 'next-category' : 'prev-category'
  transitionLocked.value = true
  const index = categories.value.findIndex(c => c.slug === activeCategory.value)
  const nextIndex = (index + offset + categories.value.length) % categories.value.length
  await switchCategory(categories.value[nextIndex].slug)
  showCategories()
  scheduleHideCategories(2000)
  setTimeout(() => { transitionLocked.value = false }, 700)
}

function onKeydown(event: KeyboardEvent) {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return
  if (event.key === 'ArrowRight') { event.preventDefault(); nextPhoto() }
  else if (event.key === 'ArrowLeft') { event.preventDefault(); previousPhoto() }
  else if (event.key === 'ArrowDown') { event.preventDefault(); moveCategory(1) }
  else if (event.key === 'ArrowUp') { event.preventDefault(); moveCategory(-1) }
  else if (event.key.toLowerCase() === 'c') { event.preventDefault(); toggleCategories() }
}

function onMouseClick(event: MouseEvent) {
  if (isInteractiveElement(event.target)) return
  if (!activePhotos.value.length || transitionLocked.value) return
  event.preventDefault()
  previousPhoto()
}

function onContextMenu(event: MouseEvent) {
  if (isInteractiveElement(event.target)) return
  if (!activePhotos.value.length || transitionLocked.value) return
  event.preventDefault()
  nextPhoto()
}

function onWheel(event: WheelEvent) {
  if (isInteractiveElement(event.target)) return
  if (transitionLocked.value) return
  event.preventDefault()
  wheelAccumulator += event.deltaY
  if (wheelTimer !== null) clearTimeout(wheelTimer)
  wheelTimer = setTimeout(() => {
    if (transitionLocked.value) { wheelAccumulator = 0; return }
    if (wheelAccumulator > 40) moveCategory(1)
    else if (wheelAccumulator < -40) moveCategory(-1)
    wheelAccumulator = 0
  }, 400)
}

if (!currentUser.value) { await loadMe() }
if (!currentUser.value) {
  await navigateTo('/login')
} else {
  await loadShowcase(activeCategory.value)
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('click', onMouseClick)
  window.addEventListener('contextmenu', onContextMenu)
  window.addEventListener('wheel', onWheel, { passive: false })
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('click', onMouseClick)
  window.removeEventListener('contextmenu', onContextMenu)
  window.removeEventListener('wheel', onWheel)
  if (hideTimer) clearTimeout(hideTimer)
  if (wheelTimer) clearTimeout(wheelTimer)
})
</script>

<template>
  <section class="relative h-screen overflow-hidden bg-neutral-950 text-white">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.06),transparent_55%)]" />

    <!-- Hidden top menu — revealed on hover -->
    <div class="group/menu fixed inset-x-0 top-0 z-40">
      <div class="h-3" />
      <div
        class="mx-auto flex max-w-6xl translate-y-[-0.75rem] items-center justify-between gap-4 px-4 py-3 opacity-0 transition duration-300 group-hover/menu:translate-y-0 group-hover/menu:opacity-100 focus-within:translate-y-0 focus-within:opacity-100 sm:px-6"
      >
        <NuxtLink to="/showcase" class="focus-ring inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold bg-neutral-950/35 backdrop-blur-xl border border-white/8 shadow-lg shadow-black/20">
          <Images class="h-4 w-4 text-moss" aria-hidden="true" />
          KinFrame
        </NuxtLink>
        <nav class="flex items-center gap-2 rounded-md px-2 py-2 bg-neutral-950/35 backdrop-blur-xl border border-white/8 shadow-lg shadow-black/20">
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
          <NuxtLink
            v-if="currentUser?.role === 'admin'"
            to="/admin/jobs"
            class="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-white/10"
            title="Jobs"
          >
            <ListTodo class="h-4 w-4" aria-hidden="true" />
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

    <!-- Left category sidebar — hover trigger strip -->
    <div
      class="fixed inset-y-0 left-0 z-30 hidden w-7 md:block"
      @mouseenter="showCategories"
    />

    <!-- Left category sidebar — narrow vertical panel -->
    <aside
      class="fixed inset-y-0 left-0 z-40 flex items-center transition-[opacity,transform] duration-[360ms,420ms] ease-[ease,cubic-bezier(0.22,1,0.36,1)]"
      :class="categoryVisible ? 'opacity-100 translate-x-0 pointer-events-auto' : 'opacity-0 -translate-x-5 pointer-events-none'"
      @mouseleave="scheduleHideCategories"
    >
      <div
        class="flex h-full flex-col items-center justify-center gap-8 py-32 pl-4 pr-2.5"
        style="
          background: rgba(10, 12, 18, 0.18);
          backdrop-filter: blur(18px) saturate(1.15);
          -webkit-backdrop-filter: blur(18px) saturate(1.15);
          border-right: 1px solid rgba(255,255,255,0.06);
          box-shadow: 0 24px 80px rgba(0,0,0,0.18);
          mask-image: linear-gradient(
            to bottom,
            transparent 0%,
            rgba(0,0,0,0.35) 18%,
            black 40%,
            black 60%,
            rgba(0,0,0,0.35) 82%,
            transparent 100%
          );
          -webkit-mask-image: linear-gradient(
            to bottom,
            transparent 0%,
            rgba(0,0,0,0.35) 18%,
            black 40%,
            black 60%,
            rgba(0,0,0,0.35) 82%,
            transparent 100%
          );
        "
      >
        <!-- Previous category — dimmed -->
        <button
          v-if="orderedCategories.prev"
          type="button"
          class="transition-colors duration-300 hover:text-white/50"
          style="writing-mode: vertical-rl; text-orientation: upright; color: rgba(255,255,255,0.18); font-size: clamp(13px, 1vw, 16px); font-weight: 400; letter-spacing: 0.12em;"
          @click="selectCategoryFade(orderedCategories.prev.slug)"
        >
          {{ showcaseDisplayName(orderedCategories.prev.name) }}
        </button>

        <!-- Current category — prominent -->
        <button
          v-if="orderedCategories.current"
          type="button"
          class="focus-ring -my-1 transition-colors duration-300"
          style="writing-mode: vertical-rl; text-orientation: upright; color: rgba(255,255,255,0.92); font-size: clamp(22px, 2.2vw, 34px); font-weight: 500; letter-spacing: 0.18em; font-family: 'Noto Serif SC', 'Source Han Serif SC', 'STSong', 'Songti SC', 'Noto Serif CJK SC', serif;"
          @click="selectCategoryFade(orderedCategories.current.slug)"
        >
          {{ showcaseDisplayName(orderedCategories.current.name) }}
        </button>

        <!-- Next category — dimmed -->
        <button
          v-if="orderedCategories.next"
          type="button"
          class="transition-colors duration-300 hover:text-white/50"
          style="writing-mode: vertical-rl; text-orientation: upright; color: rgba(255,255,255,0.18); font-size: clamp(13px, 1vw, 16px); font-weight: 400; letter-spacing: 0.12em;"
          @click="selectCategoryFade(orderedCategories.next.slug)"
        >
          {{ showcaseDisplayName(orderedCategories.next.name) }}
        </button>
      </div>
    </aside>

    <!-- Main slide area -->
    <div class="relative z-10 flex h-full items-center justify-center">
      <div v-if="pending" class="text-sm text-white/70">Loading showcase</div>
      <p v-else-if="errorMessage" class="max-w-md rounded-md border border-red-300/40 bg-red-950/60 px-4 py-3 text-sm text-red-50">
        {{ errorMessage }}
      </p>
      <div v-else-if="currentItem" class="h-full w-full">
        <Transition :name="transitionName" mode="out-in">
          <SlideRenderer
            :key="slideKey"
            :design-json="currentDesign"
            :preview-url="currentPreviewUrl"
            :photo-index="activeIndex"
            :photo-count="activePhotos.length"
            :time-text="currentTimeText"
            :location-text="locationSummary"
          />
        </Transition>
      </div>
      <div v-else class="text-center">
        <h1 class="text-2xl font-semibold">{{ activeCategoryMeta?.name || 'KinFrame' }}</h1>
        <p class="mt-2 text-sm text-white/65">还没有可放映的照片</p>
        <NuxtLink to="/upload" class="mt-4 inline-block rounded-md bg-moss px-4 py-2 text-sm font-medium text-white hover:bg-moss/90">
          上传照片
        </NuxtLink>
      </div>
    </div>

    <!-- Bottom info bar -->
    <div class="pointer-events-none fixed inset-x-0 bottom-0 z-20 bg-gradient-to-t from-black/70 to-transparent px-4 pb-5 pt-16 sm:px-8">
      <div class="mx-auto flex max-w-6xl items-end justify-between gap-4">
        <div>
          <p class="text-sm font-semibold">{{ activeCategoryMeta?.name ? showcaseDisplayName(activeCategoryMeta.name) : showcaseDisplayName(activeCategory) }}</p>
          <Transition name="kf-caption" mode="out-in">
            <p v-if="currentItem" :key="slideKey" class="mt-1 max-w-xl text-sm text-white/70">
              {{ currentItem.photo.final_caption || currentItem.photo.user_message || formatDate(currentItem.photo.taken_at) }}
              <span v-if="locationSummary" class="text-white/50"> · {{ locationSummary }}</span>
            </p>
          </Transition>
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
