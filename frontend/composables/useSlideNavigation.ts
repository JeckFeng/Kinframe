import { ref } from 'vue'

type TransitionDirection = 'next-photo' | 'prev-photo' | 'next-category' | 'prev-category' | 'initial'

const TRANSITION_MAP: Record<TransitionDirection, string> = {
  'next-photo': 'kf-photo-next',
  'prev-photo': 'kf-photo-prev',
  'next-category': 'kf-category-next',
  'prev-category': 'kf-category-prev',
  initial: 'kf-fade',
}

export function useSlideNavigation() {
  const prefersReducedMotion = ref(false)

  if (typeof window !== 'undefined') {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = mq.matches
    mq.addEventListener('change', (e) => {
      prefersReducedMotion.value = e.matches
    })
  }

  function getTransitionName(direction: TransitionDirection): string {
    return TRANSITION_MAP[direction]
  }

  function formatPosition(index: number, total: number): string {
    if (total <= 0) return ''
    return `第 ${index + 1}/${total} 张`
  }

  function emptyStateMessage(categoryName: string): string {
    return `${categoryName}分类还在等待第一张照片。`
  }

  return {
    prefersReducedMotion,
    getTransitionName,
    formatPosition,
    emptyStateMessage,
  }
}
