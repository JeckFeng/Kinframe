<script setup lang="ts">
import { ChevronLeft, ChevronRight, Grid3X3, Images, ListTodo, LogOut, MapPin, Pause, Play, Upload, Users } from 'lucide-vue-next'
import type { PhotoCategoryDefinition, ShowcaseCategory, ShowcasePhotoItem, ShowcaseResponse } from '~/types/api'
import SlideRenderer from '~/app/slide-renderer/components/SlideRenderer.vue'
import type { SlideDesign } from '~/app/slide-renderer/types'

const { apiFetch } = useApi()
const { currentUser, loadMe, logout } = useAuth()
const { formatDate } = useFormat()
const { displayCategory, showcaseDisplayName } = usePhotoCategories()
const { preloadAdjacent, cancelPreloads, preloadingCount } = useImagePreload()
const { getTransitionName, formatPosition, emptyStateMessage } = useSlideNavigation()

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

// Mobile-specific state
const isMobile = ref(false)
const MOBILE_MAX_WIDTH = 428
let touchStartX = 0
let touchStartY = 0
const SWIPE_THRESHOLD = 50

const { isAutoPlaying, autoPlayInterval, toggleAutoPlay, setAutoPlayInterval, stopAutoPlay } = useAutoPlay({
  onAdvance: () => nextPhoto(),
})

const indicatorVisible = ref(true)
let hideIndicatorTimer: ReturnType<typeof setTimeout> | null = null

function resetIndicatorVisibility() {
  indicatorVisible.value = true
  if (hideIndicatorTimer) clearTimeout(hideIndicatorTimer)
  hideIndicatorTimer = setTimeout(() => {
    indicatorVisible.value = false
  }, 2000)
}

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

const transitionName = computed(() => getTransitionName(transitionDirection.value))

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

function triggerPreload() {
  preloadAdjacent(activePhotos.value, activeIndex.value)
}

