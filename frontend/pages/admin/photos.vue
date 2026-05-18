<script setup lang="ts">
import { Loader2, RefreshCw } from 'lucide-vue-next'
import type { AdminCategory, AdminJobItem, AdminPhotoListItem, AdminPhotoListResponse, Photo } from '~/types/api'

const { apiFetch } = useApi()
const { formatDate } = useFormat()

const photos = ref<AdminPhotoListItem[]>([])
const categories = ref<AdminCategory[]>([])
const pending = ref(true)
const errorMessage = ref('')

const categoryFilter = ref('')
const geocodingFilter = ref('')
const showcaseFilter = ref('')
const designSourceFilter = ref('')
const failedOnly = ref(false)
const needsReview = ref(false)
const visibilityUpdatingId = ref<string | null>(null)
const deletingPhotoId = ref<string | null>(null)
const deleteJobId = ref<string | null>(null)

async function loadPhotos() {
  pending.value = true
  errorMessage.value = ''
  try {
    const params = new URLSearchParams()
    if (categoryFilter.value) params.set('category', categoryFilter.value)
    if (geocodingFilter.value) params.set('geocoding_status', geocodingFilter.value)
    if (showcaseFilter.value) params.set('showcase_visibility', showcaseFilter.value)
    if (designSourceFilter.value) params.set('design_source', designSourceFilter.value)
    if (failedOnly.value) params.set('failed_only', 'true')
    if (needsReview.value) params.set('needs_review', 'true')
    const query = params.toString()
    const response = await apiFetch<AdminPhotoListResponse>(`/admin/photos${query ? `?${query}` : ''}`)
    photos.value = response.items
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

async function loadCategories() {
  categories.value = await apiFetch<AdminCategory[]>('/admin/categories')
}

async function loadPage() {
  await Promise.all([loadCategories(), loadPhotos()])
}

async function toggleShowcaseVisibility(photo: AdminPhotoListItem) {
  visibilityUpdatingId.value = photo.id
  errorMessage.value = ''
  try {
    const updated = await apiFetch<Photo>(`/photos/${photo.id}`, {
      method: 'PATCH',
      body: { include_in_showcase: !photo.include_in_showcase },
    })
    const target = photos.value.find((item) => item.id === photo.id)
    if (target) {
      target.include_in_showcase = updated.include_in_showcase
    }
    if (showcaseFilter.value === 'visible' && !updated.include_in_showcase) {
      photos.value = photos.value.filter((item) => item.id !== photo.id)
    } else if (showcaseFilter.value === 'hidden' && updated.include_in_showcase) {
      photos.value = photos.value.filter((item) => item.id !== photo.id)
    }
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    visibilityUpdatingId.value = null
  }
}

async function refreshDeleteJob(targetPhotoId: string) {
  if (!deleteJobId.value) return
  const jobs = await apiFetch<AdminJobItem[]>('/admin/jobs?job_type=photo_purge')
  const job = jobs.find((candidate) => candidate.id === deleteJobId.value)
  if (!job) return

  if (job.status === 'succeeded') {
    photos.value = photos.value.filter((item) => item.id !== targetPhotoId)
    deletingPhotoId.value = null
    deleteJobId.value = null
    return
  }

  if (job.status === 'failed') {
    deletingPhotoId.value = null
    deleteJobId.value = null
    errorMessage.value = job.error_message || 'Permanent delete failed'
    await loadPhotos()
  }
}

async function deletePhotoPermanently(photo: AdminPhotoListItem) {
  if (deletingPhotoId.value) return
  const confirmed = process.client
    ? window.confirm(
        'Delete this photo permanently?\n\nThis removes the original, preview, thumbnail, slide designs, and database records. This cannot be undone.',
      )
    : false
  if (!confirmed) return

  deletingPhotoId.value = photo.id
  errorMessage.value = ''
  try {
    const response = await apiFetch<{ photo_id: string; job_id: string; job_type: string }>(`/admin/photos/${photo.id}/delete`, {
      method: 'POST',
    })
    deleteJobId.value = response.job_id
    await refreshDeleteJob(photo.id)
    for (let attempt = 0; attempt < 20 && deletingPhotoId.value === photo.id; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 500))
      await refreshDeleteJob(photo.id)
    }
  } catch (error) {
    deletingPhotoId.value = null
    deleteJobId.value = null
    errorMessage.value = getApiErrorMessage(error)
  }
}

onMounted(loadPage)
</script>

