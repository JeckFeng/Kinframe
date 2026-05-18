import type { Ref, ShallowRef } from 'vue'
import type { PhotoCategoryDefinition, ShowcaseCategory, ShowcasePhotoItem } from '~/types/api'

export type ShowcaseRailInteractionSource =
  | 'wheel'
  | 'touch'
  | 'thumb'
  | 'keyboard'
  | 'autoplay'
  | 'restore'
  | 'programmatic'

export type ShowcaseRailInteractionState =
  | 'idle'
  | 'driving'
  | 'settling'
  | 'snapped'
  | 'suspended'

export interface ShowcaseRailSnapshot {
  currentX: number
  targetX: number
  activeIndex: number
  activePhotoId: string | null
  itemPitchPx: number
  loopSpanPx: number
  timestamp: number
}

export interface ShowcaseRailActiveChangePayload {
  activeIndex: number
  activePhotoId: string | null
  direction: -1 | 0 | 1
  source: ShowcaseRailInteractionSource
  snapshot: ShowcaseRailSnapshot
}

export interface ShowcaseRailInteractionStatePayload {
  state: ShowcaseRailInteractionState
  source: ShowcaseRailInteractionSource | null
}

export interface ShowcaseStripItemLayout {
  index: number
  startPx: number
  centerPx: number
  frameWidthPx: number
  frameHeightPx: number
  backgroundImageOffsetYPx: number
  matteWidthPx: number
  matteHeightPx: number
  holeWidthPx: number
  holeHeightPx: number
}

export interface ShowcaseCardVisualState {
  index: number
  captionTranslateX: number
  timeTranslateX: number
  opacity: number
  normalizedProgress: number
  isVisible: boolean
  isActive: boolean
}

export interface ShowcaseRailConfig {
  loop: boolean
  wheelMultiplier: number
  touchMultiplier: number
  lerp: number
  snapThresholdPx: number
  activeBiasPx: number
  overscanPx: number
}

export interface ShowcaseCategoryMemoryEntry {
  category: ShowcaseCategory
  activeIndex: number
  snapshot: ShowcaseRailSnapshot | null
  updatedAt: number
}

export interface ShowcaseProgressJumpPayload {
  index: number
  source: 'thumb'
}

export interface ShowcaseStageExpose {
  jumpToIndex: (index: number, source?: ShowcaseRailInteractionSource) => void
  jumpBy: (step: number, source?: ShowcaseRailInteractionSource) => void
  restoreSnapshot: (snapshot: ShowcaseRailSnapshot | null | undefined) => void
  getSnapshot: () => ShowcaseRailSnapshot
  suspend: () => void
  resume: () => void
}

export interface ShowcaseStageProps {
  photos: ShowcasePhotoItem[]
  activeCategory: ShowcaseCategory
  initialSnapshot?: ShowcaseRailSnapshot | null
  reducedMotion?: boolean
  showProgress?: boolean
}

export interface ShowcaseRailProps {
  photos: ShowcasePhotoItem[]
  initialSnapshot?: ShowcaseRailSnapshot | null
  reducedMotion?: boolean
  config?: Partial<ShowcaseRailConfig>
}

export interface ShowcaseCardProps {
  item: ShowcasePhotoItem
  index: number
  layout: ShowcaseStripItemLayout
  visual: ShowcaseCardVisualState
  timeLabel: string
  locationLabel: string
  captionLabel: string
}

export interface ShowcaseProgressStripProps {
  photos: ShowcasePhotoItem[]
  activeIndex: number
  reducedMotion?: boolean
}

export interface ShowcaseCategorySidebarProps {
  categories: PhotoCategoryDefinition[]
  activeCategory: ShowcaseCategory
  visible?: boolean
}

export interface UseShowcaseRailOptions {
  photos: Ref<ShowcasePhotoItem[]>
  reducedMotion: Ref<boolean>
  initialSnapshot: Ref<ShowcaseRailSnapshot | null | undefined>
  config?: Partial<ShowcaseRailConfig>
  onActiveChange?: (payload: ShowcaseRailActiveChangePayload) => void
  onSettle?: (snapshot: ShowcaseRailSnapshot) => void
  onInteractionStateChange?: (payload: ShowcaseRailInteractionStatePayload) => void
}

export interface UseShowcaseRailReturn {
  viewportRef: Ref<HTMLElement | null>
  railRef: Ref<HTMLElement | null>
  layouts: ShallowRef<ShowcaseStripItemLayout[]>
  cardStates: ShallowRef<ShowcaseCardVisualState[]>
  activeIndex: Ref<number>
  currentX: Ref<number>
  targetX: Ref<number>
  backgroundOffsetXPx: Ref<number>
  backgroundOffsetYPx: Ref<number>
  foregroundOffsetXPx: Ref<number>
  foregroundOffsetYPx: Ref<number>
  backgroundTravelXPx: Ref<number>
  foregroundTravelXPx: Ref<number>
  viewportWidthPx: Ref<number>
  viewportHeightPx: Ref<number>
  loopSpanPx: Ref<number>
  imageHeightPx: Ref<number>
  matteHeightPx: Ref<number>
  interactionState: Ref<ShowcaseRailInteractionState>
  onWheel: (event: WheelEvent) => void
  onTouchStart: (event: TouchEvent) => void
  onTouchMove: (event: TouchEvent) => void
  onTouchEnd: (event: TouchEvent) => void
  jumpToIndex: (index: number, source?: ShowcaseRailInteractionSource) => void
  jumpBy: (step: number, source?: ShowcaseRailInteractionSource) => void
  restoreSnapshot: (snapshot: ShowcaseRailSnapshot | null | undefined) => void
  getSnapshot: () => ShowcaseRailSnapshot
  suspend: () => void
  resume: () => void
  recalc: () => void
  destroy: () => void
}

export interface UseShowcaseCategoryMemoryReturn {
  save: (category: ShowcaseCategory, entry: ShowcaseCategoryMemoryEntry) => void
  load: (category: ShowcaseCategory) => ShowcaseCategoryMemoryEntry | null
  has: (category: ShowcaseCategory) => boolean
  clear: (category?: ShowcaseCategory) => void
}
