<script setup lang="ts">
import { Edit3, ExternalLink, Loader2, RefreshCw, RotateCcw, Save } from 'lucide-vue-next'
import type { AdminPhoto, Photo, PhotoCategory, PhotoProcessingStatusResponse, PresignedUrlResponse } from '~/types/api'

const route = useRoute()
const { apiFetch } = useApi()
const { formatBytes, formatDate } = useFormat()
const { displayCategory } = usePhotoCategories()
const { currentUser, loadMe } = useAuth()

const isAdmin = computed(() => currentUser.value?.role === 'admin')
const isOwner = computed(() => currentUser.value?.id === photo.value?.owner_id)
const canManageShowcaseVisibility = computed(() => isOwner.value || isAdmin.value)

const photo = ref<Photo | null>(null)
const adminPhoto = ref<AdminPhoto | null>(null)
const processingStatus = ref<PhotoProcessingStatusResponse | null>(null)
const imageUrl = ref('')
const category = ref<PhotoCategory>('life')
const userMessage = ref('')
const pending = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

// Admin fields
const adminFinalCaption = ref('')
const adminLocationName = ref('')
const adminLocationCity = ref('')
const adminLocationCountry = ref('')
const adminLocationRegion = ref('')
const adminLocationDistrict = ref('')
const adminLocationRoad = ref('')
const adminSaving = ref(false)
const adminRegenerating = ref(false)
const adminResettingCaption = ref(false)
const manualDesignJson = ref('')
const manualDesignSaving = ref(false)
const activatingDesignId = ref<string | null>(null)
type RegenerateScope = 'caption' | 'template' | 'css_tokens' | 'full' | 'fallback'
const regenScope = ref<RegenerateScope>('full')

const editingMessage = ref(false)
const messageSaving = ref(false)
const showcaseSaving = ref(false)

let processingPollTimer: ReturnType<typeof setInterval> | null = null

const STATUS_LABELS: Record<string, string> = {
  uploaded: '已上传',
  processing: '正在解析照片信息…',
  exif_parsed: '已解析拍摄信息',
  preview_generated: '正在生成预览…',
  vision_analyzed: 'AI 分析已完成',
  design_generated: '正在生成幻灯片设计…',
  ready: '已完成 ✓',
  failed: '处理失败',
}
const ADMIN_JOB_TYPE_LABELS: Record<string, string> = {
  photo_ingest: 'Photo Ingest',
  reverse_geocode: 'Reverse Geocode',
  vision_analyze: 'Vision Analyze',
  slide_design_generate: 'Slide Design',
  caption_regenerate: 'Caption Regenerate',
  template_regenerate: 'Template Regenerate',
  css_regenerate: 'CSS Regenerate',
  fallback_regenerate: 'Fallback Regenerate',
}
const DESIGN_SOURCE_LABELS: Record<string, string> = {
  fallback: 'Fallback',
  ai: 'AI',
  manual: 'Manual',
}
const AI_STATUS_LABELS: Record<string, string> = {
  analyzed: 'Analyzed',
  failed: 'Failed',
  missing: 'Missing',
}

function formatStatus(status: string): string {
  return STATUS_LABELS[status] || status
}

function formatAdminJobType(type: string): string {
  return ADMIN_JOB_TYPE_LABELS[type] || type
}

function syncManualDesignEditor(force = false) {
  if (!adminPhoto.value?.design_versions.length) return
  if (manualDesignJson.value && !force) return
  const preferredDesign = adminPhoto.value.design_versions.find((design) => design.status === 'active') || adminPhoto.value.design_versions[0]
  manualDesignJson.value = preferredDesign.design_json ? JSON.stringify(preferredDesign.design_json, null, 2) : ''
}

function isInProgressStatus(status: string) {
  return !['ready', 'failed'].includes(status)
}

function hasActiveJob(status: PhotoProcessingStatusResponse | null) {
  return status?.job_status === 'pending' || status?.job_status === 'running'
}

function stopProcessingPoll() {
  if (processingPollTimer) {
    clearInterval(processingPollTimer)
    processingPollTimer = null
  }
}

