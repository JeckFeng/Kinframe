import { ref } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { computeLayerOffsets, computeStripLayouts, useShowcaseRail } from '~/composables/useShowcaseRail'
import type { ShowcasePhotoItem } from '~/types/api'

function makeShowcasePhotoItem(id: string): ShowcasePhotoItem {
  return {
    photo: {
      id,
      owner_id: 'owner-1',
      category: 'life',
      category_source: 'manual',
      caption_source: 'manual',
      user_message: `Message ${id}`,
      final_caption: `Caption ${id}`,
      include_in_showcase: true,
      time_source: 'exif',
      bucket: 'photos',
      object_key_original: `original/${id}.jpg`,
      object_key_thumbnail: `thumbnail/${id}.jpg`,
      object_key_preview: `preview/${id}.jpg`,
      mime_type: 'image/jpeg',
      file_size: 1024,
      sha256: `sha-${id}`,
      width: 1200,
      height: 1600,
      taken_at: '2026-05-17T10:00:00Z',
      uploaded_at: '2026-05-17T10:00:00Z',
      gps_lat: null,
      gps_lng: null,
      camera_make: null,
      camera_model: null,
      location_name: 'Bund',
      location_country: 'China',
      location_region: 'Shanghai',
      location_city: 'Shanghai',
      location_district: null,
      location_road: null,
      geocoding_status: 'resolved',
      geocoding_provider: null,
      geocoded_at: null,
      status: 'ready',
      processing_message: null,
      created_at: '2026-05-17T10:00:00Z',
      updated_at: '2026-05-17T10:00:00Z',
    },
    preview_url: `https://example.com/${id}/preview.jpg`,
    thumbnail_url: `https://example.com/${id}/thumb.jpg`,
    slide_design: null,
  }
}

