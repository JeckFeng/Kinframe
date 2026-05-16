<script setup lang="ts">
import { RefreshCw, RotateCcw } from 'lucide-vue-next'
import type { AdminJobItem } from '~/types/api'

const route = useRoute()
const { apiFetch } = useApi()
const { formatDate } = useFormat()

const jobs = ref<AdminJobItem[]>([])
const pending = ref(true)
const errorMessage = ref('')
const successMessage = ref('')
const retrying = ref<string | null>(null)
const statusFilter = ref('')
const jobTypeFilter = ref('')
const photoIdFilter = ref('')

const STATUS_LABELS: Record<string, string> = {
  pending: '等待处理',
  running: '处理中',
  succeeded: '已完成',
  failed: '失败',
}
const JOB_TYPE_LABELS: Record<string, string> = {
  photo_ingest: '照片入库',
  slide_design_generate: '幻灯片生成',
  reverse_geocode: '反向地理编码',
  vision_analyze: 'AI 视觉分析',
  caption_regenerate: '文案重生成',
  template_regenerate: '模板重生成',
  css_regenerate: '样式重生成',
  fallback_regenerate: '兜底重生成',
}

function formatJobStatus(status: string): string {
  return STATUS_LABELS[status] || status
}

function formatJobType(type: string): string {
  return JOB_TYPE_LABELS[type] || type
}

