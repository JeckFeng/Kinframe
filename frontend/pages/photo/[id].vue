<script setup lang="ts">
import { ExternalLink, Loader2, Save } from 'lucide-vue-next'
import type { Photo, PhotoCategory, PhotoProcessingStatusResponse, PresignedUrlResponse } from '~/types/api'

const route = useRoute()
const { apiFetch } = useApi()
const { formatBytes, formatDate } = useFormat()
const { displayCategory } = usePhotoCategories()

const photo = ref<Photo | null>(null)
const processingStatus = ref<PhotoProcessingStatusResponse | null>(null)
const imageUrl = ref('')
const category = ref<PhotoCategory>('life')
const userMessage = ref('')
const pending = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
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

function formatStatus(status: string): string {
  return STATUS_LABELS[status] || status
}

function isInProgressStatus(status: string) {
  return !['ready', 'failed'].includes(status)
}

function stopProcessingPoll() {
  if (processingPollTimer) {
    clearInterval(processingPollTimer)
    processingPollTimer = null
  }
}

async function refreshProcessingStatus() {
  if (!photo.value) {
    return
  }
  const status = await apiFetch<PhotoProcessingStatusResponse>(`/photos/${photo.value.id}/processing-status`)
  processingStatus.value = status
  if (!isInProgressStatus(status.photo_status)) {
    stopProcessingPoll()
    await loadPhoto(false)
  }
}

function startProcessingPoll() {
  if (processingPollTimer) {
    return
  }
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
    category.value = photo.value.category === 'travel' ? 'photography' : photo.value.category
    userMessage.value = photo.value.user_message || ''
    processingStatus.value = null
    const response = await apiFetch<PresignedUrlResponse>(`/photos/${id}/original-url`)
    imageUrl.value = response.url
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

async function savePhoto() {
  if (!photo.value) {
    return
  }
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    photo.value = await apiFetch<Photo>(`/photos/${photo.value.id}`, {
      method: 'PATCH',
      body: {
        category: category.value,
        user_message: userMessage.value,
      },
    })
    successMessage.value = 'Saved'
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    saving.value = false
  }
}

onMounted(loadPhoto)
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
        </div>

        <form class="rounded-lg border border-stone-200 bg-white p-4 shadow-sm" @submit.prevent="savePhoto">
          <div class="space-y-4">
            <label class="block">
              <span class="mb-1 block text-sm font-medium text-stone-700">Category</span>
              <select v-model="category" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2">
                <option value="life">生活照</option>
                <option value="photography">摄影照</option>
                <option value="pet">宠物照</option>
              </select>
            </label>

            <label class="block">
              <span class="mb-1 block text-sm font-medium text-stone-700">Message</span>
              <textarea
                v-model="userMessage"
                class="focus-ring min-h-28 w-full rounded-md border border-stone-300 bg-white px-3 py-2"
                maxlength="2000"
              />
            </label>

            <p v-if="successMessage" class="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {{ successMessage }}
            </p>

            <button
              type="submit"
              class="focus-ring inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 font-medium text-white hover:bg-moss/90 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="saving"
            >
              <Save class="h-4 w-4" aria-hidden="true" />
              {{ saving ? 'Saving' : 'Save' }}
            </button>
          </div>
        </form>
      </aside>
    </div>
  </section>
</template>