<template>
  <section class="space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-semibold">Photo Operations</h1>
        <p class="text-sm text-stone-600">{{ photos.length }} photos</p>
      </div>
      <button
        type="button"
        class="focus-ring inline-flex items-center gap-2 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
        @click="loadPhotos"
      >
        <RefreshCw class="h-4 w-4" aria-hidden="true" />
        Refresh
      </button>
    </div>

    <div class="grid gap-3 rounded-lg border border-stone-200 bg-white p-4 shadow-sm lg:grid-cols-6">
      <label class="space-y-1 text-sm">
        <span class="text-stone-600">Category</span>
        <select v-model="categoryFilter" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
          <option value="">All</option>
          <option v-for="category in categories" :key="category.id" :value="category.slug">{{ category.name }}</option>
        </select>
      </label>
      <label class="space-y-1 text-sm">
        <span class="text-stone-600">Geocoding</span>
        <select v-model="geocodingFilter" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
          <option value="">All</option>
          <option value="not_applicable">Not Applicable</option>
          <option value="pending">Pending</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
        </select>
      </label>
      <label class="space-y-1 text-sm">
        <span class="text-stone-600">Showcase</span>
        <select v-model="showcaseFilter" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
          <option value="">All</option>
          <option value="visible">Visible</option>
          <option value="hidden">Hidden</option>
        </select>
      </label>
      <label class="space-y-1 text-sm">
        <span class="text-stone-600">Design Source</span>
        <select v-model="designSourceFilter" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
          <option value="">All</option>
          <option value="fallback">Fallback</option>
          <option value="manual">Manual</option>
        </select>
      </label>
      <label class="flex items-center gap-2 rounded-md border border-stone-200 px-3 py-2 text-sm text-stone-700">
        <input v-model="failedOnly" type="checkbox" class="rounded border-stone-300" />
        Failed only
      </label>
      <label class="flex items-center gap-2 rounded-md border border-stone-200 px-3 py-2 text-sm text-stone-700">
        <input v-model="needsReview" type="checkbox" class="rounded border-stone-300" />
        Needs review
      </label>
      <div class="flex gap-2 lg:col-span-7">
        <button
          type="button"
          class="focus-ring inline-flex items-center justify-center rounded-md bg-moss px-3 py-2 text-sm font-medium text-white hover:bg-moss/90"
          @click="loadPhotos"
        >
          Apply Filters
        </button>
        <button
          type="button"
          class="focus-ring inline-flex items-center justify-center rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
          @click="categoryFilter = ''; geocodingFilter = ''; showcaseFilter = ''; designSourceFilter = ''; failedOnly = false; needsReview = false; loadPhotos()"
        >
          Reset
        </button>
      </div>
    </div>

    <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>

    <div class="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
      <table class="min-w-full divide-y divide-stone-200 text-sm">
        <thead class="bg-mist/50 text-left text-stone-700">
          <tr>
            <th class="px-3 py-3 font-semibold">Photo</th>
            <th class="px-3 py-3 font-semibold">Caption</th>
            <th class="px-3 py-3 font-semibold">Category</th>
            <th class="px-3 py-3 font-semibold">Design</th>
            <th class="px-3 py-3 font-semibold">Showcase</th>
            <th class="px-3 py-3 font-semibold">Geocoding</th>
            <th class="px-3 py-3 font-semibold">Latest Job</th>
            <th class="px-3 py-3 font-semibold">Taken</th>
            <th class="px-3 py-3 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-stone-100">
          <tr v-if="pending">
            <td class="px-3 py-4 text-stone-600" colspan="9">Loading photos</td>
          </tr>
          <tr v-else-if="!photos.length">
            <td class="px-3 py-4 text-stone-600" colspan="9">No matching photos</td>
          </tr>
          <tr v-for="photo in photos" v-else :key="photo.id" :class="photo.has_failed_jobs ? 'bg-red-50/30' : photo.needs_review ? 'bg-amber-50/30' : ''">
            <td class="px-3 py-3">
              <NuxtLink :to="`/photo/${photo.id}`" class="font-mono text-xs text-moss hover:underline">
                {{ photo.id.slice(0, 8) }}…
              </NuxtLink>
            </td>
            <td class="px-3 py-3 max-w-56 truncate text-stone-700">{{ photo.final_caption || photo.user_message || '-' }}</td>
            <td class="px-3 py-3">{{ photo.category }}</td>
            <td class="px-3 py-3 text-xs text-stone-700">
              <p>{{ photo.active_design_source || 'none' }}</p>
              <p class="text-stone-500">v{{ photo.active_design_version || 0 }}</p>
            </td>
            <td class="px-3 py-3">
              <span
                class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                :class="photo.include_in_showcase ? 'bg-emerald-100 text-emerald-700' : 'bg-stone-200 text-stone-700'"
              >
                {{ photo.include_in_showcase ? 'Visible' : 'Hidden' }}
              </span>
            </td>
            <td class="px-3 py-3 text-xs text-stone-700">
              <p>{{ photo.geocoding_status }}</p>
              <p class="text-stone-500">{{ photo.location_city || photo.location_name || '-' }}</p>
            </td>
            <td class="px-3 py-3 text-xs text-stone-700">
              <p>{{ photo.latest_job_type || '-' }}</p>
              <p class="text-stone-500">{{ photo.latest_job_status || '-' }}</p>
              <p v-if="photo.latest_job_error" class="max-w-48 truncate text-red-600">{{ photo.latest_job_error }}</p>
            </td>
            <td class="px-3 py-3 whitespace-nowrap text-stone-600">{{ formatDate(photo.taken_at) }}</td>
            <td class="px-3 py-3">
              <button
                type="button"
                class="focus-ring inline-flex items-center gap-1.5 rounded-md border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 hover:bg-mist/60 disabled:opacity-50"
                :disabled="visibilityUpdatingId === photo.id || deletingPhotoId === photo.id"
                @click="toggleShowcaseVisibility(photo)"
              >
                <Loader2 v-if="visibilityUpdatingId === photo.id" class="h-3.5 w-3.5 animate-spin" />
                <span>{{ photo.include_in_showcase ? 'Hide' : 'Show' }}</span>
              </button>
              <button
                type="button"
                class="focus-ring ml-2 inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                :disabled="deletingPhotoId === photo.id || visibilityUpdatingId === photo.id"
                @click="deletePhotoPermanently(photo)"
              >
                <Loader2 v-if="deletingPhotoId === photo.id" class="h-3.5 w-3.5 animate-spin" />
                <span>{{ deletingPhotoId === photo.id ? 'Deleting…' : 'Delete' }}</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
