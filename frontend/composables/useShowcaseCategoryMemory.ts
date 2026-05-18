import type { ShowcaseCategory } from '~/types/api'
import type { ShowcaseCategoryMemoryEntry, UseShowcaseCategoryMemoryReturn } from '~/types/showcase'

export function useShowcaseCategoryMemory(): UseShowcaseCategoryMemoryReturn {
  const memory = new Map<ShowcaseCategory, ShowcaseCategoryMemoryEntry>()

  function save(category: ShowcaseCategory, entry: ShowcaseCategoryMemoryEntry) {
    memory.set(category, entry)
  }

  function load(category: ShowcaseCategory): ShowcaseCategoryMemoryEntry | null {
    return memory.get(category) ?? null
  }

  function has(category: ShowcaseCategory): boolean {
    return memory.has(category)
  }

  function clear(category?: ShowcaseCategory) {
    if (category) {
      memory.delete(category)
      return
    }
    memory.clear()
  }

  return {
    save,
    load,
    has,
    clear,
  }
}