async function refreshProcessingStatus() {
  if (!photo.value) return
  const status = await apiFetch<PhotoProcessingStatusResponse>(`/photos/${photo.value.id}/processing-status`)
  processingStatus.value = status
  if (!isInProgressStatus(status.photo_status) && !hasActiveJob(status)) {
    stopProcessingPoll()
    await loadPhoto(false)
  }
}

function startProcessingPoll() {
  if (processingPollTimer) return
  processingPollTimer = setInterval(() => {
    refreshProcessingStatus().catch(() => stopProcessingPoll())
  }, 2000)
}

async function loadPhoto(enablePolling = true) {
  pending.value = true
  errorMessage.value = ''
  try {
    const id = String(route.params.id)
    photo.value = await apiFetch<Photo>(`/photos/${id}`)
    category.value = photo.value.category === 'travel' ? 'photography' : photo.value.category as PhotoCategory
    userMessage.value = photo.value.user_message || ''
    processingStatus.value = null

    const response = await apiFetch<PresignedUrlResponse>(`/photos/${id}/original-url`)
    imageUrl.value = response.url

    if (isAdmin.value) {
      await loadAdminPhoto(id)
    }

    if (enablePolling && isInProgressStatus(photo.value.status)) {
      await refreshProcessingStatus()
      if (photo.value && isInProgressStatus(photo.value.status)) {
        startProcessingPoll()
      }
    } else if (!isInProgressStatus(photo.value.status)) {
      stopProcessingPoll()
    }
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

async function loadAdminPhoto(id: string) {
  try {
    adminPhoto.value = await apiFetch<AdminPhoto>(`/admin/photos/${id}`)
    adminFinalCaption.value = adminPhoto.value.final_caption || ''
    adminLocationName.value = adminPhoto.value.location_name || ''
    adminLocationCity.value = adminPhoto.value.location_city || ''
    adminLocationCountry.value = adminPhoto.value.location_country || ''
    adminLocationRegion.value = adminPhoto.value.location_region || ''
    adminLocationDistrict.value = adminPhoto.value.location_district || ''
    adminLocationRoad.value = adminPhoto.value.location_road || ''
    syncManualDesignEditor(true)
  } catch {
    // Admin data not critical
  }
}

async function savePhoto() {
  if (!photo.value) return
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    photo.value = await apiFetch<Photo>(`/photos/${photo.value.id}`, {
      method: 'PATCH',
      body: { category: category.value, user_message: userMessage.value },
    })
    successMessage.value = 'Saved'
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    saving.value = false
  }
}

async function saveMessage() {
  if (!photo.value) return
  messageSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    photo.value = await apiFetch<Photo>(`/photos/${photo.value.id}/message`, {
      method: 'PATCH',
      body: { user_message: userMessage.value },
    })
    editingMessage.value = false
    successMessage.value = 'Message saved'
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    messageSaving.value = false
  }
}

async function toggleShowcaseVisibility() {
  if (!photo.value) return
  showcaseSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    photo.value = await apiFetch<Photo>(`/photos/${photo.value.id}`, {
      method: 'PATCH',
      body: { include_in_showcase: !photo.value.include_in_showcase },
    })
    successMessage.value = photo.value.include_in_showcase ? 'Photo is visible in showcase' : 'Photo hidden from showcase'
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    showcaseSaving.value = false
  }
}

async function saveAdminPhoto() {
  if (!photo.value) return
  adminSaving.value = true
  errorMessage.value = ''
  try {
    const body: Record<string, unknown> = {}
    if (category.value !== photo.value.category) {
      body.category = category.value
    }
    body.final_caption = adminFinalCaption.value || null
    body.location_name = adminLocationName.value || null
    body.location_city = adminLocationCity.value || null
    body.location_country = adminLocationCountry.value || null
    body.location_region = adminLocationRegion.value || null
    body.location_district = adminLocationDistrict.value || null
    body.location_road = adminLocationRoad.value || null

    adminPhoto.value = await apiFetch<AdminPhoto>(`/admin/photos/${photo.value.id}`, {
      method: 'PATCH',
      body,
    })
    await loadPhoto(false)
    successMessage.value = 'Admin changes saved'
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    adminSaving.value = false
  }
}