async function loadJobs() {
  pending.value = true
  errorMessage.value = ''
  try {
    const params = new URLSearchParams()
    if (statusFilter.value) params.set('status', statusFilter.value)
    if (jobTypeFilter.value) params.set('job_type', jobTypeFilter.value)
    if (photoIdFilter.value.trim()) params.set('photo_id', photoIdFilter.value.trim())
    const query = params.toString()
    jobs.value = await apiFetch<AdminJobItem[]>(`/admin/jobs${query ? `?${query}` : ''}`)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

async function retryJob(jobId: string) {
  retrying.value = jobId
  successMessage.value = ''
  errorMessage.value = ''
  try {
    await apiFetch(`/admin/jobs/${jobId}/retry`, { method: 'POST' })
    successMessage.value = `Job ${jobId.slice(0, 8)}… reset to pending`
    await loadJobs()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    retrying.value = null
  }
}

onMounted(() => {
  statusFilter.value = typeof route.query.status === 'string' ? route.query.status : ''
  jobTypeFilter.value = typeof route.query.job_type === 'string' ? route.query.job_type : ''
  photoIdFilter.value = typeof route.query.photo_id === 'string' ? route.query.photo_id : ''
  loadJobs()
})
</script>

<template>
  <section class="space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-semibold">Processing Jobs</h1>
        <p class="text-sm text-stone-600">{{ jobs.length }} jobs</p>
      </div>
      <button
        type="button"
        class="focus-ring inline-flex items-center gap-2 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
        @click="loadJobs"
      >
        <RefreshCw class="h-4 w-4" aria-hidden="true" />
        Refresh
      </button>
    </div>

    <div class="grid gap-3 rounded-lg border border-stone-200 bg-white p-4 shadow-sm md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.5fr)_auto]">
      <label class="space-y-1 text-sm">
        <span class="text-stone-600">Status</span>
        <select v-model="statusFilter" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-700">
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
        </select>
      </label>
      <label class="space-y-1 text-sm">
        <span class="text-stone-600">Job Type</span>
        <select v-model="jobTypeFilter" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-700">
          <option value="">All</option>
          <option value="photo_ingest">Photo Ingest</option>
          <option value="reverse_geocode">Reverse Geocode</option>
          <option value="vision_analyze">Vision Analyze</option>
          <option value="slide_design_generate">Slide Design</option>
          <option value="caption_regenerate">Caption Regenerate</option>
          <option value="template_regenerate">Template Regenerate</option>
          <option value="css_regenerate">CSS Regenerate</option>
          <option value="fallback_regenerate">Fallback Regenerate</option>
        </select>
      </label>
      <label class="space-y-1 text-sm">
        <span class="text-stone-600">Photo ID</span>
        <input
          v-model="photoIdFilter"
          type="text"
          class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-700"
          placeholder="Filter one photo"
          @keyup.enter="loadJobs"
        >
      </label>
      <button
        type="button"
        class="focus-ring inline-flex items-center justify-center rounded-md bg-moss px-3 py-2 text-sm font-medium text-white hover:bg-moss/90"
        @click="loadJobs"
      >
        Apply
      </button>
    </div>

    <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>
    <p v-if="successMessage" class="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
      {{ successMessage }}
    </p>

    <div class="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
      <table class="min-w-full divide-y divide-stone-200 text-sm">
        <thead class="bg-mist/50 text-left text-stone-700">
          <tr>
            <th class="px-3 py-3 font-semibold">Job ID</th>
            <th class="px-3 py-3 font-semibold">Type</th>
            <th class="px-3 py-3 font-semibold">Photo</th>
            <th class="px-3 py-3 font-semibold">Status</th>
            <th class="px-3 py-3 font-semibold">Attempts</th>
            <th class="px-3 py-3 font-semibold">AI</th>
            <th class="px-3 py-3 font-semibold">Error</th>
            <th class="px-3 py-3 font-semibold">Created</th>
            <th class="px-3 py-3 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-stone-100">
          <tr v-if="pending">
            <td class="px-3 py-4 text-stone-600" colspan="9">Loading jobs</td>
          </tr>
          <tr v-else-if="!jobs.length">
            <td class="px-3 py-4 text-stone-600" colspan="9">No jobs</td>
          </tr>
          <tr v-for="job in jobs" v-else :key="job.id" :class="job.status === 'failed' ? 'bg-red-50/40' : ''">
            <td class="px-3 py-3 font-mono text-xs">{{ job.id.slice(0, 8) }}…</td>
            <td class="px-3 py-3">{{ formatJobType(job.job_type) }}</td>
            <td class="px-3 py-3">
              <NuxtLink :to="`/photo/${job.photo_id}`" class="font-medium text-moss hover:underline">
                {{ job.photo_category }} ({{ job.photo_width }}x{{ job.photo_height }})
              </NuxtLink>
            </td>
            <td class="px-3 py-3">
              <span
                class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                :class="{
                  'bg-emerald-100 text-emerald-700': job.status === 'succeeded',
                  'bg-amber-100 text-amber-700': job.status === 'pending' || job.status === 'running',
                  'bg-red-100 text-red-700': job.status === 'failed',
                }"
              >
                {{ formatJobStatus(job.status) }}
              </span>
            </td>
            <td class="px-3 py-3">{{ job.attempts }} / {{ job.max_attempts }}</td>
            <td class="px-3 py-3 text-xs text-stone-600">
              <div v-if="job.ai_provider || job.ai_model">
                <p>{{ job.ai_provider || 'AI' }}</p>
                <p class="text-stone-500">{{ job.ai_model || job.ai_prompt_version || '-' }}</p>
              </div>
              <span v-else>-</span>
            </td>
            <td class="px-3 py-3 max-w-48 truncate text-xs text-red-600">{{ job.error_message || '-' }}</td>
            <td class="px-3 py-3 whitespace-nowrap">{{ formatDate(job.created_at) }}</td>
            <td class="px-3 py-3">
              <button
                v-if="job.status === 'failed' || job.status === 'succeeded'"
                type="button"
                class="focus-ring inline-flex items-center gap-1 rounded-md border border-stone-300 bg-white px-2 py-1 text-xs font-medium text-stone-700 hover:bg-mist/60 disabled:opacity-50"
                :disabled="retrying === job.id"
                @click="retryJob(job.id)"
              >
                <RotateCcw class="h-3 w-3" aria-hidden="true" />
                {{ retrying === job.id ? '…' : 'Retry' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
