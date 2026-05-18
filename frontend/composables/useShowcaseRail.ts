import { ref, shallowRef, watch } from 'vue'
import type { ShowcasePhotoItem } from '~/types/api'
import type {
  UseShowcaseRailOptions,
  UseShowcaseRailReturn,
  ShowcaseRailInteractionSource,
  ShowcaseRailSnapshot,
  ShowcaseCardVisualState,
  ShowcaseStripItemLayout,
} from '~/types/showcase'

const DEFAULT_VIEWPORT_HEIGHT_PX = 900
const DEFAULT_LOOP_SPAN_PX = 960
const DEFAULT_MASK_SPEED_MULTIPLIER = 1.5
const DEFAULT_CONFIG = {
  loop: true,
  wheelMultiplier: 1,
  touchMultiplier: 1,
  lerp: 0.18,
  snapThresholdPx: 0.5,
  activeBiasPx: 0,
  overscanPx: 0,
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function normalizeLoopX(value: number, loopSpanPx: number): number {
  if (loopSpanPx <= 0) return 0
  return ((value % loopSpanPx) + loopSpanPx) % loopSpanPx
}

function computeRenderCycleFactor(multiplier: number): number {
  for (let factor = 1; factor <= 12; factor += 1) {
    const steps = multiplier * factor
    if (Math.abs(steps - Math.round(steps)) < 0.000001) {
      return factor
    }
  }

  return 1
}

function computeRenderRepeatCount(multiplier: number): number {
  const cycleFactor = computeRenderCycleFactor(multiplier)
  const phaseSteps = Math.max(1, Math.round(multiplier * cycleFactor))
  return phaseSteps + 4
}

export function getShowcaseRenderCopyLabels(multiplier = DEFAULT_MASK_SPEED_MULTIPLIER): string[] {
  const repeatCount = computeRenderRepeatCount(multiplier)
  const middleIndex = Math.floor(repeatCount / 2)

  return Array.from({ length: repeatCount }, (_, index) => {
    if (index === middleIndex) return 'current'
    if (index < middleIndex) return `before-${middleIndex - index}`
    return `after-${index - middleIndex}`
  })
}

function getTouchClientX(event: TouchEvent): number | null {
  const primaryTouch = event.touches[0] ?? event.changedTouches[0]
  return typeof primaryTouch?.clientX === 'number' ? primaryTouch.clientX : null
}

function circularDistance(from: number, to: number, loopSpanPx: number): number {
  if (loopSpanPx <= 0) return to - from
  const direct = to - from
  const wrappedForward = direct + loopSpanPx
  const wrappedBackward = direct - loopSpanPx
  return [direct, wrappedForward, wrappedBackward].sort((a, b) => Math.abs(a) - Math.abs(b))[0] ?? direct
}

function computeDirection(previousIndex: number, nextIndex: number, length: number): -1 | 0 | 1 {
  if (previousIndex === nextIndex || length <= 1) return 0
  const forwardDistance = (nextIndex - previousIndex + length) % length
  const backwardDistance = (previousIndex - nextIndex + length) % length
  return forwardDistance <= backwardDistance ? 1 : -1
}

export function computeStripLayouts(photos: ShowcasePhotoItem[], viewportHeightPx: number) {
  const safeViewportHeightPx = viewportHeightPx > 0 ? viewportHeightPx : DEFAULT_VIEWPORT_HEIGHT_PX
  const frameHeightPx = Math.round(clamp(safeViewportHeightPx * 0.34, 220, 380))
  const frameWidthPx = Math.round(clamp(frameHeightPx * 1.28, 280, 520))
  const mattePadXPx = Math.round(clamp(frameHeightPx * 0.16, 30, 68))
  const mattePadYPx = Math.round(clamp(frameHeightPx * 0.18, 32, 74))

  let cursorPx = 0
  const layouts: ShowcaseStripItemLayout[] = photos.map((_, index) => {
    const startPx = cursorPx
    const centerPx = startPx + frameWidthPx / 2
    cursorPx += frameWidthPx

    return {
      index,
      startPx,
      centerPx,
      frameWidthPx,
      frameHeightPx,
      matteWidthPx: frameWidthPx + mattePadXPx * 2,
      matteHeightPx: frameHeightPx + mattePadYPx * 2,
      holeWidthPx: frameWidthPx,
      holeHeightPx: frameHeightPx,
    }
  })

  return {
    layouts,
    loopSpanPx: cursorPx > 0 ? cursorPx : DEFAULT_LOOP_SPAN_PX,
    imageHeightPx: frameHeightPx,
    matteHeightPx: frameHeightPx + mattePadYPx * 2,
    averagePitchPx: layouts.length ? cursorPx / layouts.length : 0,
  }
}

function computeActiveIndex(
  layouts: ShowcaseStripItemLayout[],
  currentX: number,
  activeBiasPx: number,
  loopSpanPx: number,
): number {
  if (!layouts.length) return 0

  const normalizedX = normalizeLoopX(currentX + activeBiasPx, loopSpanPx)
  let nearestIndex = 0
  let nearestDistance = Number.POSITIVE_INFINITY

  layouts.forEach((layout, index) => {
    const distance = Math.abs(circularDistance(normalizedX, layout.centerPx, loopSpanPx))
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearestIndex = index
    }
  })

  return nearestIndex
}

