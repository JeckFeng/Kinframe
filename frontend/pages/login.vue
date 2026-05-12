<script setup lang="ts">
import { LogIn } from 'lucide-vue-next'

const username = ref('')
const password = ref('')
const errorMessage = ref('')
const pending = ref(false)
const { login } = useAuth()

async function submitLogin() {
  errorMessage.value = ''
  pending.value = true
  try {
    await login(username.value, password.value)
    await navigateTo('/showcase')
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="flex min-h-[calc(100vh-3rem)] items-center justify-center">
    <form class="w-full max-w-sm rounded-lg border border-stone-200 bg-white p-6 shadow-sm" @submit.prevent="submitLogin">
      <div class="mb-6 flex items-center gap-2">
        <div class="flex h-10 w-10 items-center justify-center rounded-md bg-moss text-white">
          <LogIn class="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <h1 class="text-xl font-semibold">KinFrame</h1>
          <p class="text-sm text-stone-600">Sign in</p>
        </div>
      </div>

      <label class="mb-4 block">
        <span class="mb-1 block text-sm font-medium text-stone-700">Username</span>
        <input
          v-model="username"
          class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2"
          autocomplete="username"
          required
        >
      </label>

      <label class="mb-4 block">
        <span class="mb-1 block text-sm font-medium text-stone-700">Password</span>
        <input
          v-model="password"
          class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2"
          type="password"
          autocomplete="current-password"
          required
        >
      </label>

      <p v-if="errorMessage" class="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ errorMessage }}
      </p>

      <button
        type="submit"
        class="focus-ring inline-flex w-full items-center justify-center gap-2 rounded-md bg-moss px-4 py-2 font-medium text-white hover:bg-moss/90 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="pending"
      >
        <LogIn class="h-4 w-4" aria-hidden="true" />
        {{ pending ? 'Signing in' : 'Sign in' }}
      </button>
    </form>
  </div>
</template>
