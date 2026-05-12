<script setup lang="ts">
import { Plus, RefreshCw } from 'lucide-vue-next'
import type { User, UserRole } from '~/types/api'

const { apiFetch } = useApi()
const users = ref<User[]>([])
const errorMessage = ref('')
const successMessage = ref('')
const pending = ref(true)
const creating = ref(false)

const form = reactive({
  username: '',
  display_name: '',
  password: '',
  role: 'member' as UserRole,
})

async function loadUsers() {
  pending.value = true
  errorMessage.value = ''
  try {
    users.value = await apiFetch<User[]>('/admin/users')
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}

async function createUser() {
  creating.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await apiFetch<User>('/admin/users', {
      method: 'POST',
      body: { ...form },
    })
    successMessage.value = 'User created'
    form.username = ''
    form.display_name = ''
    form.password = ''
    form.role = 'member'
    await loadUsers()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    creating.value = false
  }
}

onMounted(loadUsers)
</script>

<template>
  <section class="space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-semibold">Users</h1>
        <p class="text-sm text-stone-600">{{ users.length }} accounts</p>
      </div>
      <button
        type="button"
        class="focus-ring inline-flex items-center gap-2 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
        @click="loadUsers"
      >
        <RefreshCw class="h-4 w-4" aria-hidden="true" />
        Refresh
      </button>
    </div>

    <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>
    <p v-if="successMessage" class="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
      {{ successMessage }}
    </p>

    <form class="grid gap-4 rounded-lg border border-stone-200 bg-white p-4 shadow-sm md:grid-cols-5" @submit.prevent="createUser">
      <label class="block">
        <span class="mb-1 block text-sm font-medium text-stone-700">Username</span>
        <input v-model="form.username" class="focus-ring w-full rounded-md border border-stone-300 px-3 py-2" required>
      </label>
      <label class="block">
        <span class="mb-1 block text-sm font-medium text-stone-700">Display name</span>
        <input v-model="form.display_name" class="focus-ring w-full rounded-md border border-stone-300 px-3 py-2" required>
      </label>
      <label class="block">
        <span class="mb-1 block text-sm font-medium text-stone-700">Password</span>
        <input v-model="form.password" class="focus-ring w-full rounded-md border border-stone-300 px-3 py-2" type="password" required minlength="8">
      </label>
      <label class="block">
        <span class="mb-1 block text-sm font-medium text-stone-700">Role</span>
        <select v-model="form.role" class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2">
          <option value="member">Member</option>
          <option value="admin">Admin</option>
        </select>
      </label>
      <div class="flex items-end">
        <button
          type="submit"
          class="focus-ring inline-flex w-full items-center justify-center gap-2 rounded-md bg-moss px-4 py-2 font-medium text-white hover:bg-moss/90 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="creating"
        >
          <Plus class="h-4 w-4" aria-hidden="true" />
          {{ creating ? 'Creating' : 'Create' }}
        </button>
      </div>
    </form>

    <div class="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
      <table class="min-w-full divide-y divide-stone-200 text-sm">
        <thead class="bg-mist/50 text-left text-stone-700">
          <tr>
            <th class="px-4 py-3 font-semibold">Username</th>
            <th class="px-4 py-3 font-semibold">Display name</th>
            <th class="px-4 py-3 font-semibold">Role</th>
            <th class="px-4 py-3 font-semibold">Status</th>
            <th class="px-4 py-3 font-semibold">Last login</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-stone-100">
          <tr v-if="pending">
            <td class="px-4 py-4 text-stone-600" colspan="5">Loading users</td>
          </tr>
          <tr v-for="user in users" v-else :key="user.id">
            <td class="px-4 py-3 font-medium">{{ user.username }}</td>
            <td class="px-4 py-3">{{ user.display_name }}</td>
            <td class="px-4 py-3 capitalize">{{ user.role }}</td>
            <td class="px-4 py-3">{{ user.is_active ? 'Active' : 'Inactive' }}</td>
            <td class="px-4 py-3">{{ user.last_login_at || 'Never' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
