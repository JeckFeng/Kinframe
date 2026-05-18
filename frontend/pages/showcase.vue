<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Grid3X3, Images, ListTodo, LogOut, MapPin, Pause, Play, Upload, Users } from 'lucide-vue-next'
import ShowcaseStage from '~/components/showcase/ShowcaseStage.vue'
import { useShowcaseArchivePage } from '~/composables/useShowcaseArchivePage'
import { useShowcaseCategoryMemory } from '~/composables/useShowcaseCategoryMemory'
import type { PhotoCategoryDefinition, ShowcaseCategory } from '~/types/api'
import type { ShowcaseRailInteractionSource, ShowcaseStageExpose } from '~/types/showcase'

const { apiFetch } = useApi()
const { currentUser, loadMe, logout } = useAuth()
const { showcaseDisplayName } = usePhotoCategories()

const stageRef = ref<ShowcaseStageExpose | null>(null)
const categoryMemory = useShowcaseCategoryMemory()

const {
  categories,
  photos: showcasePhotos,
  activeCategory,
  activePhotoIndex,
  pending,
  errorMessage,
  initialize,
  switchCategory,
  restoreCategorySnapshot,
  handleStageActiveChange,
  handleStageSettle,
  handleKeydown: handleArchiveKeydown,
  advancePhoto,
} = useShowcaseArchivePage({
  apiFetch,
  stageRef,
  memory: categoryMemory,
})

const categoryVisible = ref(false)
const isMobile = ref(false)
const MOBILE_MAX_WIDTH = 428
const indicatorVisible = ref(true)

let hideTimer: ReturnType<typeof setTimeout> | null = null
let hideIndicatorTimer: ReturnType<typeof setTimeout> | null = null

const { isAutoPlaying, autoPlayInterval, toggleAutoPlay, setAutoPlayInterval, stopAutoPlay } = useAutoPlay({
  onAdvance: () => advancePhoto(1, 'autoplay'),
})

const activeCategoryMeta = computed(() =>
  categories.value.find(category => category.slug === activeCategory.value) || null,
)

const orderedCategories = computed(() => {
  const items = categories.value
  if (!items.length) return { prev: null, current: null, next: null } as {
    prev: PhotoCategoryDefinition | null
    current: PhotoCategoryDefinition | null
    next: PhotoCategoryDefinition | null
  }

  const currentIndex = items.findIndex(category => category.slug === activeCategory.value)
  if (currentIndex === -1) {
    return {
      prev: null,
      current: items[0] ?? null,
      next: items.length > 1 ? items[1] ?? null : null,
    }
  }

  const length = items.length
  return {
    prev: length > 1 ? items[(currentIndex - 1 + length) % length] : null,
    current: items[currentIndex] ?? null,
    next: length > 1 ? items[(currentIndex + 1) % length] : null,
  }
})

function checkMobile() {
  isMobile.value = window.innerWidth <= MOBILE_MAX_WIDTH
}

function showCategories() {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
  categoryVisible.value = true
}

function scheduleHideCategories(delay = 800) {
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => {
    categoryVisible.value = false
  }, delay)
}

function toggleCategories() {
  if (categoryVisible.value) {
    categoryVisible.value = false
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
    return
  }

  showCategories()
}

function resetIndicatorVisibility() {
  indicatorVisible.value = true
  if (hideIndicatorTimer) clearTimeout(hideIndicatorTimer)
  hideIndicatorTimer = setTimeout(() => {
    indicatorVisible.value = false
  }, 2000)
}

async function changeCategory(offset: -1 | 1) {
  stopAutoPlay()
  await switchCategory(offset)
  showCategories()
  scheduleHideCategories(2000)
}

async function onKeydown(event: KeyboardEvent) {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return

  if (event.key === 'ArrowRight') {
    event.preventDefault()
    stopAutoPlay()
    advancePhoto(1, 'keyboard')
    return
  }

  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    stopAutoPlay()
    advancePhoto(-1, 'keyboard')
    return
  }

  if (event.key === 'ArrowDown') {
    stopAutoPlay()
    await handleArchiveKeydown(event)
    showCategories()
    scheduleHideCategories(2000)
    return
  }

  if (event.key === 'ArrowUp') {
    stopAutoPlay()
    await handleArchiveKeydown(event)
    showCategories()
    scheduleHideCategories(2000)
    return
  }

  if (event.key.toLowerCase() === 'c') {
    event.preventDefault()
    toggleCategories()
    return
  }

  if (event.key === ' ' || event.key === 'Space') {
    event.preventDefault()
    toggleAutoPlay()
    return
  }

  if (event.key.toLowerCase() === 'm') {
    event.preventDefault()
    await navigateTo('/map')
  }
}

