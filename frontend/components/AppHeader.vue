<script setup lang="ts">
import { FolderCog, Images, ListTodo, LogOut, Upload, Users } from 'lucide-vue-next'

const { currentUser, loadMe, logout } = useAuth()

onMounted(async () => {
  if (!currentUser.value) {
    await loadMe()
  }
})
</script>

<template>
  <header class="border-b border-stone-200 bg-paper/95">
    <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
      <NuxtLink to="/showcase" class="flex items-center gap-2 text-lg font-semibold text-ink">
        <Images class="h-5 w-5 text-moss" aria-hidden="true" />
        <span>KinFrame</span>
      </NuxtLink>

      <nav class="flex items-center gap-2">
        <NuxtLink
          to="/showcase"
          class="focus-ring rounded-md px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
        >
          Showcase
        </NuxtLink>
        <NuxtLink
          to="/gallery"
          class="focus-ring rounded-md px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
        >
          Gallery
        </NuxtLink>
        <NuxtLink
          to="/upload"
          class="focus-ring inline-flex items-center gap-2 rounded-md bg-moss px-3 py-2 text-sm font-medium text-white hover:bg-moss/90"
        >
          <Upload class="h-4 w-4" aria-hidden="true" />
          Upload
        </NuxtLink>
        <NuxtLink
          v-if="currentUser?.role === 'admin'"
          to="/admin/photos"
          class="focus-ring inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
        >
          <Images class="h-4 w-4" aria-hidden="true" />
          Photos
        </NuxtLink>
        <NuxtLink
          v-if="currentUser?.role === 'admin'"
          to="/admin/users"
          class="focus-ring inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
        >
          <Users class="h-4 w-4" aria-hidden="true" />
          Users
        </NuxtLink>
        <NuxtLink
          v-if="currentUser?.role === 'admin'"
          to="/admin/jobs"
          class="focus-ring inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
        >
          <ListTodo class="h-4 w-4" aria-hidden="true" />
          Jobs
        </NuxtLink>
        <NuxtLink
          v-if="currentUser?.role === 'admin'"
          to="/admin/categories"
          class="focus-ring inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-stone-700 hover:bg-mist/60"
        >
          <FolderCog class="h-4 w-4" aria-hidden="true" />
          Categories
        </NuxtLink>
        <button
          v-if="currentUser"
          type="button"
          class="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md text-stone-700 hover:bg-mist/60"
          title="Log out"
          @click="logout"
        >
          <LogOut class="h-4 w-4" aria-hidden="true" />
        </button>
      </nav>
    </div>
  </header>
</template>
