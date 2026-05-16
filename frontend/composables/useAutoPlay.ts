import { ref, onUnmounted, type Ref } from 'vue'

export interface AutoPlayOptions {
  onAdvance: () => void
  defaultInterval?: number
}

export interface AutoPlayState {
  isAutoPlaying: Ref<boolean>
  autoPlayInterval: Ref<number>
  autoPlayTimer: Ref<ReturnType<typeof setInterval> | null>
  toggleAutoPlay: () => void
  startAutoPlay: () => void
  stopAutoPlay: () => void
  setAutoPlayInterval: (ms: number) => void
}

export function useAutoPlay(options: AutoPlayOptions): AutoPlayState {
  const { onAdvance, defaultInterval = 5000 } = options

  const isAutoPlaying = ref(false)
  const autoPlayInterval = ref(defaultInterval)
  const autoPlayTimer = ref<ReturnType<typeof setInterval> | null>(null)

  function startAutoPlay() {
    isAutoPlaying.value = true
    autoPlayTimer.value = setInterval(() => {
      onAdvance()
    }, autoPlayInterval.value)
  }

  function stopAutoPlay() {
    isAutoPlaying.value = false
    if (autoPlayTimer.value) {
      clearInterval(autoPlayTimer.value)
      autoPlayTimer.value = null
    }
  }

  function toggleAutoPlay() {
    if (isAutoPlaying.value) {
      stopAutoPlay()
    } else {
      startAutoPlay()
    }
  }

  function setAutoPlayInterval(ms: number) {
    autoPlayInterval.value = ms
    if (isAutoPlaying.value) {
      stopAutoPlay()
      startAutoPlay()
    }
  }

  onUnmounted(() => {
    if (autoPlayTimer.value) {
      clearInterval(autoPlayTimer.value)
    }
  })

  return {
    isAutoPlaying,
    autoPlayInterval,
    autoPlayTimer,
    toggleAutoPlay,
    startAutoPlay,
    stopAutoPlay,
    setAutoPlayInterval,
  }
}
