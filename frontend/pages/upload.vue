<script setup lang="ts">
import { CheckCircle2, Upload, XCircle } from 'lucide-vue-next'
import type { PhotoBatchUploadResponse, PhotoCategory } from '~/types/api'

const { apiFetch } = useApi()
const { formatBytes } = useFormat()
const fileInput = ref<HTMLInputElement | null>(null)
const category = ref<PhotoCategory>('life')
const userMessage = ref('')
const selectedFiles = ref<File[]>([])
const pending = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const uploadResults = ref<PhotoBatchUploadResponse | null>(null)

function onFileChange() {
  selectedFiles.value = Array.from(fileInput.value?.files || [])
  uploadResults.value = null
  successMessage.value = ''
  errorMessage.value = ''
}

function displayError(error: string | null) {
  if (!error) {
    return ''
  }
  if (error === 'HEIC/HEIF conversion is not available') {
    return 'HEIC/HEIF conversion is not available. Convert the photo to JPEG and upload it again.'
  }
  return error
}

async function submitUpload() {
  errorMessage.value = ''
  successMessage.value = ''
  uploadResults.value = null
  if (!selectedFiles.value.length) {
    errorMessage.value = 'Select photos first'
    return
  }

  const formData = new FormData()
  for (const file of selectedFiles.value) {
    formData.append('files', file)
  }
  formData.set('category', category.value)
  if (userMessage.value.trim()) {
    formData.set('user_message', userMessage.value.trim())
  }

  pending.value = true
  try {
    const result = await apiFetch<PhotoBatchUploadResponse>('/photos/batch-upload', {
      method: 'POST',
      body: formData,
    })
    uploadResults.value = result
    successMessage.value = `${result.success_count} uploaded, ${result.failure_count} failed`
  } catch (error) {
    errorMessage.value = displayError(getApiErrorMessage(error))
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <section class="max-w-2xl space-y-5">
    <div>
      <h1 class="text-2xl font-semibold">Upload</h1>
    </div>

    <form class="space-y-5 rounded-lg border border-stone-200 bg-white p-5 shadow-sm" @submit.prevent="submitUpload">
      <label class="block">
        <span class="mb-1 block text-sm font-medium text-stone-700">Photo</span>
        <input
          ref="fileInput"
          class="focus-ring block w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
          multiple
          required
          @change="onFileChange"
        >
      </label>

      <div v-if="selectedFiles.length" class="overflow-hidden rounded-md border border-stone-200">
        <div
          v-for="file in selectedFiles"
          :key="`${file.name}-${file.size}-${file.lastModified}`"
          class="flex items-center justify-between gap-3 border-b border-stone-100 px-3 py-2 last:border-b-0"
        >
          <span class="min-w-0 truncate text-sm text-stone-800">{{ file.name }}</span>
          <span class="shrink-0 text-xs text-stone-500">{{ formatBytes(file.size) }}</span>
        </div>
      </div>

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

      <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ errorMessage }}
      </p>
      <p v-if="successMessage" class="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
        {{ successMessage }}
      </p>

      <div v-if="uploadResults" class="overflow-hidden rounded-md border border-stone-200">
        <div
          v-for="(item, index) in uploadResults.results"
          :key="`${item.filename}-${index}`"
          class="flex items-start gap-3 border-b border-stone-100 px-3 py-2 last:border-b-0"
        >
          <CheckCircle2 v-if="item.success" class="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
          <XCircle v-else class="mt-0.5 h-4 w-4 shrink-0 text-red-600" aria-hidden="true" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-stone-800">{{ item.filename }}</p>
            <p class="text-sm text-stone-600">
              {{ item.success ? 'Queued for processing' : displayError(item.error) }}
            </p>
          </div>
          <NuxtLink
            v-if="item.photo"
            :to="`/photo/${item.photo.id}`"
            class="focus-ring shrink-0 rounded-md px-2 py-1 text-sm font-medium text-moss hover:bg-mist/60"
          >
            Open
          </NuxtLink>
        </div>
      </div>

      <button
        type="submit"
        class="focus-ring inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 font-medium text-white hover:bg-moss/90 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="pending"
      >
        <Upload class="h-4 w-4" aria-hidden="true" />
        {{ pending ? 'Uploading' : 'Upload' }}
      </button>
    </form>
  </section>
</template>