function makeCardStates(
  layouts: ShowcaseStripItemLayout[],
  activeIndex: number,
  currentX: number,
  loopSpanPx: number,
  reducedMotion: boolean,
  overscanPx: number,
): ShowcaseCardVisualState[] {
  const normalizedX = normalizeLoopX(currentX, loopSpanPx)

  return layouts.map(layout => {
    const centerDistance = circularDistance(normalizedX, layout.centerPx, loopSpanPx)
    const normalizedProgress = layout.frameWidthPx > 0 ? centerDistance / layout.frameWidthPx : 0
    const distanceFactor = Math.min(Math.abs(normalizedProgress), 2.4)
    const isActive = layout.index === activeIndex

    return {
      index: layout.index,
      captionTranslateX: reducedMotion ? 0 : clamp(-centerDistance * 0.08, -22, 22),
      timeTranslateX: reducedMotion ? 0 : clamp(-centerDistance * 0.05, -16, 16),
      opacity: isActive ? 1 : Math.max(0.58, 1 - distanceFactor * 0.22),
      normalizedProgress,
      isVisible: Math.abs(centerDistance) <= layout.frameWidthPx * 1.8 + overscanPx,
      isActive,
    }
  })
}

export function computeLayerOffsets(input: {
  viewportWidthPx: number
  viewportHeightPx: number
  loopSpanPx: number
  currentX: number
  imageHeightPx: number
  matteHeightPx: number
  maskSpeedMultiplier?: number
}) {
  const maskSpeedMultiplier = input.maskSpeedMultiplier ?? DEFAULT_MASK_SPEED_MULTIPLIER
  const renderCycleFactor = computeRenderCycleFactor(maskSpeedMultiplier)
  const renderRepeatCount = computeRenderRepeatCount(maskSpeedMultiplier)
  const renderBaseOffsetLoops = Math.floor(renderRepeatCount / 2)
  const renderCycleSpanPx = input.loopSpanPx * renderCycleFactor
  const renderBaseOffsetPx = input.loopSpanPx * renderBaseOffsetLoops
  const sharedRenderX = normalizeLoopX(input.currentX, renderCycleSpanPx)

  return {
    backgroundOffsetXPx: 0,
    backgroundOffsetYPx: -input.imageHeightPx / 2,
    foregroundOffsetXPx: 0,
    // The foreground shells use the same frame height as the background strip.
    foregroundOffsetYPx: -input.imageHeightPx / 2,
    backgroundTravelXPx: -(renderBaseOffsetPx + sharedRenderX),
    foregroundTravelXPx: -(renderBaseOffsetPx + sharedRenderX * maskSpeedMultiplier),
  }
}

