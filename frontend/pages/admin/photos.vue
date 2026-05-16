<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next'
import type { AdminCategory, AdminPhotoListItem, AdminPhotoListResponse } from '~/types/api'

const { apiFetch } = useApi()
const { formatDate } = useFormat()

const photos = ref<AdminPhotoListItem[]>([])
const categories = ref<AdminCategory[]>([])
const pending = ref(true)
const errorMessage = ref('')

const categoryFilter = ref('')
const geocodingFilter = ref('')
const aiStatusFilter = ref('')
const designSourceFilter = ref('')
const failedOnly = ref(false)
const needsReview = ref(false)

async function loadPhotos() {
  pending.value = true
  errorMessage.value = ''
  try {
    const params = new URLSearchParams()
    if (categoryFilter.value) params.set('category', categoryFilter.value)
    if (geocodingFilter.value) params.set('geocoding_status', geocodingFilter.value)
    if (aiStatusFilter.value) params.set('ai_status', aiStatusFilter.value)
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

function formatAiStatus(status: string) {
  if (status === 'analyzed') return 'Analyzed'
  if (status === 'failed') return 'Failed'
  return 'Missing'
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
        <span class="text-stone-600">AI Status</span>
        <select v-model="aiStatusFilter" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
          <option value="">All</option>
          <option value="analyzed">Analyzed</option>
          <option value="failed">Failed</option>
          <option value="missing">Missing</option>
        </select>
      </label>
      <label class="space-y-1 text-sm">
        <span class="text-stone-600">Design Source</span>
        <select v-model="designSourceFilter" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
          <option value="">All</option>
          <option value="fallback">Fallback</option>
          <option value="ai">AI</option>
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
      <div class="lg:col-span-6 flex gap-2">
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
          @click="categoryFilter = ''; geocodingFilter = ''; aiStatusFilter = ''; designSourceFilter = ''; failedOnly = false; needsReview = false; loadPhotos()"
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
            <th class="px-3 py-3 font-semibold">AI</th>
            <th class="px-3 py-3 font-semibold">Design</th>
            <th class="px-3 py-3 font-semibold">Geocoding</th>
            <th class="px-3 py-3 font-semibold">Latest Job</th>
            <th class="px-3 py-3 font-semibold">Taken</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-stone-100">
          <tr v-if="pending">
            <td class="px-3 py-4 text-stone-600" colspan="8">Loading photos</td>
          </tr>
          <tr v-else-if="!photos.length">
            <td class="px-3 py-4 text-stone-600" colspan="8">No matching photos</td>
          </tr>
          <tr v-for="photo in photos" v-else :key="photo.id" :class="photo.has_failed_jobs ? 'bg-red-50/30' : photo.needs_review ? 'bg-amber-50/30' : ''">
            <td class="px-3 py-3">
              <NuxtLink :to="`/photo/${photo.id}`" class="font-mono text-xs text-moss hover:underline">
                {{ photo.id.slice(0, 8) }}…
              </NuxtLink>
            </td>
            <td class="px-3 py-3 max-w-56 truncate text-stone-700">{{ photo.final_caption || photo.user_message || '-' }}</td>
            <td class="px-3 py-3">{{ photo.category }}</td>
            <td class="px-3 py-3">
              <span
                class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                :class="{
                  'bg-emerald-100 text-emerald-700': photo.ai_status === 'analyzed',
                  'bg-red-100 text-red-700': photo.ai_status === 'failed',
                  'bg-stone-100 text-stone-600': photo.ai_status === 'missing',
                }"
              >
                {{ formatAiStatus(photo.ai_status) }}
              </span>
            </td>
            <td class="px-3 py-3 text-xs text-stone-700">
              <p>{{ photo.active_design_source || 'none' }}</p>
              <p class="text-stone-500">v{{ photo.active_design_version || 0 }}</p>
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
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