function onStageActiveChange(payload: Parameters<typeof handleStageActiveChange>[0]) {
  handleStageActiveChange(payload)
  resetIndicatorVisibility()
}

function onStageSettle(snapshot: Parameters<typeof handleStageSettle>[0]) {
  handleStageSettle(snapshot)
}

if (!currentUser.value) {
  await loadMe()
}

if (!currentUser.value) {
  await navigateTo('/login')
} else {
  await initialize()
}

onMounted(() => {
  checkMobile()
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', checkMobile)
  window.addEventListener('pointermove', resetIndicatorVisibility)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', checkMobile)
  window.removeEventListener('pointermove', resetIndicatorVisibility)

  if (hideTimer) clearTimeout(hideTimer)
  if (hideIndicatorTimer) clearTimeout(hideIndicatorTimer)
})
</script>

<template>
  <section class="relative min-h-screen overflow-hidden bg-black text-white">
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
        <NuxtLink to="/showcase" class="focus-ring inline-flex items-center gap-2 rounded-md border border-white/8 bg-black/45 px-3 py-2 text-sm font-semibold shadow-lg shadow-black/20 backdrop-blur-xl min-h-[44px] sm:min-h-0">
          <Images class="h-4 w-4 text-moss" aria-hidden="true" />
          KinFrame
        </NuxtLink>

        <div class="flex items-center gap-1 rounded-md border border-white/8 bg-black/45 px-2 py-2 shadow-lg shadow-black/20 backdrop-blur-xl">
          <button
            type="button"
            class="focus-ring inline-flex h-11 w-11 items-center justify-center rounded-md hover:bg-white/10 sm:h-9 sm:w-9"
            :title="isAutoPlaying ? '暂停自动播放' : '开始自动播放'"
            @click="toggleAutoPlay"
          >
            <Pause v-if="isAutoPlaying" :size="18" />
            <Play v-else :size="18" />
          </button>
          <div class="flex rounded-md bg-white/5 p-0.5">
            <button
              v-for="s in [3, 5, 8]"
              :key="s"
              type="button"
              class="rounded px-2 py-1 text-xs transition-colors"
              :class="autoPlayInterval === s * 1000 ? 'bg-white/15 text-white' : 'text-white/60 hover:text-white/80'"
              @click="setAutoPlayInterval(s * 1000)"
            >
              {{ s }}s
            </button>
          </div>
        </div>

        <nav class="flex items-center gap-2 rounded-md border border-white/8 bg-black/45 px-2 py-2 shadow-lg shadow-black/20 backdrop-blur-xl">
          <NuxtLink to="/gallery" class="focus-ring inline-flex h-11 w-11 items-center justify-center rounded-md hover:bg-white/10 sm:h-9 sm:w-9" title="Gallery">
            <Grid3X3 class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink to="/upload" class="focus-ring inline-flex h-11 w-11 items-center justify-center rounded-md hover:bg-white/10 sm:h-9 sm:w-9" title="Upload">
            <Upload class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink to="/map" class="focus-ring inline-flex h-11 w-11 items-center justify-center rounded-md hover:bg-white/10 sm:h-9 sm:w-9" title="地图">
            <MapPin class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink
            v-if="currentUser?.role === 'admin'"
            to="/admin/users"
            class="focus-ring inline-flex h-11 w-11 items-center justify-center rounded-md hover:bg-white/10 sm:h-9 sm:w-9"
            title="Users"
          >
            <Users class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <NuxtLink
            v-if="currentUser?.role === 'admin'"
            to="/admin/jobs"
            class="focus-ring inline-flex h-11 w-11 items-center justify-center rounded-md hover:bg-white/10 sm:h-9 sm:w-9"
            title="Jobs"
          >
            <ListTodo class="h-4 w-4" aria-hidden="true" />
          </NuxtLink>
          <button
            type="button"
            class="focus-ring inline-flex h-11 w-11 items-center justify-center rounded-md hover:bg-white/10 sm:h-9 sm:w-9"
            title="Log out"
            @click="logout"
          >
            <LogOut class="h-4 w-4" aria-hidden="true" />
          </button>
        </nav>
      </div>
    </div>

    <button
      type="button"
      class="fixed left-3 top-1/2 z-30 flex min-h-[44px] min-w-[44px] -translate-y-1/2 items-center justify-center rounded-full border border-white/10 bg-black/50 p-3 shadow-lg backdrop-blur-md sm:hidden"
      :aria-label="categoryVisible ? 'Hide categories' : 'Show categories'"
      @click="toggleCategories"
    >
      <span class="mb-1 block h-px w-4 bg-white/70" />
      <span class="mb-1 block h-px w-4 bg-white/70" />
      <span class="block h-px w-4 bg-white/70" />
    </button>

    <div
      class="fixed inset-y-0 left-0 z-30 hidden w-7 md:block"
      @mouseenter="showCategories"
    />

    <aside
      class="fixed inset-y-0 left-0 z-40 flex items-center transition-[opacity,transform] duration-[360ms,420ms] ease-[ease,cubic-bezier(0.22,1,0.36,1)]"
      :class="categoryVisible ? 'pointer-events-auto translate-x-0 opacity-100' : 'pointer-events-none -translate-x-5 opacity-0'"
      @mouseleave="scheduleHideCategories"
    >
      <div
        class="flex h-full flex-col items-center justify-center gap-8 py-32 pl-4 pr-2.5"
        style="
          background: rgba(0, 0, 0, 0.22);
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
        <button
          v-if="orderedCategories.prev"
          type="button"
          class="transition-colors duration-300 hover:text-white/50"
          style="writing-mode: vertical-rl; text-orientation: upright; color: rgba(255,255,255,0.18); font-size: clamp(13px, 1vw, 16px); font-weight: 400; letter-spacing: 0.12em;"
          @click="changeCategory(-1)"
        >
          {{ showcaseDisplayName(orderedCategories.prev.name) }}
        </button>

        <button
          v-if="orderedCategories.current"
          type="button"
          class="focus-ring -my-1 transition-colors duration-300"
          style="writing-mode: vertical-rl; text-orientation: upright; color: rgba(255,255,255,0.92); font-size: clamp(22px, 2.2vw, 34px); font-weight: 500; letter-spacing: 0.18em; font-family: 'Noto Serif SC', 'Source Han Serif SC', 'STSong', 'Songti SC', 'Noto Serif CJK SC', serif;"
          @click="showCategories"
        >
          {{ showcaseDisplayName(orderedCategories.current.name) }}
        </button>

        <button
          v-if="orderedCategories.next"
          type="button"
          class="transition-colors duration-300 hover:text-white/50"
          style="writing-mode: vertical-rl; text-orientation: upright; color: rgba(255,255,255,0.18); font-size: clamp(13px, 1vw, 16px); font-weight: 400; letter-spacing: 0.12em;"
          @click="changeCategory(1)"
        >
          {{ showcaseDisplayName(orderedCategories.next.name) }}
        </button>
      </div>
    </aside>

    <main class="relative z-10 flex min-h-screen items-center justify-center px-3 py-20 sm:px-8">
      <div v-if="pending" class="text-sm text-white/70">Loading showcase</div>
      <p v-else-if="errorMessage" class="max-w-md rounded-md border border-red-300/40 bg-red-950/60 px-4 py-3 text-sm text-red-50">
        {{ errorMessage }}
      </p>
      <div v-else-if="showcasePhotos.length" class="w-full">
        <ShowcaseStage
          ref="stageRef"
          :photos="showcasePhotos"
          :active-category="activeCategory"
          :initial-snapshot="restoreCategorySnapshot(activeCategory)"
          @active-change="onStageActiveChange"
          @settle="onStageSettle"
        />

        <div
          v-if="isAutoPlaying"
          class="pointer-events-none fixed bottom-5 left-1/2 z-30 h-0.5 w-32 -translate-x-1/2 overflow-hidden rounded-full bg-white/10"
          :class="indicatorVisible ? 'opacity-100' : 'opacity-0'"
          style="transition: opacity 0.6s"
        >
          <div class="h-full rounded-full bg-white/40 animate-pulse" />
        </div>
      </div>
      <div v-else class="text-center">
        <h1 class="text-2xl font-semibold">{{ activeCategoryMeta?.name || 'KinFrame' }}</h1>
        <p class="mt-2 text-sm text-white/65">
          {{ activeCategoryMeta?.name ? `${showcaseDisplayName(activeCategoryMeta.name)} 分类还在等待第一张照片。` : '当前分类还没有可展示的照片。' }}
        </p>
        <NuxtLink to="/upload" class="mt-4 inline-block rounded-md bg-moss px-4 py-2 text-sm font-medium text-white hover:bg-moss/90">
          上传照片
        </NuxtLink>
      </div>
    </main>
  </section>
</template>
