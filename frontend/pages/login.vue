<script setup lang="ts">
import { LogIn, X } from 'lucide-vue-next'

const { currentUser, loadMe, login } = useAuth()
const username = ref('')
const password = ref('')
const errorMessage = ref('')
const pending = ref(false)
const hydrated = ref(false)
const isLoading = ref(true)
const isDialogOpen = ref(false)

if (!currentUser.value) {
  await loadMe()
}

if (currentUser.value) {
  await navigateTo('/showcase')
}

let smoother: { kill: () => void } | null = null

async function initSmoother() {
  if (!import.meta.client || smoother || isLoading.value) {
    return
  }

  await nextTick()

  const [{ default: gsap }, { ScrollTrigger }, { ScrollSmoother }] = await Promise.all([
    import('../vendor/gsap/index.js'),
    import('../vendor/gsap/ScrollTrigger.js'),
    import('../vendor/gsap/ScrollSmoother.js'),
  ])

  gsap.registerPlugin(ScrollTrigger, ScrollSmoother)

  smoother = ScrollSmoother.create({
    wrapper: '.login-parallax-wrapper',
    content: '.login-parallax-content',
    smooth: 2,
    effects: true,
  })
}

async function handleWindowLoad() {
  isLoading.value = false
  await initSmoother()
}

function openDialog() {
  isDialogOpen.value = true
}

function closeDialog() {
  if (pending.value) {
    return
  }

  isDialogOpen.value = false
}

onMounted(() => {
  hydrated.value = true

  if (document.readyState === 'complete') {
    void handleWindowLoad()
    return
  }

  window.addEventListener('load', handleWindowLoad, { once: true })
})

onBeforeUnmount(() => {
  if (import.meta.client) {
    window.removeEventListener('load', handleWindowLoad)
  }

  smoother?.kill()
  smoother = null
})

async function submitLogin() {
  errorMessage.value = ''
  pending.value = true
  try {
    await login(username.value, password.value)
    isDialogOpen.value = false
    await navigateTo('/showcase')
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error)
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-black text-[#e7e7e0]">
    <div v-if="isLoading" class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/90 text-white">
      <div class="flex flex-col items-center gap-4">
        <p class="text-2xl font-medium tracking-wide">Loading...</p>
      </div>
    </div>

    <div v-else class="login-parallax-wrapper">
      <div class="login-parallax-content">
        <header class="relative flex h-screen items-center justify-center overflow-hidden text-center">
          <div class="relative flex h-full w-full items-center justify-center">
            <div
              data-speed="0.55"
              class="z-10 text-[#e7e7e0] uppercase drop-shadow-[0_0_15px_#9d822b]"
            >
              <div class="mt-[-clamp(1rem,1vw+1vh,2rem)] text-[clamp(1rem,1vw+1vh,2rem)] tracking-[clamp(0.2rem,(1vw+1vh)/3.5,1rem)]">
                Welcome to Parallax
              </div>
              <div class="-translate-y-4 text-[clamp(2rem,(1vw+1vh)*2.5,6rem)] tracking-[clamp(0.5rem,(1vw+1vh)/2.25,2rem)]">
                Fairy Forest
              </div>
            </div>

            <div
              data-speed="0.5"
              class="absolute inset-0 z-0 bg-cover bg-center"
              style="background-image: url('/login-parallax/layer-base.png')"
            />
            <div
              data-speed="0.67"
              class="absolute inset-0 z-20 bg-cover bg-center"
              style="background-image: url('/login-parallax/layer-middle.png')"
            />
            <div
              data-speed="0.9"
              class="absolute inset-0 z-30 bg-cover bg-center"
              style="background-image: url('/login-parallax/layer-front.png')"
            />
          </div>
        </header>

        <article
          class="relative flex min-h-screen flex-col items-center justify-center bg-cover bg-center bg-no-repeat text-center text-[#e7e7e0]"
          style="background-image: url('/login-parallax/dungeon.jpg')"
        >
          <div
            class="absolute -top-36 left-0 z-[99] h-[calc((1vw+1vh)*10)] w-full bg-cover bg-center bg-no-repeat"
            style="background-image: url('/login-parallax/ground.png')"
          />

          <div class="article__content relative z-[120]">
            <button
              type="button"
              class="focus-ring inline-flex min-h-[84px] min-w-[260px] items-center justify-center border border-[#d1bf82] bg-black/55 px-12 text-[clamp(1.1rem,(1vw+1vh),1.7rem)] uppercase tracking-[0.22em] text-[#f0ead1] shadow-[0_0_35px_rgba(157,130,43,0.28)] transition hover:bg-black/72"
              @click="openDialog"
            >
              Login
            </button>
          </div>
        </article>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="isDialogOpen"
        class="fixed inset-0 z-[10000] flex items-center justify-center bg-black/72 px-4 backdrop-blur-sm"
        @click.self="closeDialog"
      >
        <form class="w-full max-w-sm rounded-lg border border-stone-200 bg-white p-6 text-ink shadow-2xl" @submit.prevent="submitLogin">
          <div class="mb-6 flex items-start justify-between gap-4">
            <div class="flex items-center gap-2">
              <div class="flex h-10 w-10 items-center justify-center rounded-md bg-moss text-white">
                <LogIn class="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h1 class="text-xl font-normal">KinFrame</h1>
                <p class="text-sm text-stone-600">Sign in</p>
              </div>
            </div>

            <button
              type="button"
              class="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-800"
              aria-label="Close login dialog"
              :disabled="pending"
              @click="closeDialog"
            >
              <X class="h-4 w-4" aria-hidden="true" />
            </button>
          </div>

          <label class="mb-4 block">
            <span class="mb-1 block text-sm font-normal text-stone-700">Username</span>
            <input
              v-model="username"
              class="focus-ring w-full rounded-md border border-stone-300 bg-white px-3 py-2"
              autocomplete="username"
              required
            >
          </label>

          <label class="mb-4 block">
            <span class="mb-1 block text-sm font-normal text-stone-700">Password</span>
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
            class="focus-ring inline-flex w-full items-center justify-center gap-2 rounded-md bg-moss px-4 py-2 font-normal text-white hover:bg-moss/90 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="pending || !hydrated"
          >
            <LogIn class="h-4 w-4" aria-hidden="true" />
            {{ pending ? 'Signing in' : 'Sign in' }}
          </button>
        </form>
      </div>
    </Teleport>
  </div>
</template>
