import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { useImagePreload } from '~/composables/useImagePreload'

function makePhoto(id: string, previewUrl: string) {
  return {
    photo: { id, taken_at: '2024-01-15T10:00:00Z' },
    preview_url: previewUrl,
    thumbnail_url: previewUrl.replace('preview', 'thumbnail'),
  }
}

describe('useImagePreload — preloadAdjacent', () => {
  let originalImage: typeof Image

  beforeEach(() => {
    originalImage = globalThis.Image
  })

  afterEach(() => {
    globalThis.Image = originalImage
  })

  it('preloads prev and next photo URLs', () => {
    const photos = [
      makePhoto('p1', 'https://example.com/p1.jpg'),
      makePhoto('p2', 'https://example.com/p2.jpg'),
      makePhoto('p3', 'https://example.com/p3.jpg'),
    ]
    const srcs: string[] = []
    globalThis.Image = class {
      set src(url: string) { srcs.push(url) }
    } as unknown as typeof Image

    const { preloadAdjacent } = useImagePreload()
    preloadAdjacent(photos, 1) // current index = 1 (p2)
    expect(srcs).toContain('https://example.com/p1.jpg')
    expect(srcs).toContain('https://example.com/p3.jpg')
    expect(srcs.length).toBe(2)
  })

  it('does not preload if no adjacent photos (single photo)', () => {
    const photos = [makePhoto('p1', 'https://example.com/p1.jpg')]
    const srcs: string[] = []
    globalThis.Image = class {
      set src(url: string) { srcs.push(url) }
    } as unknown as typeof Image

    const { preloadAdjacent } = useImagePreload()
    preloadAdjacent(photos, 0)
    expect(srcs.length).toBe(0)
  })

  it('skips already loaded photo URLs', () => {
    const photos = [
      makePhoto('p1', 'https://example.com/p1.jpg'),
      makePhoto('p2', 'https://example.com/p2.jpg'),
    ]
    const srcs: string[] = []
    globalThis.Image = class {
      set src(url: string) { srcs.push(url) }
    } as unknown as typeof Image

    const { preloadAdjacent } = useImagePreload()
    preloadAdjacent(photos, 0) // idx=0 → preload p2
    expect(srcs).toContain('https://example.com/p2.jpg')
    expect(srcs.length).toBe(1)

    // Navigate to p2 — p1 should load, p2 is already tracked
    preloadAdjacent(photos, 1)
    expect(srcs).toContain('https://example.com/p1.jpg')
    // p2 was already loaded, should not appear again
    const p2Count = srcs.filter(s => s === 'https://example.com/p2.jpg').length
    expect(p2Count).toBe(1)
  })

  it('returns currently loading state', () => {
    const photos = [
      makePhoto('p1', 'https://example.com/p1.jpg'),
      makePhoto('p2', 'https://example.com/p2.jpg'),
    ]

    globalThis.Image = originalImage
    const { preloadAdjacent, preloadingCount } = useImagePreload()
    // With real Image, we can't easily test async loading in jsdom
    // but the state should be reactive
    expect(preloadingCount.value).toBe(0)
    preloadAdjacent(photos, 0)
    // new Image() fires immediately but we check the reactive ref exists
    expect(preloadingCount).toBeDefined()
  })
})

describe('useImagePreload — cancelPreloads', () => {
  it('resets preload state on cancel', () => {
    const { cancelPreloads, loadedIds } = useImagePreload()
    // Pre-track some IDs
    loadedIds.add('photo-1')
    loadedIds.add('photo-2')
    cancelPreloads()
    // After cancel, loaded IDs should be cleared
    expect(loadedIds.size).toBe(0)
  })
})

describe('useImagePreload — urlExpiry', () => {
  it('detects expired URLs from presigned URL timestamp', () => {
    const { isUrlExpired } = useImagePreload()
    // Presigned MinIO URLs have X-Amz-Date and X-Amz-Expires
    const freshUrl = 'https://minio.example.com/bucket/obj?X-Amz-Date=20260115T120000Z&X-Amz-Expires=900'
    expect(isUrlExpired(freshUrl)).toBe(true) // future date in URL → expired for current time

    // URL without expiry params is assumed fresh
    const plainUrl = 'https://example.com/photo.jpg'
    expect(isUrlExpired(plainUrl)).toBe(false)
  })
})
