import { nextTick, ref } from 'vue'
import type { PhotoCategoryDefinition, ShowcaseCategory, ShowcasePhotoItem, ShowcaseResponse } from '~/types/api'
import { useShowcaseCategoryMemory } from '~/composables/useShowcaseCategoryMemory'
import type {
  ShowcaseRailActiveChangePayload,
  ShowcaseRailInteractionSource,
  ShowcaseRailSnapshot,
  ShowcaseStageExpose,
  UseShowcaseCategoryMemoryReturn,
} from '~/types/showcase'

interface UseShowcaseArchivePageOptions {
  apiFetch: <T>(path: string) => Promise<T>
  stageRef: { value: ShowcaseStageExpose | null }
  memory?: UseShowcaseCategoryMemoryReturn
  initialCategory?: ShowcaseCategory
}

function toErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'Failed to load showcase'
}

export function useShowcaseArchivePage(options: UseShowcaseArchivePageOptions) {
  const memory = options.memory ?? useShowcaseCategoryMemory()

  const categories = ref<PhotoCategoryDefinition[]>([])
  const photos = ref<ShowcasePhotoItem[]>([])
  const activeCategory = ref<ShowcaseCategory>(options.initialCategory ?? 'life')
  const activePhotoIndex = ref(0)
  const pending = ref(false)
  const errorMessage = ref('')

  function restoreCategorySnapshot(category: ShowcaseCategory): ShowcaseRailSnapshot | null {
    return memory.load(category)?.snapshot ?? null
  }

  function saveCurrentCategorySnapshot() {
    const snapshot = options.stageRef.value?.getSnapshot()
    if (!snapshot) return

    memory.save(activeCategory.value, {
      category: activeCategory.value,
      activeIndex: snapshot.activeIndex,
      snapshot,
      updatedAt: snapshot.timestamp,
    })
  }

  async function loadCategory(category: ShowcaseCategory) {
    pending.value = true
    errorMessage.value = ''

    try {
      const data = await options.apiFetch<ShowcaseResponse>(`/showcase?category=${category}`)
      categories.value = data.categories
      photos.value = data.photos
      activeCategory.value = category
    } catch (error) {
      errorMessage.value = toErrorMessage(error)
    } finally {
      pending.value = false
    }
  }

  async function restoreStageForCategory(category: ShowcaseCategory) {
    await nextTick()
    const snapshot = restoreCategorySnapshot(category)
    options.stageRef.value?.restoreSnapshot(snapshot)
    activePhotoIndex.value = snapshot?.activeIndex ?? 0
  }

  async function initialize() {
    await loadCategory(activeCategory.value)
    await restoreStageForCategory(activeCategory.value)
  }

  async function switchCategory(offset: -1 | 1) {
    if (!categories.value.length) return

    const stage = options.stageRef.value
    saveCurrentCategorySnapshot()
    stage?.suspend()

    try {
      const currentIndex = categories.value.findIndex(category => category.slug === activeCategory.value)
      if (currentIndex === -1) return

      const nextIndex = (currentIndex + offset + categories.value.length) % categories.value.length
      const nextCategory = categories.value[nextIndex]?.slug
      if (!nextCategory) return

      await loadCategory(nextCategory)
      await restoreStageForCategory(nextCategory)
    } finally {
      stage?.resume()
    }
  }

  function handleStageActiveChange(payload: ShowcaseRailActiveChangePayload) {
    activePhotoIndex.value = payload.activeIndex
  }

  function handleStageSettle(snapshot: ShowcaseRailSnapshot) {
    memory.save(activeCategory.value, {
      category: activeCategory.value,
      activeIndex: snapshot.activeIndex,
      snapshot,
      updatedAt: snapshot.timestamp,
    })
    activePhotoIndex.value = snapshot.activeIndex
  }

  async function handleKeydown(event: KeyboardEvent) {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      await switchCategory(1)
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      await switchCategory(-1)
    }
  }

  function advancePhoto(step: number, source: ShowcaseRailInteractionSource = 'programmatic') {
    options.stageRef.value?.jumpBy(step, source)
  }

  return {
    categories,
    photos,
    activeCategory,
    activePhotoIndex,
    pending,
    errorMessage,
    initialize,
    loadCategory,
    switchCategory,
    restoreCategorySnapshot,
    handleStageActiveChange,
    handleStageSettle,
    handleKeydown,
    advancePhoto,
  }
}
