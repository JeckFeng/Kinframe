import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { useSlideNavigation } from '~/composables/useSlideNavigation'

type TransitionDirection = 'next-photo' | 'prev-photo' | 'next-category' | 'prev-category' | 'initial'

describe('useSlideNavigation — transitionName', () => {
  it('returns kf-photo-next for next-photo direction', () => {
    const { getTransitionName } = useSlideNavigation()
    expect(getTransitionName('next-photo')).toBe('kf-photo-next')
  })

  it('returns kf-photo-prev for prev-photo direction', () => {
    const { getTransitionName } = useSlideNavigation()
    expect(getTransitionName('prev-photo')).toBe('kf-photo-prev')
  })

  it('returns kf-category-next for next-category direction', () => {
    const { getTransitionName } = useSlideNavigation()
    expect(getTransitionName('next-category')).toBe('kf-category-next')
  })

  it('returns kf-category-prev for prev-category direction', () => {
    const { getTransitionName } = useSlideNavigation()
    expect(getTransitionName('prev-category')).toBe('kf-category-prev')
  })

  it('returns kf-fade for initial direction', () => {
    const { getTransitionName } = useSlideNavigation()
    expect(getTransitionName('initial')).toBe('kf-fade')
  })
})

describe('useSlideNavigation — formatPosition', () => {
  it('formats position as "第 N/M 张" for middle position', () => {
    const { formatPosition } = useSlideNavigation()
    expect(formatPosition(2, 10)).toBe('第 3/10 张')
  })

  it('formats first photo correctly', () => {
    const { formatPosition } = useSlideNavigation()
    expect(formatPosition(0, 28)).toBe('第 1/28 张')
  })

  it('formats last photo correctly', () => {
    const { formatPosition } = useSlideNavigation()
    expect(formatPosition(27, 28)).toBe('第 28/28 张')
  })

  it('formats single photo correctly', () => {
    const { formatPosition } = useSlideNavigation()
    expect(formatPosition(0, 1)).toBe('第 1/1 张')
  })

  it('returns empty string for empty category', () => {
    const { formatPosition } = useSlideNavigation()
    expect(formatPosition(0, 0)).toBe('')
  })
})

describe('useSlideNavigation — emptyStateMessage', () => {
  it('returns the prescribed empty state message', () => {
    const { emptyStateMessage } = useSlideNavigation()
    expect(emptyStateMessage('摄影')).toBe('摄影分类还在等待第一张照片。')
  })
})

describe('useSlideNavigation — reducedMotion', () => {
  let originalMatchMedia: typeof window.matchMedia

  beforeEach(() => {
    originalMatchMedia = window.matchMedia
  })

  afterEach(() => {
    window.matchMedia = originalMatchMedia
  })

  it('detects reduced motion preference', () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))

    const { prefersReducedMotion } = useSlideNavigation()
    expect(prefersReducedMotion.value).toBe(true)
  })

  it('detects no reduced motion preference', () => {
    window.matchMedia = vi.fn().mockImplementation((_query: string) => ({
      matches: false,
      media: _query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))

    const { prefersReducedMotion } = useSlideNavigation()
    expect(prefersReducedMotion.value).toBe(false)
  })
})
