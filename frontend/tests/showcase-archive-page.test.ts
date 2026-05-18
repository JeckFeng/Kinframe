import { ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import { useShowcaseArchivePage } from '~/composables/useShowcaseArchivePage'
import { useShowcaseCategoryMemory } from '~/composables/useShowcaseCategoryMemory'
import type { PhotoCategoryDefinition, ShowcasePhotoItem, ShowcaseResponse } from '~/types/api'
import type { ShowcaseRailSnapshot, ShowcaseStageExpose } from '~/types/showcase'

const categories: PhotoCategoryDefinition[] = [
  {
    id: 'cat-life',
    slug: 'life',
    name: 'Life',
    description: null,
    legacy_slug: null,
    sort_order: 1,
    is_active: true,
  },
  {
    id: 'cat-photography',
    slug: 'photography',
    name: 'Photography',
    description: null,
    legacy_slug: null,
    sort_order: 2,
    is_active: true,
  },
  {
    id: 'cat-pet',
    slug: 'pet',
    name: 'Pet',
    description: null,
    legacy_slug: null,
    sort_order: 3,
    is_active: true,
  },
]

function makeShowcasePhotoItem(id: string, category: 'life' | 'photography' | 'pet'): ShowcasePhotoItem {
  return {
    photo: {
      id,
      owner_id: 'owner-1',
      category: category === 'photography' ? 'photography' : category,
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

function makeResponse(category: 'life' | 'photography' | 'pet', ids: string[]): ShowcaseResponse {
  return {
    categories,
    photos: ids.map(id => makeShowcasePhotoItem(id, category)),
  }
}

function makeSnapshot(activeIndex: number, activePhotoId: string): ShowcaseRailSnapshot {
  return {
    currentX: 120,
    targetX: 180,
    activeIndex,
    activePhotoId,
    itemPitchPx: 320,
    loopSpanPx: 1280,
    timestamp: 1715942400000 + activeIndex,
  }
}

function makeKeydownEvent(key: string): KeyboardEvent {
  return {
    key,
    preventDefault: vi.fn(),
    target: document.createElement('div'),
  } as unknown as KeyboardEvent
}

describe('useShowcaseArchivePage', () => {
  it('loads categories, switches by ArrowUp/ArrowDown, and restores saved snapshots per category', async () => {
    const responses = new Map<string, ShowcaseResponse>([
      ['/showcase?category=life', makeResponse('life', ['life-1', 'life-2', 'life-3'])],
      ['/showcase?category=photography', makeResponse('photography', ['photography-1'])],
      ['/showcase?category=pet', makeResponse('pet', ['pet-1', 'pet-2'])],
    ])

    const apiFetch = vi.fn(async <T,>(url: string) => responses.get(url) as T)

    let currentSnapshot = makeSnapshot(2, 'life-3')
    const stageApi: ShowcaseStageExpose = {
      jumpToIndex: vi.fn(),
      jumpBy: vi.fn(),
      restoreSnapshot: vi.fn(),
      getSnapshot: vi.fn(() => currentSnapshot),
      suspend: vi.fn(),
      resume: vi.fn(),
    }

    const page = useShowcaseArchivePage({
      apiFetch,
      stageRef: ref(stageApi),
      memory: useShowcaseCategoryMemory(),
    })

    await page.initialize()
    page.handleStageSettle(currentSnapshot)

    expect(page.activeCategory.value).toBe('life')
    expect(page.photos.value).toHaveLength(3)

    await page.handleKeydown(makeKeydownEvent('ArrowDown'))

    expect(page.activeCategory.value).toBe('photography')
    expect(page.photos.value).toHaveLength(1)
    expect(stageApi.restoreSnapshot).toHaveBeenLastCalledWith(null)
    expect(page.activePhotoIndex.value).toBe(0)

    currentSnapshot = makeSnapshot(0, 'photography-1')
    page.handleStageSettle(currentSnapshot)

    await page.handleKeydown(makeKeydownEvent('ArrowUp'))

    expect(page.activeCategory.value).toBe('life')
    expect(stageApi.restoreSnapshot).toHaveBeenLastCalledWith(makeSnapshot(2, 'life-3'))
    expect(page.activePhotoIndex.value).toBe(2)
    expect(apiFetch).toHaveBeenCalledWith('/showcase?category=life')
    expect(apiFetch).toHaveBeenCalledWith('/showcase?category=photography')
  })

  it('resumes the rail even when category switching cannot resolve the current category index', async () => {
    const responses = new Map<string, ShowcaseResponse>([
      ['/showcase?category=life', makeResponse('life', ['life-1', 'life-2'])],
    ])

    const apiFetch = vi.fn(async <T,>(url: string) => responses.get(url) as T)
    const snapshot = makeSnapshot(1, 'life-2')
    const stageApi: ShowcaseStageExpose = {
      jumpToIndex: vi.fn(),
      jumpBy: vi.fn(),
      restoreSnapshot: vi.fn(),
      getSnapshot: vi.fn(() => snapshot),
      suspend: vi.fn(),
      resume: vi.fn(),
    }

    const page = useShowcaseArchivePage({
      apiFetch,
      stageRef: ref(stageApi),
      memory: useShowcaseCategoryMemory(),
    })

    await page.initialize()
    vi.mocked(stageApi.restoreSnapshot).mockClear()
    vi.mocked(stageApi.suspend).mockClear()
    vi.mocked(stageApi.resume).mockClear()
    page.categories.value = [categories[1], categories[2]].filter(Boolean) as PhotoCategoryDefinition[]

    await page.switchCategory(1)

    expect(stageApi.suspend).toHaveBeenCalledTimes(1)
    expect(stageApi.resume).toHaveBeenCalledTimes(1)
    expect(stageApi.restoreSnapshot).not.toHaveBeenCalled()
  })
})