export function useShowcaseRail(options: UseShowcaseRailOptions): UseShowcaseRailReturn {
  const config = { ...DEFAULT_CONFIG, ...(options.config ?? {}) }
  const viewportRef = ref<HTMLElement | null>(null)
  const railRef = ref<HTMLElement | null>(null)
  const layouts = shallowRef<ShowcaseStripItemLayout[]>([])
  const cardStates = shallowRef<ShowcaseCardVisualState[]>([])
  const activeIndex = ref(0)
  const currentX = ref(0)
  const targetX = ref(0)
  const backgroundOffsetXPx = ref(0)
  const backgroundOffsetYPx = ref(0)
  const foregroundOffsetXPx = ref(0)
  const foregroundOffsetYPx = ref(0)
  const backgroundTravelXPx = ref(0)
  const foregroundTravelXPx = ref(0)
  const viewportWidthPx = ref(0)
  const viewportHeightPx = ref(0)
  const loopSpanPx = ref(DEFAULT_LOOP_SPAN_PX)
  const imageHeightPx = ref(0)
  const matteHeightPx = ref(0)
  const averagePitchPx = ref(0)
  const interactionState = ref<'idle' | 'driving' | 'settling' | 'snapped' | 'suspended'>('idle')
  const activeSource = ref<ShowcaseRailInteractionSource | null>(null)
  const frameId = ref<number | null>(null)
  const lastActiveIndex = ref(0)
  const touchStartX = ref<number | null>(null)
  const touchBaseTargetX = ref(0)
  const isTouchDragging = ref(false)

  function getLoopSpanPx(): number {
    return loopSpanPx.value > 0 ? loopSpanPx.value : DEFAULT_LOOP_SPAN_PX
  }

  function getRenderCycleSpanPx(): number {
    return getLoopSpanPx() * computeRenderCycleFactor(DEFAULT_MASK_SPEED_MULTIPLIER)
  }

  function getNormalizedCurrentX(): number {
    const span = getRenderCycleSpanPx()
    if (!config.loop || span <= 0) return currentX.value
    return normalizeLoopX(currentX.value, span)
  }

  function getNormalizedTargetX(): number {
    const span = getRenderCycleSpanPx()
    if (!config.loop || span <= 0) return targetX.value
    return normalizeLoopX(targetX.value, span)
  }

  function getAnchorX(): number {
    return Number.isFinite(targetX.value) ? targetX.value : currentX.value
  }

  function getAnchorIndex(): number {
    return computeActiveIndex(
      layouts.value,
      getAnchorX(),
      config.activeBiasPx,
      getLoopSpanPx(),
    )
  }

  function resolveLoopedCenterPx(
    index: number,
    anchorX: number,
    directionHint: -1 | 0 | 1,
  ): number | null {
    const targetLayout = layouts.value[index]
    if (!targetLayout) return null

    if (!config.loop) {
      return targetLayout.centerPx
    }

    const span = getLoopSpanPx()
    if (span <= 0) {
      return targetLayout.centerPx
    }

    const nearestLoopIndex = Math.round((anchorX - targetLayout.centerPx) / span)
    let resolvedCenterPx = targetLayout.centerPx + nearestLoopIndex * span

    if (directionHint > 0 && resolvedCenterPx <= anchorX) {
      resolvedCenterPx += span
    }

    if (directionHint < 0 && resolvedCenterPx >= anchorX) {
      resolvedCenterPx -= span
    }

    return resolvedCenterPx
  }

  function rebaseLoopPositions() {
    if (!config.loop) return

    const span = getRenderCycleSpanPx()
    if (span <= 0) return

    const rebaseMultiplier = Math.trunc(currentX.value / span)
    if (rebaseMultiplier === 0) return

    const rebaseOffset = rebaseMultiplier * span
    currentX.value -= rebaseOffset
    targetX.value -= rebaseOffset

    if (touchStartX.value !== null) {
      touchBaseTargetX.value -= rebaseOffset
    }
  }

  function updateLayerOffsets() {
    const offsets = computeLayerOffsets({
      viewportWidthPx: viewportWidthPx.value,
      viewportHeightPx: viewportHeightPx.value,
      loopSpanPx: getLoopSpanPx(),
      currentX: currentX.value,
      imageHeightPx: imageHeightPx.value,
      matteHeightPx: matteHeightPx.value,
    })

    backgroundOffsetXPx.value = offsets.backgroundOffsetXPx
    backgroundOffsetYPx.value = offsets.backgroundOffsetYPx
    foregroundOffsetXPx.value = offsets.foregroundOffsetXPx
    foregroundOffsetYPx.value = offsets.foregroundOffsetYPx
    backgroundTravelXPx.value = offsets.backgroundTravelXPx
    foregroundTravelXPx.value = offsets.foregroundTravelXPx
  }

  function measureGeometry() {
    viewportWidthPx.value = viewportRef.value?.clientWidth ?? 0
    viewportHeightPx.value = viewportRef.value?.clientHeight ?? 0

    const metrics = computeStripLayouts(options.photos.value, viewportHeightPx.value)
    layouts.value = metrics.layouts
    loopSpanPx.value = metrics.loopSpanPx
    imageHeightPx.value = metrics.imageHeightPx
    matteHeightPx.value = metrics.matteHeightPx
    averagePitchPx.value = metrics.averagePitchPx

    updateLayerOffsets()
  }

  function setInteractionState(state: 'idle' | 'driving' | 'settling' | 'snapped' | 'suspended', source: ShowcaseRailInteractionSource | null) {
    interactionState.value = state
    activeSource.value = source
    options.onInteractionStateChange?.({ state, source })
  }

  function syncCardStates(source: ShowcaseRailInteractionSource = 'programmatic') {
    rebaseLoopPositions()
    cardStates.value = makeCardStates(
      layouts.value,
      activeIndex.value,
      currentX.value,
      getLoopSpanPx(),
      options.reducedMotion.value,
      config.overscanPx,
    )
    updateLayerOffsets()

    const activePhotoId = options.photos.value[activeIndex.value]?.photo.id ?? null
    const direction = computeDirection(lastActiveIndex.value, activeIndex.value, options.photos.value.length)
    options.onActiveChange?.({
      activeIndex: activeIndex.value,
      activePhotoId,
      direction,
      source,
      snapshot: getSnapshot(),
    })
    lastActiveIndex.value = activeIndex.value
  }

  function settle(source: ShowcaseRailInteractionSource) {
    currentX.value = targetX.value
    rebaseLoopPositions()
    activeIndex.value = computeActiveIndex(layouts.value, currentX.value, config.activeBiasPx, getLoopSpanPx())
    syncCardStates(source)
    setInteractionState('idle', source)
    options.onSettle?.(getSnapshot())
  }

  function stopTick() {
    if (frameId.value !== null) {
      cancelAnimationFrame(frameId.value)
      frameId.value = null
    }
  }

  function tick() {
    const source = activeSource.value ?? 'programmatic'
    const delta = targetX.value - currentX.value

    if (Math.abs(delta) <= config.snapThresholdPx) {
      stopTick()
      settle(source)
      return
    }

    currentX.value += delta * config.lerp
    rebaseLoopPositions()
    const nextActiveIndex = computeActiveIndex(layouts.value, currentX.value, config.activeBiasPx, getLoopSpanPx())

    if (nextActiveIndex !== activeIndex.value) {
      activeIndex.value = nextActiveIndex
      syncCardStates(source)
    } else {
      cardStates.value = makeCardStates(
        layouts.value,
        activeIndex.value,
        currentX.value,
        getLoopSpanPx(),
        options.reducedMotion.value,
        config.overscanPx,
      )
      updateLayerOffsets()
    }

    setInteractionState('settling', source)
    frameId.value = requestAnimationFrame(() => tick())
  }

  function startTick(source: ShowcaseRailInteractionSource) {
    activeSource.value = source
    if (frameId.value !== null) return
    frameId.value = requestAnimationFrame(() => tick())
  }

  function onWheel(event: WheelEvent) {
    if (!options.photos.value.length) return
    if (interactionState.value === 'suspended') return
    if (event.preventDefault) event.preventDefault()

    const deltaY = Number.isFinite(event.deltaY) ? event.deltaY : 0
    const deltaX = Number.isFinite(event.deltaX) ? event.deltaX : 0
    const dominantDelta = Math.abs(deltaY) >= Math.abs(deltaX) ? deltaY : deltaX
    targetX.value += dominantDelta * config.wheelMultiplier
    rebaseLoopPositions()

    if (options.reducedMotion.value) {
      currentX.value = targetX.value
      activeIndex.value = computeActiveIndex(layouts.value, currentX.value, config.activeBiasPx, getLoopSpanPx())
      settle('wheel')
      return
    }

    setInteractionState('driving', 'wheel')
    startTick('wheel')
  }

  function onTouchStart(event: TouchEvent) {
    if (!options.photos.value.length) return
    if (interactionState.value === 'suspended') return

    const clientX = getTouchClientX(event)
    if (clientX === null) return

    touchStartX.value = clientX
    touchBaseTargetX.value = targetX.value
    isTouchDragging.value = true
    activeSource.value = 'touch'
  }

  function onTouchMove(event: TouchEvent) {
    if (!isTouchDragging.value) return

    const clientX = getTouchClientX(event)
    if (clientX === null || touchStartX.value === null) return

    if (event.preventDefault) event.preventDefault()

    const deltaX = touchStartX.value - clientX
    targetX.value = touchBaseTargetX.value + deltaX * config.touchMultiplier
    rebaseLoopPositions()

    if (options.reducedMotion.value) {
      currentX.value = targetX.value
      activeIndex.value = computeActiveIndex(layouts.value, currentX.value, config.activeBiasPx, getLoopSpanPx())
      settle('touch')
      return
    }

    setInteractionState('driving', 'touch')
    startTick('touch')
  }

  function onTouchEnd(_event: TouchEvent) {
    if (!isTouchDragging.value) return

    isTouchDragging.value = false
    touchStartX.value = null

    if (options.reducedMotion.value) {
      settle('touch')
      return
    }

    if (frameId.value === null) {
      startTick('touch')
    } else {
      setInteractionState('settling', 'touch')
    }
  }

  function moveToResolvedCenter(
    resolvedCenterPx: number,
    nextActiveIndex: number,
    source: ShowcaseRailInteractionSource,
  ) {
    targetX.value = resolvedCenterPx

    if (options.reducedMotion.value) {
      currentX.value = resolvedCenterPx
      activeIndex.value = nextActiveIndex
      settle(source)
      return
    }

    setInteractionState('driving', source)
    startTick(source)
  }

  function jumpToIndex(index: number, source: ShowcaseRailInteractionSource = 'programmatic') {
    const safeLength = layouts.value.length
    if (!safeLength) {
      activeIndex.value = 0
      currentX.value = 0
      targetX.value = 0
      syncCardStates(source)
      return
    }

    const normalizedIndex = config.loop
      ? ((index % safeLength) + safeLength) % safeLength
      : Math.min(Math.max(index, 0), safeLength - 1)
    const directionHint = computeDirection(getAnchorIndex(), normalizedIndex, safeLength)
    const resolvedCenterPx = resolveLoopedCenterPx(normalizedIndex, getAnchorX(), directionHint)
    if (resolvedCenterPx === null) return

    moveToResolvedCenter(resolvedCenterPx, normalizedIndex, source)
  }

  function jumpBy(step: number, source: ShowcaseRailInteractionSource = 'programmatic') {
    const safeLength = layouts.value.length
    if (!safeLength) return

    const anchorIndex = getAnchorIndex()
    const normalizedIndex = config.loop
      ? ((anchorIndex + step) % safeLength + safeLength) % safeLength
      : Math.min(Math.max(anchorIndex + step, 0), safeLength - 1)
    const directionHint = step === 0 ? 0 : step > 0 ? 1 : -1
    const resolvedCenterPx = resolveLoopedCenterPx(normalizedIndex, getAnchorX(), directionHint)
    if (resolvedCenterPx === null) return

    moveToResolvedCenter(resolvedCenterPx, normalizedIndex, source)
  }

  function restoreSnapshot(snapshot: ShowcaseRailSnapshot | null | undefined) {
    if (!snapshot) return
    currentX.value = snapshot.currentX
    targetX.value = snapshot.targetX
    rebaseLoopPositions()
    activeIndex.value = snapshot.activeIndex
    syncCardStates('restore')
  }

  function getSnapshot(): ShowcaseRailSnapshot {
    const activePhotoId = options.photos.value[activeIndex.value]?.photo.id ?? null
    return {
      currentX: getNormalizedCurrentX(),
      targetX: getNormalizedTargetX(),
      activeIndex: activeIndex.value,
      activePhotoId,
      itemPitchPx: averagePitchPx.value,
      loopSpanPx: getLoopSpanPx(),
      timestamp: Date.now(),
    }
  }

  function suspend() {
    stopTick()
    isTouchDragging.value = false
    touchStartX.value = null
    setInteractionState('suspended', activeSource.value)
  }

  function resume() {
    setInteractionState('idle', activeSource.value)
  }

  function recalc() {
    measureGeometry()
    activeIndex.value = computeActiveIndex(layouts.value, currentX.value, config.activeBiasPx, getLoopSpanPx())
    syncCardStates()
  }

  function destroy() {
    stopTick()
  }

  if (options.initialSnapshot.value) {
    restoreSnapshot(options.initialSnapshot.value)
  }

  watch(options.photos, nextPhotos => {
    if (!nextPhotos.length) {
      layouts.value = []
      cardStates.value = []
      activeIndex.value = 0
      currentX.value = 0
      targetX.value = 0
      backgroundOffsetXPx.value = 0
      backgroundOffsetYPx.value = 0
      foregroundOffsetXPx.value = 0
      foregroundOffsetYPx.value = 0
      loopSpanPx.value = DEFAULT_LOOP_SPAN_PX
      imageHeightPx.value = 0
      matteHeightPx.value = 0
      averagePitchPx.value = 0
      return
    }

    measureGeometry()

    if (activeIndex.value > nextPhotos.length - 1) {
      activeIndex.value = nextPhotos.length - 1
    }

    const targetLayout = layouts.value[activeIndex.value]
    if (targetLayout && currentX.value === 0 && targetX.value === 0) {
      currentX.value = targetLayout.centerPx
      targetX.value = targetLayout.centerPx
    }

    activeIndex.value = computeActiveIndex(layouts.value, currentX.value, config.activeBiasPx, getLoopSpanPx())
    syncCardStates()
  }, { immediate: true })

  watch(options.reducedMotion, () => {
    syncCardStates()
  })

  return {
    viewportRef,
    railRef,
    layouts,
    cardStates,
    activeIndex,
    currentX,
    targetX,
    backgroundOffsetXPx,
    backgroundOffsetYPx,
    foregroundOffsetXPx,
    foregroundOffsetYPx,
    backgroundTravelXPx,
    foregroundTravelXPx,
    viewportWidthPx,
    viewportHeightPx,
    loopSpanPx,
    imageHeightPx,
    matteHeightPx,
    interactionState,
    onWheel,
    onTouchStart,
    onTouchMove,
    onTouchEnd,
    jumpToIndex,
    jumpBy,
    restoreSnapshot,
    getSnapshot,
    suspend,
    resume,
    recalc,
    destroy,
  }
}