describe('useShowcaseRail', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('jumps to a requested index and reports the active photo in its snapshot', () => {
    const onActiveChange = vi.fn()
    const onSettle = vi.fn()
    const photos = ref([
      makeShowcasePhotoItem('photo-1'),
      makeShowcasePhotoItem('photo-2'),
      makeShowcasePhotoItem('photo-3'),
    ])

    const rail = useShowcaseRail({
      photos,
      reducedMotion: ref(true),
      initialSnapshot: ref(null),
      onActiveChange,
      onSettle,
    })

    rail.jumpToIndex(2, 'thumb')

    expect(rail.activeIndex.value).toBe(2)
    expect(rail.getSnapshot().activePhotoId).toBe('photo-3')
    expect(onActiveChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        activeIndex: 2,
        activePhotoId: 'photo-3',
        source: 'thumb',
      }),
    )
    expect(onSettle).toHaveBeenCalled()
  })

  it('recomputes visual states and layouts when the bound photo list changes', async () => {
    const photos = ref([
      makeShowcasePhotoItem('photo-1'),
      makeShowcasePhotoItem('photo-2'),
    ])

    const rail = useShowcaseRail({
      photos,
      reducedMotion: ref(false),
      initialSnapshot: ref(null),
    })

    expect(rail.cardStates.value).toHaveLength(2)
    expect(rail.layouts.value).toHaveLength(2)

    photos.value = [
      makeShowcasePhotoItem('photo-3'),
      makeShowcasePhotoItem('photo-4'),
      makeShowcasePhotoItem('photo-5'),
    ]

    await Promise.resolve()

    expect(rail.cardStates.value).toHaveLength(3)
    expect(rail.layouts.value).toHaveLength(3)
    expect(rail.activeIndex.value).toBe(0)
    expect(rail.getSnapshot().activePhotoId).toBe('photo-3')
  })

  it('advances to the next centered photo after wheel-driven inertial scrolling settles', () => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      return setTimeout(() => callback(Date.now()), 16) as unknown as number
    })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => {
      clearTimeout(id)
    })

    const onActiveChange = vi.fn()
    const onSettle = vi.fn()
    const photos = ref([
      makeShowcasePhotoItem('photo-1'),
      makeShowcasePhotoItem('photo-2'),
      makeShowcasePhotoItem('photo-3'),
    ])

    const rail = useShowcaseRail({
      photos,
      reducedMotion: ref(false),
      initialSnapshot: ref(null),
      config: {
        lerp: 0.35,
        snapThresholdPx: 0.5,
        wheelMultiplier: 1,
      },
      onActiveChange,
      onSettle,
    })

    rail.onWheel({ deltaY: 320 } as WheelEvent)
    vi.advanceTimersByTime(1500)

    expect(rail.activeIndex.value).toBe(1)
    expect(rail.getSnapshot().activePhotoId).toBe('photo-2')
    expect(onActiveChange).toHaveBeenCalledWith(
      expect.objectContaining({
        activeIndex: 1,
        activePhotoId: 'photo-2',
        source: 'wheel',
      }),
    )
    expect(onSettle).toHaveBeenCalled()
  })

  it('advances to the next centered photo after touch dragging settles', () => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      return setTimeout(() => callback(Date.now()), 16) as unknown as number
    })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => {
      clearTimeout(id)
    })

    const onActiveChange = vi.fn()
    const onSettle = vi.fn()
    const photos = ref([
      makeShowcasePhotoItem('photo-1'),
      makeShowcasePhotoItem('photo-2'),
      makeShowcasePhotoItem('photo-3'),
    ])

    const rail = useShowcaseRail({
      photos,
      reducedMotion: ref(false),
      initialSnapshot: ref(null),
      config: {
        lerp: 0.35,
        snapThresholdPx: 0.5,
        touchMultiplier: 1,
      },
      onActiveChange,
      onSettle,
    })

    rail.onTouchStart({ touches: [{ clientX: 320 }] } as unknown as TouchEvent)
    rail.onTouchMove({
      touches: [{ clientX: 0 }],
      preventDefault: vi.fn(),
    } as unknown as TouchEvent)
    rail.onTouchEnd({ changedTouches: [{ clientX: 0 }] } as unknown as TouchEvent)
    vi.advanceTimersByTime(1500)

    expect(rail.activeIndex.value).toBe(1)
    expect(rail.getSnapshot().activePhotoId).toBe('photo-2')
    expect(onActiveChange).toHaveBeenCalledWith(
      expect.objectContaining({
        activeIndex: 1,
        activePhotoId: 'photo-2',
        source: 'touch',
      }),
    )
    expect(onSettle).toHaveBeenCalled()
  })

  it('wraps to the first logical photo on the next physical copy when jumpBy advances beyond the final slot in loop mode', () => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      return setTimeout(() => callback(Date.now()), 16) as unknown as number
    })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => {
      clearTimeout(id)
    })

    const onActiveChange = vi.fn()
    const photos = ref([
      makeShowcasePhotoItem('photo-1'),
      makeShowcasePhotoItem('photo-2'),
      makeShowcasePhotoItem('photo-3'),
    ])

    const rail = useShowcaseRail({
      photos,
      reducedMotion: ref(false),
      initialSnapshot: ref(null),
      onActiveChange,
    })

    const loopSpanPx = rail.getSnapshot().loopSpanPx
    const lastLayout = rail.layouts.value[2]
    expect(lastLayout).toBeDefined()

    rail.restoreSnapshot({
      currentX: lastLayout?.centerPx ?? 0,
      targetX: lastLayout?.centerPx ?? 0,
      activeIndex: 2,
      activePhotoId: 'photo-3',
      itemPitchPx: rail.getSnapshot().itemPitchPx,
      loopSpanPx,
      timestamp: Date.now(),
    })
    rail.jumpBy(1, 'keyboard')
    expect(rail.targetX.value).toBeGreaterThan(loopSpanPx)
    vi.advanceTimersByTime(1500)

    expect(rail.activeIndex.value).toBe(0)
    expect(rail.getSnapshot().activePhotoId).toBe('photo-1')
    expect(rail.currentX.value).toBeGreaterThan(loopSpanPx)
    expect(onActiveChange).toHaveBeenCalledWith(
      expect.objectContaining({
        activeIndex: 0,
        activePhotoId: 'photo-1',
        direction: 1,
        source: 'keyboard',
      }),
    )
  })

  it('continues from the in-flight target when jumpBy is triggered repeatedly before the previous animation settles', () => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      return setTimeout(() => callback(Date.now()), 16) as unknown as number
    })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => {
      clearTimeout(id)
    })

    const photos = ref([
      makeShowcasePhotoItem('photo-1'),
      makeShowcasePhotoItem('photo-2'),
      makeShowcasePhotoItem('photo-3'),
    ])

    const rail = useShowcaseRail({
      photos,
      reducedMotion: ref(false),
      initialSnapshot: ref(null),
    })

    const loopSpanPx = rail.getSnapshot().loopSpanPx
    const lastLayout = rail.layouts.value[2]
    expect(lastLayout).toBeDefined()

    rail.restoreSnapshot({
      currentX: lastLayout?.centerPx ?? 0,
      targetX: lastLayout?.centerPx ?? 0,
      activeIndex: 2,
      activePhotoId: 'photo-3',
      itemPitchPx: rail.getSnapshot().itemPitchPx,
      loopSpanPx,
      timestamp: Date.now(),
    })

    rail.jumpBy(1, 'keyboard')
    rail.jumpBy(1, 'keyboard')
    vi.advanceTimersByTime(1500)

    expect(rail.activeIndex.value).toBe(1)
    expect(rail.getSnapshot().activePhotoId).toBe('photo-2')
    expect(rail.currentX.value).toBeGreaterThan(loopSpanPx)
  })

  it('builds seamless strip layouts from the source photo aspect ratios', () => {
    const portrait = makeShowcasePhotoItem('portrait')
    const wide = makeShowcasePhotoItem('wide')
    wide.photo.width = 1920
    wide.photo.height = 1080

    const metrics = computeStripLayouts([portrait, wide], 900)

    expect(metrics.layouts).toHaveLength(2)
    expect(metrics.layouts[0]?.frameWidthPx).toBe(metrics.layouts[1]?.frameWidthPx)
    expect(metrics.layouts[0]?.startPx).toBe(0)
    expect(metrics.layouts[1]?.startPx).toBe(metrics.layouts[0]?.frameWidthPx)
    expect(metrics.loopSpanPx).toBe(
      (metrics.layouts[0]?.frameWidthPx ?? 0) + (metrics.layouts[1]?.frameWidthPx ?? 0),
    )
  })

  it('anchors both strips on the viewport centerline and only offsets each track by half its own height', () => {
    expect(computeLayerOffsets({
      viewportWidthPx: 1200,
      viewportHeightPx: 900,
      loopSpanPx: 720,
      currentX: 240,
      imageHeightPx: 320,
      matteHeightPx: 420,
    })).toEqual({
      backgroundOffsetXPx: 0,
      backgroundOffsetYPx: -160,
      foregroundOffsetXPx: 0,
      foregroundOffsetYPx: -160,
      backgroundTravelXPx: -2400,
      foregroundTravelXPx: -2520,
    })
  })

  it('keeps the continuous strip position beyond one loop when wheel scrolling wraps past the final photo', () => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      return setTimeout(() => callback(Date.now()), 16) as unknown as number
    })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => {
      clearTimeout(id)
    })

    const photos = ref([
      makeShowcasePhotoItem('photo-1'),
      makeShowcasePhotoItem('photo-2'),
      makeShowcasePhotoItem('photo-3'),
    ])

    const rail = useShowcaseRail({
      photos,
      reducedMotion: ref(false),
      initialSnapshot: ref(null),
      config: {
        lerp: 0.35,
        snapThresholdPx: 0.5,
        wheelMultiplier: 1,
      },
    })

    const loopSpanPx = rail.getSnapshot().loopSpanPx
    const lastLayout = rail.layouts.value[2]
    expect(lastLayout).toBeDefined()

    rail.restoreSnapshot({
      currentX: lastLayout?.centerPx ?? 0,
      targetX: lastLayout?.centerPx ?? 0,
      activeIndex: 2,
      activePhotoId: 'photo-3',
      itemPitchPx: rail.getSnapshot().itemPitchPx,
      loopSpanPx,
      timestamp: Date.now(),
    })
    rail.onWheel({ deltaY: 240 } as WheelEvent)
    vi.advanceTimersByTime(1500)

    expect(rail.activeIndex.value).toBe(0)
    expect(rail.currentX.value).toBeGreaterThan(loopSpanPx)
    expect(rail.targetX.value).toBeGreaterThan(loopSpanPx)
  })

  it('re-centers the rendered strip transforms after wheel scrolling passes one full loop so the first photo stays visually reachable', () => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      return setTimeout(() => callback(Date.now()), 16) as unknown as number
    })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => {
      clearTimeout(id)
    })

    const photos = ref([
      makeShowcasePhotoItem('photo-1'),
      makeShowcasePhotoItem('photo-2'),
      makeShowcasePhotoItem('photo-3'),
    ])

    const rail = useShowcaseRail({
      photos,
      reducedMotion: ref(false),
      initialSnapshot: ref(null),
      config: {
        lerp: 0.35,
        snapThresholdPx: 0.5,
        wheelMultiplier: 1,
      },
    })

    const loopSpanPx = rail.getSnapshot().loopSpanPx
    const lastLayout = rail.layouts.value[2]
    expect(lastLayout).toBeDefined()

    rail.restoreSnapshot({
      currentX: lastLayout?.centerPx ?? 0,
      targetX: lastLayout?.centerPx ?? 0,
      activeIndex: 2,
      activePhotoId: 'photo-3',
      itemPitchPx: rail.getSnapshot().itemPitchPx,
      loopSpanPx,
      timestamp: Date.now(),
    })
    rail.onWheel({ deltaY: 240 } as WheelEvent)
    vi.advanceTimersByTime(1500)

    expect(rail.activeIndex.value).toBe(0)
    expect(rail.currentX.value).toBeGreaterThan(loopSpanPx)
    expect(Math.abs(rail.backgroundTravelXPx.value)).toBeLessThanOrEqual(loopSpanPx * 5)
    expect(Math.abs(rail.foregroundTravelXPx.value)).toBeLessThanOrEqual(loopSpanPx * 6)
  })

  it('re-bases positions after many loop spans so scrolling can continue indefinitely without growing unbounded', () => {
    const photos = ref([
      makeShowcasePhotoItem('photo-1'),
      makeShowcasePhotoItem('photo-2'),
      makeShowcasePhotoItem('photo-3'),
    ])

    const rail = useShowcaseRail({
      photos,
      reducedMotion: ref(true),
      initialSnapshot: ref(null),
      config: {
        wheelMultiplier: 1,
      },
    })

    const loopSpanPx = rail.getSnapshot().loopSpanPx
    rail.onWheel({ deltaY: loopSpanPx * 9 + 240 } as WheelEvent)

    expect(rail.currentX.value).toBeGreaterThanOrEqual(0)
    expect(rail.currentX.value).toBeLessThan(loopSpanPx * 2)
    expect(rail.targetX.value).toBeGreaterThanOrEqual(0)
    expect(rail.targetX.value).toBeLessThan(loopSpanPx * 2)
    expect(Math.abs(rail.backgroundTravelXPx.value)).toBeLessThanOrEqual(loopSpanPx * 5)
    expect(Math.abs(rail.foregroundTravelXPx.value)).toBeLessThanOrEqual(loopSpanPx * 6)
  })
})