async function resetCaption() {
  if (!photo.value) return
  adminResettingCaption.value = true
  try {
    const resp = await apiFetch<{ final_caption: string | null; caption_source: string }>(
      `/admin/photos/${photo.value.id}/reset-caption`,
      { method: 'POST' },
    )
    await loadAdminPhoto(photo.value.id)
    await loadPhoto(false)
    successMessage.value = 'Caption reset to auto'
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    adminResettingCaption.value = false
  }
}

async function regenerateDesign() {
  if (!photo.value) return
  const labels: Record<RegenerateScope, string> = {
    caption: 'Regenerate Caption Only',
    template: 'Regenerate Template Only',
    css_tokens: 'Regenerate CSS Tokens Only',
    full: 'Regenerate Full Design',
    fallback: 'Reset to Deterministic Fallback',
  }
  if (process.client && !window.confirm(`Confirm: ${labels[regenScope.value]}?`)) {
    return
  }
  adminRegenerating.value = true
  try {
    await apiFetch(`/admin/photos/${photo.value.id}/regenerate`, {
      method: 'POST',
      body: { scope: regenScope.value },
    })
    successMessage.value = 'Regeneration queued'
    await refreshProcessingStatus()
    startProcessingPoll()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    adminRegenerating.value = false
  }
}

function loadDesignJsonIntoEditor(designJson: Record<string, unknown> | null) {
  if (!designJson) return
  manualDesignJson.value = JSON.stringify(designJson, null, 2)
  successMessage.value = 'Loaded design JSON into editor'
}

async function saveManualDesignDraft() {
  if (!photo.value) return
  let parsed: Record<string, unknown>
  try {
    parsed = JSON.parse(manualDesignJson.value) as Record<string, unknown>
  } catch {
    errorMessage.value = 'Manual design JSON is invalid'
    return
  }

  manualDesignSaving.value = true
  errorMessage.value = ''
  try {
    adminPhoto.value = await apiFetch<AdminPhoto>(`/admin/photos/${photo.value.id}/design-versions/manual`, {
      method: 'POST',
      body: { design_json: parsed },
    })
    successMessage.value = 'Manual draft saved'
    syncManualDesignEditor()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    manualDesignSaving.value = false
  }
}

async function activateDesignVersion(designId: string) {
  if (!photo.value) return
  activatingDesignId.value = designId
  errorMessage.value = ''
  try {
    adminPhoto.value = await apiFetch<AdminPhoto>(`/admin/photos/${photo.value.id}/design-versions/${designId}/activate`, {
      method: 'POST',
    })
    await loadPhoto(false)
    successMessage.value = 'Active design updated'
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    activatingDesignId.value = null
  }
}

onMounted(async () => {
  if (!currentUser.value) {
    await loadMe()
  }
  await loadPhoto()
})
onBeforeUnmount(stopProcessingPoll)
</script>

