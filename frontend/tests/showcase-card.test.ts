import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ShowcaseCard from '~/components/showcase/ShowcaseCard.vue'

describe('ShowcaseCard', () => {
  it('renders a foreground mask slot with a transparent hole and matte geometry', () => {
    const wrapper = mount(ShowcaseCard, {
      props: {
        index: 1,
        layout: {
          index: 1,
          startPx: 230,
          centerPx: 345,
          frameWidthPx: 230,
          frameHeightPx: 306,
          backgroundImageOffsetYPx: 144,
          matteWidthPx: 328,
          matteHeightPx: 560,
          holeWidthPx: 230,
          holeHeightPx: 450,
        },
        visual: {
          index: 1,
          captionTranslateX: 8,
          timeTranslateX: 6,
          opacity: 1,
          normalizedProgress: 0,
          isVisible: true,
          isActive: true,
        },
      },
    })

    const shell = wrapper.get('.showcase-mask-slot-shell')
    expect(shell.attributes('data-active')).toBe('true')
    expect(shell.attributes('data-visible')).toBe('true')
    expect(shell.attributes('style')).toContain('--slot-width: 230px;')
    expect(shell.attributes('style')).toContain('--matte-width: 328px;')
    expect(shell.attributes('style')).toContain('--hole-width: 230px;')
    expect(shell.attributes('style')).toContain('--caption-translate-x: 8px;')
    expect(shell.attributes('style')).toContain('--time-translate-x: 6px;')
    expect(shell.attributes('style')).not.toContain('--slot-opacity')
    expect(wrapper.findAll('.showcase-mask-matte')).toHaveLength(4)
    expect(wrapper.find('.showcase-mask-hole').exists()).toBe(true)
    expect(wrapper.find('.showcase-info-caption-band').exists()).toBe(false)
    expect(wrapper.find('.showcase-info-time').exists()).toBe(false)
  })

  it('keeps inactive state metadata on the shell without rendering text content', () => {
    const wrapper = mount(ShowcaseCard, {
      props: {
        index: 0,
        layout: {
          index: 0,
          startPx: 0,
          centerPx: 115,
          frameWidthPx: 230,
          frameHeightPx: 306,
          backgroundImageOffsetYPx: 0,
          matteWidthPx: 328,
          matteHeightPx: 560,
          holeWidthPx: 230,
          holeHeightPx: 450,
        },
        visual: {
          index: 0,
          captionTranslateX: 0,
          timeTranslateX: 0,
          opacity: 0.8,
          normalizedProgress: -0.8,
          isVisible: true,
          isActive: false,
        },
      },
    })

    expect(wrapper.get('.showcase-mask-slot-shell').attributes('data-active')).toBe('false')
    expect(wrapper.find('.showcase-info-location').exists()).toBe(false)
    expect(wrapper.find('.showcase-info-copy').exists()).toBe(false)
  })
})
