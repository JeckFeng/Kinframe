import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ShowcaseCard from '~/components/showcase/ShowcaseCard.vue'
import type { ShowcasePhotoItem } from '~/types/api'

function makeShowcasePhotoItem(id: string): ShowcasePhotoItem {
  return {
    photo: {
      id,
      owner_id: 'owner-1',
      category: 'life',
      category_source: 'manual',
      caption_source: 'manual',
      user_message: `Message ${id}`,
      final_caption: `Caption ${id}`,
      include_in_showcase: true,
      time_source: 'exif',
      bucket: 'photos',
      object_key_original: `original/${id}.jpg`,
      object_key_thumbnail: `thumbnail/${id}.jpg`,
      object_key_preview: `preview/${id}.jpg`,
      mime_type: 'image/jpeg',
      file_size: 1024,
      sha256: `sha-${id}`,
      width: 1200,
      height: 1600,
      taken_at: '2026-05-17T10:00:00Z',
      uploaded_at: '2026-05-17T10:00:00Z',
      gps_lat: null,
      gps_lng: null,
      camera_make: null,
      camera_model: null,
      location_name: 'Bund',
      location_country: 'China',
      location_region: 'Shanghai',
      location_city: 'Shanghai',
      location_district: null,
      location_road: null,
      geocoding_status: 'resolved',
      geocoding_provider: null,
      geocoded_at: null,
      status: 'ready',
      processing_message: null,
      created_at: '2026-05-17T10:00:00Z',
      updated_at: '2026-05-17T10:00:00Z',
    },
    preview_url: `https://example.com/${id}/preview.jpg`,
    thumbnail_url: `https://example.com/${id}/thumb.jpg`,
    slide_design: null,
  }
}

describe('ShowcaseCard', () => {
  it('renders a foreground mask slot with a transparent hole, time label, and caption band', () => {
    const wrapper = mount(ShowcaseCard, {
      props: {
        item: makeShowcasePhotoItem('photo-1'),
        index: 1,
        layout: {
          index: 1,
          startPx: 230,
          centerPx: 345,
          frameWidthPx: 230,
          frameHeightPx: 306,
          matteWidthPx: 328,
          matteHeightPx: 416,
          holeWidthPx: 230,
          holeHeightPx: 306,
        },
        timeLabel: '2026-05-17T10:00:00Z',
        locationLabel: 'Shanghai, China',
        captionLabel: '家庭聚会结束后路过的街道，晚风很轻。',
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
    expect(wrapper.findAll('.showcase-mask-matte')).toHaveLength(4)
    expect(wrapper.find('.showcase-mask-hole').exists()).toBe(true)
    expect(wrapper.find('.showcase-mask-caption-band').exists()).toBe(true)
    expect(wrapper.get('.showcase-mask-time').text()).toBe('2026.05.17')
    expect(wrapper.get('.showcase-mask-location').text()).toBe('Shanghai, China')
    expect(wrapper.get('.showcase-mask-copy').text()).toBe('家庭聚会结束后路过的街道，晚风很轻。')
  })

  it('falls back to photo metadata when explicit location and caption labels are empty', () => {
    const wrapper = mount(ShowcaseCard, {
      props: {
        item: makeShowcasePhotoItem('photo-fallback'),
        index: 0,
        layout: {
          index: 0,
          startPx: 0,
          centerPx: 115,
          frameWidthPx: 230,
          frameHeightPx: 306,
          matteWidthPx: 328,
          matteHeightPx: 416,
          holeWidthPx: 230,
          holeHeightPx: 306,
        },
        timeLabel: '2026-05-17T10:00:00Z',
        locationLabel: '',
        captionLabel: '',
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
    expect(wrapper.get('.showcase-mask-location').text()).toBe('Bund')
    expect(wrapper.get('.showcase-mask-copy').text()).toBe('Caption photo-fallback')
  })
})
