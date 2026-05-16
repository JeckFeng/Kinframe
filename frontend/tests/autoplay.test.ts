import { describe, expect, it, vi, afterEach } from 'vitest'
import { useAutoPlay } from '~/composables/useAutoPlay'

describe('useAutoPlay — toggle and state', () => {
  it('starts in paused state', () => {
    const { isAutoPlaying } = useAutoPlay({ onAdvance: vi.fn() })
    expect(isAutoPlaying.value).toBe(false)
  })

  it('toggleAutoPlay starts auto-play when paused', () => {
    const onAdvance = vi.fn()
    const { isAutoPlaying, toggleAutoPlay, stopAutoPlay } = useAutoPlay({ onAdvance })

    toggleAutoPlay()
    expect(isAutoPlaying.value).toBe(true)

    stopAutoPlay()
  })

  it('toggleAutoPlay pauses when auto-play is running', () => {
    const onAdvance = vi.fn()
    const { isAutoPlaying, toggleAutoPlay, stopAutoPlay } = useAutoPlay({ onAdvance })

    toggleAutoPlay()
    expect(isAutoPlaying.value).toBe(true)
    toggleAutoPlay()
    expect(isAutoPlaying.value).toBe(false)

    stopAutoPlay()
  })

  it('startAutoPlay sets isAutoPlaying to true', () => {
    const onAdvance = vi.fn()
    const { isAutoPlaying, startAutoPlay, stopAutoPlay } = useAutoPlay({ onAdvance })

    startAutoPlay()
    expect(isAutoPlaying.value).toBe(true)

    stopAutoPlay()
  })

  it('stopAutoPlay sets isAutoPlaying to false', () => {
    const onAdvance = vi.fn()
    const { isAutoPlaying, startAutoPlay, stopAutoPlay } = useAutoPlay({ onAdvance })

    startAutoPlay()
    stopAutoPlay()
    expect(isAutoPlaying.value).toBe(false)
  })
})

describe('useAutoPlay — timer behavior', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('calls onAdvance at the configured interval', () => {
    vi.useFakeTimers()
    const onAdvance = vi.fn()
    const { startAutoPlay, stopAutoPlay } = useAutoPlay({ onAdvance, defaultInterval: 5000 })

    startAutoPlay()
    vi.advanceTimersByTime(5000)
    expect(onAdvance).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(5000)
    expect(onAdvance).toHaveBeenCalledTimes(2)

    stopAutoPlay()
    vi.useRealTimers()
  })

  it('does not call onAdvance after stopAutoPlay', () => {
    vi.useFakeTimers()
    const onAdvance = vi.fn()
    const { startAutoPlay, stopAutoPlay } = useAutoPlay({ onAdvance })

    startAutoPlay()
    vi.advanceTimersByTime(5000)
    expect(onAdvance).toHaveBeenCalledTimes(1)

    stopAutoPlay()
    vi.advanceTimersByTime(10000)
    expect(onAdvance).toHaveBeenCalledTimes(1)

    vi.useRealTimers()
  })

  it('restarts timer when interval changes during play', () => {
    vi.useFakeTimers()
    const onAdvance = vi.fn()
    const { startAutoPlay, setAutoPlayInterval, stopAutoPlay } = useAutoPlay({
      onAdvance,
      defaultInterval: 5000,
    })

    startAutoPlay()
    vi.advanceTimersByTime(3000)
    setAutoPlayInterval(3000)
    // timer restarted, so no call yet
    vi.advanceTimersByTime(2500)
    expect(onAdvance).toHaveBeenCalledTimes(0)
    vi.advanceTimersByTime(500)
    expect(onAdvance).toHaveBeenCalledTimes(1)

    stopAutoPlay()
    vi.useRealTimers()
  })

  it('defaults interval to 5000ms', () => {
    const { autoPlayInterval } = useAutoPlay({ onAdvance: vi.fn() })
    expect(autoPlayInterval.value).toBe(5000)
  })

  it('cleans up timer on stopAutoPlay', () => {
    const onAdvance = vi.fn()
    const { startAutoPlay, stopAutoPlay, autoPlayTimer } = useAutoPlay({ onAdvance })

    startAutoPlay()
    expect(autoPlayTimer.value).not.toBeNull()
    stopAutoPlay()
    expect(autoPlayTimer.value).toBeNull()
  })
})
