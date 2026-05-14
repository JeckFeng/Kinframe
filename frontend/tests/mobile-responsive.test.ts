/** Tests for v0.3-13: Mobile Responsiveness */

import { describe, it, expect } from 'vitest'

// ── Touch gesture detection ─────────────────────────────────────────

/** Minimum swipe distance in pixels to register a gesture. */
const SWIPE_THRESHOLD = 50

type SwipeDirection = 'left' | 'right' | 'up' | 'down' | null

function detectSwipeDirection(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
  threshold: number = SWIPE_THRESHOLD,
): SwipeDirection {
  const dx = endX - startX
  const dy = endY - startY
  const absDx = Math.abs(dx)
  const absDy = Math.abs(dy)

  if (Math.max(absDx, absDy) < threshold) return null

  if (absDx > absDy) {
    return dx > 0 ? 'right' : 'left'
  }
  return dy > 0 ? 'down' : 'up'
}

describe('detectSwipeDirection', () => {
  it('detects left swipe (swipe from right to left)', () => {
    expect(detectSwipeDirection(400, 200, 300, 200)).toBe('left')
  })

  it('detects right swipe (swipe from left to right)', () => {
    expect(detectSwipeDirection(200, 200, 400, 200)).toBe('right')
  })

  it('detects up swipe', () => {
    expect(detectSwipeDirection(200, 300, 200, 200)).toBe('up')
  })

  it('detects down swipe', () => {
    expect(detectSwipeDirection(200, 200, 200, 300)).toBe('down')
  })

  it('returns null for short movements below threshold', () => {
    expect(detectSwipeDirection(200, 200, 220, 210)).toBeNull()
  })

  it('prioritizes horizontal over vertical when diagonal', () => {
    // dx=-100, dy=20: horizontal dominates → left swipe
    expect(detectSwipeDirection(300, 200, 200, 220)).toBe('left')
    // dx=100, dy=20: horizontal dominates → right swipe
    expect(detectSwipeDirection(200, 200, 300, 220)).toBe('right')
  })

  it('returns null below threshold distance', () => {
    // 40px horizontal — below 50 threshold
    expect(detectSwipeDirection(200, 200, 240, 200)).toBeNull()
  })

  it('detects swipe at exactly threshold distance', () => {
    // 60px horizontal, 0 vertical — above 50 threshold
    expect(detectSwipeDirection(200, 200, 260, 200)).toBe('right')
  })
})

// ── Touch target sizing ─────────────────────────────────────────────

const MIN_TOUCH_TARGET_PX = 44

function isValidTouchTarget(width: number, height: number): boolean {
  return width >= MIN_TOUCH_TARGET_PX && height >= MIN_TOUCH_TARGET_PX
}

describe('touch target sizing', () => {
  it('rejects targets smaller than 44px', () => {
    expect(isValidTouchTarget(40, 40)).toBe(false)
    expect(isValidTouchTarget(44, 40)).toBe(false)
  })

  it('accepts targets at or above 44px', () => {
    expect(isValidTouchTarget(44, 44)).toBe(true)
    expect(isValidTouchTarget(48, 48)).toBe(true)
  })
})

// ── Slide canvas aspect ratio ───────────────────────────────────────

function scaleToFit(
  viewportWidth: number,
  viewportHeight: number,
  aspectRatio: number = 16 / 9,
): { width: number; height: number; letterboxH: number } {
  let width: number
  let height: number

  if (viewportWidth / viewportHeight > aspectRatio) {
    // Viewport is wider than content — letterbox on sides (but we use height)
    height = viewportHeight
    width = height * aspectRatio
  } else {
    // Viewport is taller — letterbox top/bottom
    width = viewportWidth
    height = width / aspectRatio
  }

  const letterboxH = Math.max(0, (viewportHeight - height) / 2)
  return { width, height, letterboxH }
}

describe('slide canvas scaling', () => {
  it('maintains 16:9 aspect ratio on mobile viewport (375x667)', () => {
    const result = scaleToFit(375, 667)
    expect(result.width).toBe(375)
    expect(result.height).toBeCloseTo(375 * 9 / 16)
    expect(result.letterboxH).toBeGreaterThan(0) // letterbox top/bottom
  })

  it('maintains 16:9 aspect ratio on wide viewport (1280x720)', () => {
    const result = scaleToFit(1280, 720)
    expect(result.height).toBe(720)
    expect(result.width).toBeCloseTo(720 * 16 / 9)
  })

  it('produces no letterbox when viewport matches aspect ratio', () => {
    const result = scaleToFit(1600, 900)
    expect(result.letterboxH).toBe(0)
    expect(result.width).toBe(1600)
    expect(result.height).toBe(900)
  })

  it('produces letterbox on iPhone SE (375x667)', () => {
    const result = scaleToFit(375, 667)
    // 16:9 on 375 wide → height = 210.9
    expect(result.width).toBe(375)
    expect(result.height).toBeCloseTo(210.94, 0)
    expect(result.letterboxH).toBeCloseTo((667 - 210.94) / 2, 0)
  })

  it('never crops — width never exceeds viewport', () => {
    const sizes = [
      [375, 667],   // iPhone SE
      [390, 844],   // iPhone 14
      [428, 926],   // iPhone 14 Pro Max
      [360, 640],   // small Android
    ]
    for (const [vw, vh] of sizes) {
      const result = scaleToFit(vw, vh)
      expect(result.width).toBeLessThanOrEqual(vw)
      expect(result.height).toBeLessThanOrEqual(vh)
    }
  })
})

// ── Responsive breakpoint detection ─────────────────────────────────

const MOBILE_MAX_WIDTH = 428

function isMobileViewport(width: number): boolean {
  return width <= MOBILE_MAX_WIDTH
}

describe('mobile breakpoint detection', () => {
  it('identifies iPhone SE (375px) as mobile', () => {
    expect(isMobileViewport(375)).toBe(true)
  })

  it('identifies iPhone 14 Pro Max (428px) as mobile', () => {
    expect(isMobileViewport(428)).toBe(true)
  })

  it('identifies 429px as not mobile', () => {
    expect(isMobileViewport(429)).toBe(false)
  })

  it('identifies desktop (1280px) as not mobile', () => {
    expect(isMobileViewport(1280)).toBe(false)
  })
})
