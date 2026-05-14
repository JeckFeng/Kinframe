import { reactive, ref } from 'vue'

export function useImagePreload() {
  const loadedIds = reactive(new Set<string>())
  const preloadingCount = ref(0)

  function isUrlExpired(url: string): boolean {
    try {
      const u = new URL(url)
      const amzDate = u.searchParams.get('X-Amz-Date')
      const amzExpires = u.searchParams.get('X-Amz-Expires')
      if (!amzDate || !amzExpires) return false
      // Parse X-Amz-Date: 20260115T120000Z
      const match = amzDate.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/)
      if (!match) return false
      const signTime = Date.UTC(
        Number(match[1]), Number(match[2]) - 1, Number(match[3]),
        Number(match[4]), Number(match[5]), Number(match[6]),
      )
      const expiresSec = Number(amzExpires) || 900
      const expireTime = signTime + expiresSec * 1000
      return Date.now() > expireTime
    } catch {
      return false
    }
  }

  function preloadAdjacent(
    photos: Array<{ preview_url?: string }>,
    currentIndex: number,
  ) {
    const urls: string[] = []
    const prev = photos[currentIndex - 1]
    const next = photos[currentIndex + 1]
    if (prev?.preview_url && !loadedIds.has(prev.preview_url) && !isUrlExpired(prev.preview_url)) {
      urls.push(prev.preview_url)
    }
    if (next?.preview_url && !loadedIds.has(next.preview_url) && !isUrlExpired(next.preview_url)) {
      urls.push(next.preview_url)
    }
    if (urls.length === 0) return

    preloadingCount.value += urls.length
    for (const url of urls) {
      const img = new Image()
      img.onload = () => {
        loadedIds.add(url)
        preloadingCount.value = Math.max(0, preloadingCount.value - 1)
      }
      img.onerror = () => {
        preloadingCount.value = Math.max(0, preloadingCount.value - 1)
      }
      img.src = url
    }
  }

  function cancelPreloads() {
    loadedIds.clear()
    preloadingCount.value = 0
  }

  return {
    loadedIds,
    preloadingCount,
    preloadAdjacent,
    cancelPreloads,
    isUrlExpired,
  }
}
