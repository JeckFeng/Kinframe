<script setup lang="ts">
import type { MapPhotoItem, MapPhotosResponse, PhotoCategoryDefinition } from '~/types/api'

const { apiFetch } = useApi()
const { currentUser, loadMe } = useAuth()

const categories = ref<PhotoCategoryDefinition[]>([])
const photos = ref<MapPhotoItem[]>([])
const activeCategory = ref<string | null>(null)
const pending = ref(true)
const errorMessage = ref('')

const mapContainer = ref<HTMLElement | null>(null)
let L: typeof import('leaflet').default | null = null
let mapInstance: import('leaflet').Map | null = null
let markersLayer: import('leaflet').LayerGroup | null = null

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function buildLocationText(photo: MapPhotoItem): string {
  return [photo.location_city, photo.location_region]
    .filter(Boolean)
    .join(', ') || photo.location_name || ''
}

function formatCnDate(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function popupContent(photo: MapPhotoItem): string {
  const location = buildLocationText(photo)
  const date = formatCnDate(photo.taken_at)
  const caption = photo.final_caption ? `<p class="text-sm text-stone-800 mb-1">${escapeHtml(photo.final_caption)}</p>` : ''
  const locHtml = location ? `<p class="text-xs text-stone-500 mb-1">📍 ${escapeHtml(location)}</p>` : ''
  const dateHtml = date ? `<p class="text-xs text-stone-400 mb-2">${date}</p>` : ''
  return `
    <div class="kf-map-popup">
      <img src="${photo.thumbnail_url}" alt="" class="w-full h-32 object-cover rounded-lg mb-2" loading="lazy" />
      ${caption}
      ${locHtml}
      ${dateHtml}
      <a href="/photo/${photo.photo_id}" class="text-xs text-amber-700 hover:text-amber-900 font-medium">查看照片 →</a>
    </div>
  `
}

function addMarkers() {
  if (!markersLayer || !L) return
  markersLayer.clearLayers()

  for (const photo of photos.value) {
    const icon = L.divIcon({
      className: 'kf-map-marker',
      html: `
        <div class="w-10 h-10 rounded-full border-2 border-white/80 shadow-lg overflow-hidden"
             style="background-image: url(${photo.thumbnail_url}); background-size: cover; background-position: center">
        </div>
      `,
      iconSize: [40, 40],
      iconAnchor: [20, 20],
    })

    const marker = L.marker([photo.gps_lat, photo.gps_lng], { icon })
      .bindPopup(popupContent(photo), { maxWidth: 280, closeButton: true })

    marker.addTo(markersLayer!)
  }

  if (photos.value.length > 0 && mapInstance) {
    const group = L.featureGroup(markersLayer!.getLayers() as L.Layer[])
    const bounds = group.getBounds()
    if (bounds.isValid()) {
      mapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 })
    }
  }
}

async function fetchPhotos() {
  pending.value = true
  errorMessage.value = ''
  try {
    const data = await apiFetch<MapPhotosResponse>('/api/map/photos', {
      query: activeCategory.value ? { category: activeCategory.value } : undefined,
    })
    photos.value = data.photos
    if (!data.categories) {
      // Categories come from the category list endpoint if available
    }
    // Use existing categories if already loaded
    if (categories.value.length === 0) {
      categories.value = [
        { id: '1', slug: 'life', name: '生活', description: null, legacy_slug: null, sort_order: 1, is_active: true },
        { id: '2', slug: 'photography', name: '摄影', description: null, legacy_slug: null, sort_order: 2, is_active: true },
        { id: '3', slug: 'pet', name: '萌宠', description: null, legacy_slug: null, sort_order: 3, is_active: true },
      ]
    }
    nextTick(() => addMarkers())
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

async function filterBy(categorySlug: string | null) {
  activeCategory.value = categorySlug
  await fetchPhotos()
}

if (!currentUser.value) { await loadMe() }
if (!currentUser.value) {
  await navigateTo('/login')
} else {
  await fetchPhotos()
}

onMounted(() => {
  import('leaflet').then((module) => {
    L = module.default
    if (!mapContainer.value) return

    mapInstance = L.map(mapContainer.value, {
      center: [35.86, 104.19],
      zoom: 5,
      zoomControl: true,
      attributionControl: false,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
    }).addTo(mapInstance)

    markersLayer = L.layerGroup().addTo(mapInstance)
    addMarkers()
  })
})

onBeforeUnmount(() => {
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
})
</script>

<template>
  <ClientOnly>
    <div class="fixed inset-0 bg-neutral-950">
      <!-- "返回放映" link -->
      <NuxtLink
        to="/showcase"
        class="absolute top-4 left-4 z-[1000] inline-flex items-center gap-1 rounded-lg bg-neutral-950/60 backdrop-blur-md border border-white/10 px-3 py-2 text-sm text-white/80 hover:text-white transition-colors shadow-lg"
      >
        ← 返回放映
      </NuxtLink>

      <!-- Category filter bar -->
      <div class="absolute top-0 inset-x-0 z-[1000] pointer-events-none">
        <div class="flex justify-center p-4">
          <div
            class="pointer-events-auto flex gap-2 overflow-x-auto rounded-full bg-neutral-950/60 backdrop-blur-md border border-white/10 px-2 py-1.5 shadow-lg"
          >
            <button
              type="button"
              @click="filterBy(null)"
              :class="activeCategory === null ? 'bg-white text-stone-900' : 'bg-white/10 text-white/70'"
              class="px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-colors"
            >
              全部
            </button>
            <button
              v-for="cat in categories"
              :key="cat.slug"
              type="button"
              @click="filterBy(cat.slug)"
              :class="activeCategory === cat.slug ? 'bg-white text-stone-900' : 'bg-white/10 text-white/70'"
              class="px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-colors"
            >
              {{ cat.name }}
            </button>
          </div>
        </div>
      </div>

      <!-- Map container -->
      <div ref="mapContainer" class="w-full h-full" />

      <!-- Loading state -->
      <div
        v-if="pending"
        class="absolute inset-0 flex items-center justify-center z-[1000] pointer-events-none"
      >
        <p class="text-sm text-white/70 bg-neutral-950/60 backdrop-blur-md rounded-lg px-4 py-2">
          加载中...
        </p>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="photos.length === 0"
        class="absolute inset-0 flex items-center justify-center z-[1000] pointer-events-none"
      >
        <p class="text-sm text-white/70 bg-neutral-950/60 backdrop-blur-md rounded-lg px-4 py-2">
          暂无位置数据
        </p>
      </div>

      <!-- Error state -->
      <div
        v-if="errorMessage"
        class="absolute bottom-8 inset-x-0 flex justify-center z-[1000]"
      >
        <p class="max-w-md rounded-md border border-red-300/40 bg-red-950/60 px-4 py-3 text-sm text-red-50">
          {{ errorMessage }}
        </p>
      </div>
    </div>

    <!-- Fallback while Leaflet loads on client -->
    <template #fallback>
      <div class="fixed inset-0 bg-neutral-950 flex items-center justify-center">
        <p class="text-sm text-white/50">加载地图...</p>
      </div>
    </template>
  </ClientOnly>
</template>

<style>
@import 'leaflet/dist/leaflet.css';

.kf-map-marker {
  background: transparent !important;
  border: none !important;
}

.kf-map-popup img {
  max-width: 100%;
}
</style>
