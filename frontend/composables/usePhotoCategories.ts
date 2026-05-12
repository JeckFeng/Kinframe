import type { PhotoCategory, ShowcaseCategory } from '~/types/api'

const CATEGORY_LABELS: Record<PhotoCategory, string> = {
  life: '生活照',
  travel: '摄影照',
  photography: '摄影照',
  pet: '宠物照',
}

const SHOWCASE_DISPLAY_NAMES: Record<string, string> = {
  '生活照': '生活',
  '摄影照': '摄影',
  '宠物照': '萌宠',
}

const SHOWCASE_CATEGORIES: ShowcaseCategory[] = ['life', 'photography', 'pet']

export function usePhotoCategories() {
  function displayCategory(category: PhotoCategory | string) {
    return CATEGORY_LABELS[category as PhotoCategory] || category
  }

  function showcaseDisplayName(name: string) {
    return SHOWCASE_DISPLAY_NAMES[name] || name
  }

  function isShowcaseCategory(category: string): category is ShowcaseCategory {
    return SHOWCASE_CATEGORIES.includes(category as ShowcaseCategory)
  }

  return {
    displayCategory,
    showcaseDisplayName,
    isShowcaseCategory,
    showcaseCategories: SHOWCASE_CATEGORIES,
  }
}
