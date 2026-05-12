import type { PhotoCategory, ShowcaseCategory } from '~/types/api'

const CATEGORY_LABELS: Record<PhotoCategory, string> = {
  life: '生活照',
  travel: '摄影照',
  photography: '摄影照',
  pet: '宠物照',
}

const SHOWCASE_CATEGORIES: ShowcaseCategory[] = ['life', 'photography', 'pet']

export function usePhotoCategories() {
  function displayCategory(category: PhotoCategory | string) {
    return CATEGORY_LABELS[category as PhotoCategory] || category
  }

  function isShowcaseCategory(category: string): category is ShowcaseCategory {
    return SHOWCASE_CATEGORIES.includes(category as ShowcaseCategory)
  }

  return {
    displayCategory,
    isShowcaseCategory,
    showcaseCategories: SHOWCASE_CATEGORIES,
  }
}
