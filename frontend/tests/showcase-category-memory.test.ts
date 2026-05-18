import { describe, expect, it } from 'vitest'
import { useShowcaseCategoryMemory } from '~/composables/useShowcaseCategoryMemory'
import type { ShowcaseCategoryMemoryEntry } from '~/types/showcase'

function makeEntry(category: 'life' | 'photography' | 'pet', activeIndex: number): ShowcaseCategoryMemoryEntry {
  return {
    category,
    activeIndex,
    snapshot: {
      currentX: 120,
      targetX: 180,
      activeIndex,
      activePhotoId: `${category}-${activeIndex}`,
      itemPitchPx: 320,
      loopSpanPx: 1280,
      timestamp: 1715942400000,
    },
    updatedAt: 1715942400000,
  }
}

describe('useShowcaseCategoryMemory', () => {
  it('stores and restores snapshots independently per category', () => {
    const memory = useShowcaseCategoryMemory()

    memory.save('life', makeEntry('life', 2))
    memory.save('pet', makeEntry('pet', 1))

    expect(memory.has('life')).toBe(true)
    expect(memory.has('pet')).toBe(true)
    expect(memory.load('life')?.snapshot?.activePhotoId).toBe('life-2')
    expect(memory.load('pet')?.snapshot?.activePhotoId).toBe('pet-1')
    expect(memory.load('photography')).toBeNull()
  })
})