<template>
  <section class="space-y-5">
    <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>

    <div v-if="pending" class="rounded-lg border border-stone-200 bg-white p-8 text-center text-sm text-stone-600">
      Loading photo
    </div>

    <div v-else-if="photo" class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div class="overflow-hidden rounded-lg bg-ink">
        <img
          v-if="imageUrl"
          :src="imageUrl"
          :alt="photo.final_caption || displayCategory(photo.category)"
          class="max-h-[75vh] w-full object-contain"
        >
      </div>

      <aside class="space-y-5">
        <!-- Public Details -->
        <div class="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <div class="mb-4 flex items-center justify-between gap-3">
            <h1 class="text-lg font-semibold">Photo Details</h1>
            <a
              v-if="imageUrl"
              :href="imageUrl"
              target="_blank"
              rel="noreferrer"
              class="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md text-stone-700 hover:bg-mist/60"
              title="Open original"
            >
              <ExternalLink class="h-4 w-4" aria-hidden="true" />
            </a>
          </div>

          <dl class="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt class="text-stone-500">Taken</dt>
              <dd class="font-medium">{{ formatDate(photo.taken_at) }}</dd>
            </div>
            <div>
              <dt class="text-stone-500">Uploaded</dt>
              <dd class="font-medium">{{ formatDate(photo.uploaded_at) }}</dd>
            </div>
            <div>
              <dt class="text-stone-500">Size</dt>
              <dd class="font-medium">{{ photo.width || '?' }} x {{ photo.height || '?' }}</dd>
            </div>
            <div>
              <dt class="text-stone-500">File</dt>
              <dd class="font-medium">{{ formatBytes(photo.file_size) }}</dd>
            </div>
            <div>
              <dt class="text-stone-500">Camera</dt>
              <dd class="font-medium">{{ photo.camera_make || 'Unknown' }} {{ photo.camera_model || '' }}</dd>
            </div>
            <div>
              <dt class="text-stone-500">GPS</dt>
              <dd class="font-medium">
                {{ photo.gps_lat && photo.gps_lng ? `${photo.gps_lat}, ${photo.gps_lng}` : 'Unknown' }}
              </dd>
            </div>
            <div>
              <dt class="text-stone-500">Status</dt>
              <dd class="font-medium">{{ formatStatus(photo.status) }}</dd>
            </div>
            <div v-if="processingStatus?.slide_design_status">
              <dt class="text-stone-500">Slide Design</dt>
              <dd class="font-medium">{{ processingStatus.slide_design_status }}{{ processingStatus.slide_design_source ? ` (${processingStatus.slide_design_source})` : '' }}</dd>
            </div>
          </dl>
          <p v-if="isInProgressStatus(photo.status)" class="mt-4 flex items-center gap-2 rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-600">
            <Loader2 class="h-3 w-3 animate-spin" aria-hidden="true" />
            {{ formatStatus(photo.status) }}
          </p>
          <p v-if="photo.status === 'failed'" class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {{ processingStatus?.error_message || 'Processing failed' }}
          </p>
          <p v-if="photo.location_name" class="mt-3 text-sm text-stone-600">
            📍 {{ [photo.location_city, photo.location_region, photo.location_country].filter(Boolean).join(', ') || photo.location_name }}
          </p>
        </div>

        <div v-if="canManageShowcaseVisibility" class="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <div class="mb-4 rounded-md border border-stone-200 bg-stone-50 px-3 py-3">
            <div class="flex items-center justify-between gap-3">
              <div>
                <h2 class="text-sm font-semibold text-stone-700">Showcase Visibility</h2>
                <p class="mt-1 text-xs text-stone-600">
                  {{ photo.include_in_showcase ? 'This photo currently appears in showcase.' : 'This photo is hidden from showcase.' }}
                </p>
              </div>
              <button
                type="button"
                class="focus-ring inline-flex items-center gap-1.5 rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50"
                :disabled="showcaseSaving"
                @click="toggleShowcaseVisibility"
              >
                <Loader2 v-if="showcaseSaving" class="h-3.5 w-3.5 animate-spin" />
                <span>{{ photo.include_in_showcase ? 'Hide from Showcase' : 'Show in Showcase' }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Owner Message Edit -->
        <div v-if="isOwner" class="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-stone-700">Your Message</h2>
            <button
              v-if="!editingMessage"
              type="button"
              class="focus-ring inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-stone-600 hover:bg-stone-100"
              @click="editingMessage = true"
            >
              <Edit3 class="h-3 w-3" />
              Edit
            </button>
          </div>
          <p v-if="!editingMessage" class="text-sm text-stone-800 whitespace-pre-wrap">
            {{ photo.user_message || 'No message yet' }}
          </p>
          <div v-else class="space-y-3">
            <textarea
              v-model="userMessage"
              class="focus-ring min-h-28 w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm"
              maxlength="2000"
            />
            <div v-if="photo.caption_source === 'admin'" class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              An admin has set the final caption. Your message is saved but the displayed caption stays as the admin's until they reset it.
            </div>
            <p v-if="successMessage" class="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {{ successMessage }}
            </p>
            <div class="flex gap-2">
              <button
                type="button"
                class="focus-ring inline-flex items-center gap-1.5 rounded-md bg-moss px-3 py-1.5 text-sm font-medium text-white hover:bg-moss/90 disabled:opacity-50"
                :disabled="messageSaving"
                @click="saveMessage"
              >
                <Save class="h-3.5 w-3.5" />
                {{ messageSaving ? 'Saving…' : 'Save Message' }}
              </button>
              <button
                type="button"
                class="focus-ring rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-600 hover:bg-stone-100"
                @click="editingMessage = false; userMessage = photo.user_message || ''"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>

        <!-- Admin Diagnostic Panel -->
        <div v-if="isAdmin && adminPhoto" class="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-sm">
          <h2 class="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-800">
            🔧 Admin Diagnostics
          </h2>

          <!-- Caption -->
          <div class="mb-3 space-y-2">
            <label class="block text-xs font-medium text-stone-700">
              Final Caption
              <span class="ml-1 rounded bg-stone-200 px-1.5 py-0.5 text-xs text-stone-600">
                {{ adminPhoto.caption_source }}
              </span>
            </label>
            <textarea
              v-model="adminFinalCaption"
              class="focus-ring w-full rounded-md border border-stone-300 bg-white px-2 py-1 text-sm"
              rows="2"
              maxlength="2000"
            />
            <button
              type="button"
              class="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-stone-600 hover:bg-stone-200 disabled:opacity-50"
              :disabled="adminResettingCaption || adminPhoto.caption_source === 'user' || adminPhoto.caption_source === 'ai'"
              @click="resetCaption"
            >
              <RotateCcw class="h-3 w-3" />
              {{ adminResettingCaption ? 'Resetting…' : 'Reset to auto' }}
            </button>
          </div>

          <!-- Location -->
          <div class="mb-3 grid grid-cols-2 gap-2">
            <label class="block">
              <span class="text-xs text-stone-600">Name</span>
              <input v-model="adminLocationName" class="focus-ring w-full rounded border border-stone-300 bg-white px-2 py-1 text-sm" />
            </label>
            <label class="block">
              <span class="text-xs text-stone-600">City</span>
              <input v-model="adminLocationCity" class="focus-ring w-full rounded border border-stone-300 bg-white px-2 py-1 text-sm" />
            </label>
            <label class="block">
              <span class="text-xs text-stone-600">Region</span>
              <input v-model="adminLocationRegion" class="focus-ring w-full rounded border border-stone-300 bg-white px-2 py-1 text-sm" />
            </label>
            <label class="block">
              <span class="text-xs text-stone-600">Country</span>
              <input v-model="adminLocationCountry" class="focus-ring w-full rounded border border-stone-300 bg-white px-2 py-1 text-sm" />
            </label>
            <label class="block">
              <span class="text-xs text-stone-600">District</span>
              <input v-model="adminLocationDistrict" class="focus-ring w-full rounded border border-stone-300 bg-white px-2 py-1 text-sm" />
            </label>
            <label class="block">
              <span class="text-xs text-stone-600">Road</span>
              <input v-model="adminLocationRoad" class="focus-ring w-full rounded border border-stone-300 bg-white px-2 py-1 text-sm" />
            </label>
          </div>

          <!-- Geocoding Status -->
          <div class="mb-3 text-xs">
            <span class="text-stone-600">Geocoding:</span>
            <span class="ml-1 rounded px-1.5 py-0.5" :class="adminPhoto.geocoding_status === 'succeeded' ? 'bg-emerald-100 text-emerald-700' : adminPhoto.geocoding_status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-stone-100 text-stone-600'">
              {{ adminPhoto.geocoding_status }}
            </span>
            <span v-if="adminPhoto.geocoding_provider" class="ml-1 text-stone-500">via {{ adminPhoto.geocoding_provider }}</span>
            <p v-if="adminPhoto.geocoding_error" class="mt-1 text-red-600">{{ adminPhoto.geocoding_error }}</p>
          </div>

          <!-- AI Info -->
          <div v-if="adminPhoto.ai_analysis_json || adminPhoto.ai_caption || adminPhoto.ai_category_suggestion" class="mb-3 border-t border-amber-200 pt-2 text-xs">
            <p v-if="adminPhoto.ai_category_suggestion" class="text-stone-700">
              <span class="text-stone-500">AI Category:</span> {{ adminPhoto.ai_category_suggestion }}
            </p>
            <p v-if="adminPhoto.ai_caption" class="text-stone-700">
              <span class="text-stone-500">AI Caption:</span> {{ adminPhoto.ai_caption }}
            </p>
            <details v-if="adminPhoto.ai_analysis_json" class="mt-1">
              <summary class="cursor-pointer text-stone-500 hover:text-stone-700">AI Analysis JSON</summary>
              <pre class="mt-1 max-h-32 overflow-auto rounded bg-stone-100 p-2 text-xs">{{ JSON.stringify(adminPhoto.ai_analysis_json, null, 2) }}</pre>
            </details>
          </div>

          <!-- EXIF -->
          <details v-if="adminPhoto.exif_json" class="mb-3 border-t border-amber-200 pt-2 text-xs">
            <summary class="cursor-pointer text-stone-500 hover:text-stone-700">EXIF Data</summary>
            <pre class="mt-1 max-h-32 overflow-auto rounded bg-stone-100 p-2">{{ JSON.stringify(adminPhoto.exif_json, null, 2) }}</pre>
          </details>

          <!-- Category Source -->
          <div class="mb-3 text-xs text-stone-600">
            Category source: <span class="font-medium">{{ adminPhoto.category_source }}</span>
          </div>

          <div class="mb-3 grid grid-cols-3 gap-2 text-xs">
            <div class="rounded-md border border-amber-200 bg-white px-2 py-2">
              <p class="text-stone-500">AI Status</p>
              <p class="font-medium text-stone-800">{{ AI_STATUS_LABELS[adminPhoto.ai_status] || adminPhoto.ai_status }}</p>
            </div>
            <div class="rounded-md border border-amber-200 bg-white px-2 py-2">
              <p class="text-stone-500">Active Design</p>
              <p class="font-medium text-stone-800">
                {{ adminPhoto.active_design_source ? `${DESIGN_SOURCE_LABELS[adminPhoto.active_design_source] || adminPhoto.active_design_source} v${adminPhoto.active_design_version}` : 'None' }}
              </p>
            </div>
            <div class="rounded-md border border-amber-200 bg-white px-2 py-2">
              <p class="text-stone-500">Attention</p>
              <p class="font-medium" :class="adminPhoto.needs_review ? 'text-amber-700' : 'text-emerald-700'">
                {{ adminPhoto.needs_review ? 'Needs review' : 'Healthy' }}
              </p>
            </div>
          </div>

          <!-- Admin Actions -->
          <div class="flex flex-wrap gap-2 border-t border-amber-200 pt-3">
            <button
              type="button"
              class="focus-ring inline-flex items-center gap-1.5 rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
              :disabled="adminSaving"
              @click="saveAdminPhoto"
            >
              <Save class="h-3.5 w-3.5" />
              {{ adminSaving ? 'Saving…' : 'Save Admin Changes' }}
            </button>
            <select
              v-model="regenScope"
              class="focus-ring rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-700"
              :disabled="adminRegenerating || hasActiveJob(processingStatus)"
            >
              <option value="caption">Caption only</option>
              <option value="template">Template only</option>
              <option value="css_tokens">CSS tokens only</option>
              <option value="full">Full design</option>
              <option value="fallback">Deterministic fallback</option>
            </select>
            <button
              type="button"
              class="focus-ring inline-flex items-center gap-1.5 rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50"
              :disabled="adminRegenerating || hasActiveJob(processingStatus)"
              @click="regenerateDesign"
            >
              <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': adminRegenerating }" />
              {{ adminRegenerating ? 'Queuing…' : 'Run Regeneration' }}
            </button>
          </div>
          <p v-if="hasActiveJob(processingStatus)" class="mt-3 text-xs text-stone-600">
            Latest job: {{ processingStatus?.job_type }} / {{ processingStatus?.job_status }}
          </p>

          <div v-if="adminPhoto.design_versions.length" class="mt-4 border-t border-amber-200 pt-3">
            <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-600">Design Versions</h3>
            <div class="space-y-2">
              <div
                v-for="design in adminPhoto.design_versions"
                :key="design.id"
                class="rounded-md border border-amber-200 bg-white px-3 py-2 text-xs"
              >
                <div class="flex items-center justify-between gap-2">
                  <p class="font-medium text-stone-800">
                    v{{ design.version }} · {{ DESIGN_SOURCE_LABELS[design.source] || design.source }} · {{ design.status }}
                  </p>
                  <span class="text-stone-500">{{ formatDate(design.created_at) }}</span>
                </div>
                <p class="mt-1 text-stone-600">
                  {{ design.template_id || 'unknown template' }} · {{ design.layer_count }} layers
                </p>
                <p v-if="design.quality_report" class="mt-1" :class="design.quality_report.passed ? 'text-emerald-700' : 'text-red-700'">
                  Quality {{ design.quality_report.total_score }}/5
                  <span v-if="design.quality_report.failures.length"> · {{ design.quality_report.failures.join('; ') }}</span>
                </p>
                <p v-if="design.validation_errors?.length" class="mt-1 text-red-700">
                  {{ design.validation_errors.join('; ') }}
                </p>
                <div class="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    class="focus-ring rounded-md border border-stone-300 bg-white px-2 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100"
                    @click="loadDesignJsonIntoEditor(design.design_json)"
                  >
                    Load JSON
                  </button>
                  <button
                    v-if="design.status !== 'active'"
                    type="button"
                    class="focus-ring rounded-md border border-amber-300 bg-amber-100 px-2 py-1 text-xs font-medium text-amber-900 hover:bg-amber-200 disabled:opacity-50"
                    :disabled="activatingDesignId === design.id"
                    @click="activateDesignVersion(design.id)"
                  >
                    {{ activatingDesignId === design.id ? 'Switching…' : 'Set Active' }}
                  </button>
                  <span
                    v-else
                    class="inline-flex items-center rounded-md bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-800"
                  >
                    Active
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-4 border-t border-amber-200 pt-3">
            <div class="mb-2 flex items-center justify-between gap-2">
              <h3 class="text-xs font-semibold uppercase tracking-wide text-stone-600">Manual Design JSON</h3>
              <button
                type="button"
                class="focus-ring rounded-md border border-stone-300 bg-white px-2 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100"
                @click="syncManualDesignEditor(true)"
              >
                Reset Editor
              </button>
            </div>
            <textarea
              v-model="manualDesignJson"
              class="focus-ring min-h-56 w-full rounded-md border border-stone-300 bg-white px-3 py-2 font-mono text-xs text-stone-800"
              spellcheck="false"
            />
            <div class="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                class="focus-ring inline-flex items-center gap-1.5 rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
                :disabled="manualDesignSaving"
                @click="saveManualDesignDraft"
              >
                <Save class="h-3.5 w-3.5" />
                {{ manualDesignSaving ? 'Saving…' : 'Save Manual Draft' }}
              </button>
            </div>
          </div>

          <div v-if="adminPhoto.recent_jobs.length" class="mt-4 border-t border-amber-200 pt-3">
            <div class="mb-2 flex items-center justify-between gap-2">
              <h3 class="text-xs font-semibold uppercase tracking-wide text-stone-600">Recent Jobs</h3>
              <NuxtLink :to="`/admin/jobs?photo_id=${adminPhoto.id}`" class="text-xs font-medium text-moss hover:underline">
                View all
              </NuxtLink>
            </div>
            <div class="space-y-2">
              <div
                v-for="job in adminPhoto.recent_jobs"
                :key="job.id"
                class="rounded-md border border-amber-200 bg-white px-3 py-2 text-xs"
              >
                <div class="flex items-center justify-between gap-2">
                  <p class="font-medium text-stone-800">{{ formatAdminJobType(job.job_type) }}</p>
                  <span class="text-stone-500">{{ job.status }}</span>
                </div>
                <p class="mt-1 text-stone-600">
                  {{ job.ai_provider || 'system' }}{{ job.ai_model ? ` · ${job.ai_model}` : '' }}{{ job.ai_prompt_version ? ` · ${job.ai_prompt_version}` : '' }}
                </p>
                <p v-if="job.error_message" class="mt-1 text-red-700">{{ job.error_message }}</p>
              </div>
            </div>
          </div>

          <div v-if="adminPhoto.recent_audit_logs.length" class="mt-4 border-t border-amber-200 pt-3">
            <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-600">Recent Audit</h3>
            <div class="space-y-2">
              <div
                v-for="entry in adminPhoto.recent_audit_logs"
                :key="entry.id"
                class="rounded-md border border-amber-200 bg-white px-3 py-2 text-xs"
              >
                <div class="flex items-center justify-between gap-2">
                  <p class="font-medium text-stone-800">{{ entry.action }}</p>
                  <span class="text-stone-500">{{ formatDate(entry.created_at) }}</span>
                </div>
                <p class="mt-1 text-stone-600">{{ entry.summary || 'No summary' }}</p>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>