async function loadShowcase(category: ShowcaseCategory) {
  pending.value = true
  errorMessage.value = ''
  try {
    const data = await apiFetch<ShowcaseResponse>(`/showcase?category=${category}`)
    categories.value = data.categories
    showcasePhotos.value = data.photos
    triggerPreload()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

async function switchCategory(category: ShowcaseCategory) {
  cancelPreloads()
  positionMemory.value[activeCategory.value] = activeIndex.value
  const data = await apiFetch<ShowcaseResponse>(`/showcase?category=${category}`)
  activeCategory.value = category
  const saved = positionMemory.value[category]
  const idx = saved ?? 0
  activeIndex.value = idx < data.photos.length ? idx : 0
  showcasePhotos.value = data.photos
  categories.value = data.categories
  triggerPreload()
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
  triggerPreload()
  setTimeout(() => { transitionLocked.value = false }, 500)
}

function previousPhoto() {
  if (!activePhotos.value.length || transitionLocked.value) return
  transitionDirection.value = 'prev-photo'
  transitionLocked.value = true
  activeIndex.value = (activeIndex.value - 1 + activePhotos.value.length) % activePhotos.value.length
  triggerPreload()
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

function checkMobile() {
  isMobile.value = window.innerWidth <= MOBILE_MAX_WIDTH
}

function onTouchStart(event: TouchEvent) {
  if (isInteractiveElement(event.target)) return
  const touch = event.touches[0]
  touchStartX = touch.clientX
  touchStartY = touch.clientY
}

function onTouchEnd(event: TouchEvent) {
  if (isInteractiveElement(event.target)) return
  if (!activePhotos.value.length || transitionLocked.value) return
  const touch = event.changedTouches[0]
  const dx = touch.clientX - touchStartX
  const dy = touch.clientY - touchStartY
  const absDx = Math.abs(dx)
  const absDy = Math.abs(dy)

  if (Math.max(absDx, absDy) < SWIPE_THRESHOLD) return

  stopAutoPlay()

  if (absDx > absDy) {
    event.preventDefault()
    if (dx < 0) nextPhoto()
    else previousPhoto()
  } else {
    event.preventDefault()
    if (dy < 0) moveCategory(1)
    else moveCategory(-1)
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return
  if (event.key === 'ArrowRight') { event.preventDefault(); stopAutoPlay(); nextPhoto() }
  else if (event.key === 'ArrowLeft') { event.preventDefault(); stopAutoPlay(); previousPhoto() }
  else if (event.key === 'ArrowDown') { event.preventDefault(); stopAutoPlay(); moveCategory(1) }
  else if (event.key === 'ArrowUp') { event.preventDefault(); stopAutoPlay(); moveCategory(-1) }
  else if (event.key.toLowerCase() === 'c') { event.preventDefault(); toggleCategories() }
  else if (event.key === ' ' || event.key === 'Space') { event.preventDefault(); toggleAutoPlay() }
  else if (event.key.toLowerCase() === 'm') { event.preventDefault(); navigateTo('/map') }
}

function onMouseClick(event: MouseEvent) {
  if (isInteractiveElement(event.target)) return
  if (!activePhotos.value.length || transitionLocked.value) return
  event.preventDefault()
  stopAutoPlay()
  previousPhoto()
}

function onContextMenu(event: MouseEvent) {
  if (isInteractiveElement(event.target)) return
  if (!activePhotos.value.length || transitionLocked.value) return
  event.preventDefault()
  stopAutoPlay()
  nextPhoto()
}

function onWheel(event: WheelEvent) {
  if (isInteractiveElement(event.target)) return
  if (transitionLocked.value) return
  event.preventDefault()
  stopAutoPlay()
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
  checkMobile()
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('click', onMouseClick)
  window.addEventListener('contextmenu', onContextMenu)
  window.addEventListener('wheel', onWheel, { passive: false })
  window.addEventListener('touchstart', onTouchStart, { passive: true })
  window.addEventListener('touchend', onTouchEnd, { passive: false })
  window.addEventListener('resize', checkMobile)
  window.addEventListener('pointermove', resetIndicatorVisibility)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('click', onMouseClick)
  window.removeEventListener('contextmenu', onContextMenu)
  window.removeEventListener('wheel', onWheel)
  window.removeEventListener('touchstart', onTouchStart)
  window.removeEventListener('touchend', onTouchEnd)
  window.removeEventListener('resize', checkMobile)
  window.removeEventListener('pointermove', resetIndicatorVisibility)
  if (hideTimer) clearTimeout(hideTimer)
  if (wheelTimer) clearTimeout(wheelTimer)
  if (hideIndicatorTimer) clearTimeout(hideIndicatorTimer)
})
</script>

<template>
  <section class="relative h-screen overflow-hidden bg-neutral-950 text-white">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.06),transparent_55%)]" />

    <!-- Hidden top menu — tap top area on mobile to reveal -->
    <div
      class="group/menu fixed inset-x-0 top-0 z-40"
      :class="isMobile ? 'cursor-pointer' : ''"
      @click.stop="isMobile ? isMobile = false : undefined"
    >
      <div class="h-3 sm:h-4" />
      <div
        class="mx-auto flex max-w-6xl translate-y-[-0.75rem] items-center justify-between gap-4 px-4 py-3 opacity-0 transition duration-300 group-hover/menu:translate-y-0 group-hover/menu:opacity-100 focus-within:translate-y-0 focus-within:opacity-100"
        :class="isMobile ? 'translate-y-0 opacity-100 sm:translate-y-[-0.75rem] sm:opacity-0' : 'sm:px-6'"
      >
        <NuxtLink to="/showcase" class="focus-ring inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold bg-neutral-950/35 backdrop-blur-xl border border-white/8 shadow-lg shadow-black/20 min-h-[44px] sm:min-h-0">
          <Images class="h-4 w-4 text-moss" aria-hidden="true" />
          KinFrame
        </NuxtLink>
        <!-- Auto-play controls -->
        <div class="flex items-center gap-1 rounded-md px-2 py-2 bg-neutral-950/35 backdrop-blur-xl border border-white/8 shadow-lg shadow-black/20">
          <button
            type="button"
            class="focus-ring inline-flex h-11 w-11 sm:h-9 sm:w-9 items-center justify-center rounded-md hover:bg-white/10"
            :title="isAutoPlaying ? '暂停自动播放' : '开始自动播放'"
            @click="toggleAutoPlay"
          >
            <Pause v-if="isAutoPlaying" :size="18" />
            <Play v-else :size="18" />
          </button>
          <div class="flex rounded-md bg-white/5 p-0.5">
            <button
              v-for="s in [3, 5, 8]" :key="s"
              type="button"
              @click="setAutoPlayInterval(s * 1000)"
              :class="autoPlayInterval === s * 1000 ? 'bg-white/15 text-white' : 'text-white/60 hover:text-white/80'"
              class="px-2 py-1 text-xs rounded transition-colors"
            >
              {{ s }}s
            </button>
          </div>
        </div>
        <nav class="flex items-center gap-2 rounded-md px-2 py-2 bg-neutral-950/35 backdrop-blur-xl border border-white/8 shadow-lg shadow-black/20">
          <NuxtLink to="/gallery" class="focus-ring inline-flex h-11 w-11 sm:h-9 sm:w-9 items-center justify-center rounded-md hover:bg-white/10" title="Gallery">
            <Grid3X3 class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink to="/upload" class="focus-ring inline-flex h-11 w-11 sm:h-9 sm:w-9 items-center justify-center rounded-md hover:bg-white/10" title="Upload">
            <Upload class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink to="/map" class="focus-ring inline-flex h-11 w-11 sm:h-9 sm:w-9 items-center justify-center rounded-md hover:bg-white/10" title="地图">
            <MapPin class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink
            v-if="currentUser?.role === 'admin'"
            to="/admin/users"
            class="focus-ring inline-flex h-11 w-11 sm:h-9 sm:w-9 items-center justify-center rounded-md hover:bg-white/10"
            title="Users"
          >
            <Users class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink
            v-if="currentUser?.role === 'admin'"
            to="/admin/jobs"
            class="focus-ring inline-flex h-11 w-11 sm:h-9 sm:w-9 items-center justify-center rounded-md hover:bg-white/10"
            title="Jobs"
          >
            <ListTodo class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <button
            type="button"
            class="focus-ring inline-flex h-11 w-11 sm:h-9 sm:w-9 items-center justify-center rounded-md hover:bg-white/10"
            title="Log out"
            @click="logout"
          >
            <LogOut class="h-4 w-4" aria-hidden="true" />
          </button>
        </nav>
      </div>
    </div>

    <!-- Mobile hamburger for categories -->
    <button
      type="button"
      class="fixed left-3 top-1/2 z-30 -translate-y-1/2 rounded-full bg-neutral-950/40 backdrop-blur-md border border-white/10 p-3 shadow-lg sm:hidden min-h-[44px] min-w-[44px] flex items-center justify-center"
      :aria-label="categoryVisible ? 'Hide categories' : 'Show categories'"
      @click="toggleCategories"
    >
      <span class="block w-4 h-px bg-white/70 mb-1" />
      <span class="block w-4 h-px bg-white/70 mb-1" />
      <span class="block w-4 h-px bg-white/70" />
    </button>

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
        <!-- Auto-play progress bar -->
        <div
          v-if="isAutoPlaying"
          class="absolute bottom-24 left-1/2 -translate-x-1/2 w-32 h-0.5 bg-white/10 rounded-full overflow-hidden z-30"
          :class="indicatorVisible ? 'opacity-100' : 'opacity-0'"
          style="transition: opacity 0.6s"
        >
          <div class="h-full bg-white/40 rounded-full animate-pulse" />
        </div>
      </div>
      <div v-else class="text-center">
        <h1 class="text-2xl font-semibold">{{ activeCategoryMeta?.name || 'KinFrame' }}</h1>
        <p class="mt-2 text-sm text-white/65">{{ emptyStateMessage(activeCategoryMeta?.name || '') }}</p>
        <NuxtLink to="/upload" class="mt-4 inline-block rounded-md bg-moss px-4 py-2 text-sm font-medium text-white hover:bg-moss/90">
          上传照片
        </NuxtLink>
      </div>
    </div>

    <!-- Bottom info bar -->
    <div class="pointer-events-none fixed inset-x-0 bottom-0 z-20 bg-gradient-to-t from-black/70 to-transparent px-3 pb-4 pt-12 sm:px-8 sm:pb-5 sm:pt-16">
      <div class="mx-auto flex max-w-6xl items-end justify-between gap-4">
        <div class="hidden sm:block">
          <p class="text-sm font-semibold">{{ activeCategoryMeta?.name ? showcaseDisplayName(activeCategoryMeta.name) : showcaseDisplayName(activeCategory) }}</p>
          <Transition name="kf-caption" mode="out-in">
            <p v-if="currentItem" :key="slideKey" class="mt-1 max-w-xl text-sm text-white/70">
              {{ currentItem.photo.final_caption || currentItem.photo.user_message || formatDate(currentItem.photo.taken_at) }}
              <span v-if="locationSummary" class="text-white/50"> · {{ locationSummary }}</span>
            </p>
          </Transition>
        </div>
        <!-- Mobile: compact position indicator only -->
        <div class="sm:hidden w-full text-center">
          <p class="text-xs text-white/50">{{ activeCategoryMeta?.name ? showcaseDisplayName(activeCategoryMeta.name) : '' }}</p>
        </div>
        <div class="flex items-center gap-2 sm:gap-3 text-sm text-white/70">
          <ChevronLeft class="h-4 w-4" aria-hidden="true" />
          <span class="text-xs sm:text-sm">{{ formatPosition(activeIndex, activePhotos.length) }}</span>
          <ChevronRight class="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
    </div>
  </section>
</template>
