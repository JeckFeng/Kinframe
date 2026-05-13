<script setup lang="ts">
import { Plus, Save, X } from 'lucide-vue-next'
import type { AdminCategory } from '~/types/api'

definePageMeta({ middleware: ['auth'] })

const { apiFetch } = useApi()
const { currentUser } = useAuth()

const categories = ref<AdminCategory[]>([])
const pending = ref(true)
const errorMessage = ref('')
const successMessage = ref('')
const showCreate = ref(false)
const editingId = ref<string | null>(null)

const createForm = reactive({ slug: '', name: '', description: '', sort_order: 100, is_active: true })
const editForm = reactive({ name: '', description: '', sort_order: 100, is_active: true })

async function loadCategories() {
  pending.value = true
  try {
    categories.value = await apiFetch<AdminCategory[]>('/admin/categories')
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

async function createCategory() {
  errorMessage.value = ''
  try {
    await apiFetch('/admin/categories', { method: 'POST', body: createForm })
    showCreate.value = false
    createForm.slug = ''
    createForm.name = ''
    createForm.description = ''
    createForm.sort_order = 100
    createForm.is_active = true
    successMessage.value = 'Category created'
    await loadCategories()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  }
}

function startEdit(cat: AdminCategory) {
  editingId.value = cat.id
  editForm.name = cat.name
  editForm.description = cat.description || ''
  editForm.sort_order = cat.sort_order
  editForm.is_active = cat.is_active
}

async function saveEdit() {
  if (!editingId.value) return
  errorMessage.value = ''
  try {
    await apiFetch(`/admin/categories/${editingId.value}`, { method: 'PATCH', body: editForm })
    editingId.value = null
    successMessage.value = 'Category updated'
    await loadCategories()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  }
}

function cancelEdit() {
  editingId.value = null
}

onMounted(loadCategories)
</script>

<template>
  <section class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">Category Management</h1>
      <button
        v-if="currentUser?.role === 'admin'"
        class="focus-ring inline-flex items-center gap-1.5 rounded-md bg-moss px-3 py-1.5 text-sm font-medium text-white hover:bg-moss/90"
        @click="showCreate = true"
      >
        <Plus class="h-4 w-4" /> New Category
      </button>
    </div>

    <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>
    <p v-if="successMessage" class="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
      {{ successMessage }}
    </p>

    <!-- Create dialog -->
    <div v-if="showCreate" class="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <h2 class="mb-3 text-sm font-semibold">Create Category</h2>
      <form class="space-y-3" @submit.prevent="createCategory">
        <label class="block">
          <span class="text-xs text-stone-600">Slug (immutable)</span>
          <input v-model="createForm.slug" class="focus-ring w-full rounded border border-stone-300 px-2 py-1 text-sm" required maxlength="50" />
        </label>
        <label class="block">
          <span class="text-xs text-stone-600">Name</span>
          <input v-model="createForm.name" class="focus-ring w-full rounded border border-stone-300 px-2 py-1 text-sm" required maxlength="100" />
        </label>
        <label class="block">
          <span class="text-xs text-stone-600">Description</span>
          <input v-model="createForm.description" class="focus-ring w-full rounded border border-stone-300 px-2 py-1 text-sm" />
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="block">
            <span class="text-xs text-stone-600">Sort Order</span>
            <input v-model.number="createForm.sort_order" type="number" class="focus-ring w-full rounded border border-stone-300 px-2 py-1 text-sm" />
          </label>
          <label class="flex items-center gap-2 pt-5">
            <input v-model="createForm.is_active" type="checkbox" class="rounded" />
            <span class="text-xs text-stone-600">Active</span>
          </label>
        </div>
        <div class="flex gap-2">
          <button type="submit" class="focus-ring rounded-md bg-moss px-3 py-1.5 text-sm text-white hover:bg-moss/90">Create</button>
          <button type="button" class="focus-ring rounded-md border border-stone-300 px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-100" @click="showCreate = false">Cancel</button>
        </div>
      </form>
    </div>

    <!-- Category list -->
    <div v-if="pending" class="rounded-lg border border-stone-200 bg-white p-6 text-center text-sm text-stone-600">
      Loading categories…
    </div>

    <div v-else class="overflow-hidden rounded-lg border border-stone-200 bg-white">
      <table class="w-full text-sm">
        <thead class="border-b bg-stone-50">
          <tr>
            <th class="px-4 py-2 text-left font-medium text-stone-600">Slug</th>
            <th class="px-4 py-2 text-left font-medium text-stone-600">Name</th>
            <th class="px-4 py-2 text-left font-medium text-stone-600">Sort</th>
            <th class="px-4 py-2 text-left font-medium text-stone-600">Active</th>
            <th class="px-4 py-2 text-left font-medium text-stone-600">Legacy</th>
            <th class="px-4 py-2 text-right font-medium text-stone-600">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="cat in categories"
            :key="cat.id"
            class="border-b last:border-b-0 hover:bg-stone-50"
          >
            <td class="px-4 py-2 font-mono text-xs">{{ cat.slug }}</td>
            <td class="px-4 py-2">
              <template v-if="editingId === cat.id">
                <input v-model="editForm.name" class="focus-ring w-full rounded border border-stone-300 px-2 py-0.5 text-sm" maxlength="100" />
              </template>
              <template v-else>{{ cat.name }}</template>
            </td>
            <td class="px-4 py-2">
              <template v-if="editingId === cat.id">
                <input v-model.number="editForm.sort_order" type="number" class="focus-ring w-16 rounded border border-stone-300 px-2 py-0.5 text-sm" />
              </template>
              <template v-else>{{ cat.sort_order }}</template>
            </td>
            <td class="px-4 py-2">
              <template v-if="editingId === cat.id">
                <input v-model="editForm.is_active" type="checkbox" class="rounded" />
              </template>
              <template v-else>
                <span :class="cat.is_active ? 'text-emerald-600' : 'text-stone-400'">{{ cat.is_active ? 'Yes' : 'No' }}</span>
              </template>
            </td>
            <td class="px-4 py-2 text-xs text-stone-400">{{ cat.legacy_slug || '—' }}</td>
            <td class="px-4 py-2 text-right">
              <template v-if="editingId === cat.id">
                <div class="flex items-center justify-end gap-1">
                  <button class="rounded p-1 text-emerald-600 hover:bg-emerald-50" title="Save" @click="saveEdit">
                    <Save class="h-3.5 w-3.5" />
                  </button>
                  <button class="rounded p-1 text-stone-400 hover:bg-stone-100" title="Cancel" @click="cancelEdit">
                    <X class="h-3.5 w-3.5" />
                  </button>
                </div>
              </template>
              <template v-else>
                <button class="rounded px-2 py-0.5 text-xs text-stone-600 hover:bg-stone-200" @click="startEdit(cat)">
                  Edit
                </button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
