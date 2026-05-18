import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ShowcaseInfoOverlayItem from '~/components/showcase/ShowcaseInfoOverlayItem.vue'
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

describe('ShowcaseInfoOverlayItem', () => {
  it('renders a background-bound surround frame so time and location can sit outside the image bounds', () => {
    const wrapper = mount(ShowcaseInfoOverlayItem, {
      props: {
        item: makeShowcasePhotoItem('photo-1'),
        index: 1,
        copyLabel: 'current',
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
        timeLabel: '2026-05-17T10:00:00Z',
        locationLabel: 'Shanghai, China',
        visible: true,
      },
    })

    const shell = wrapper.get('.showcase-info-slot-shell')
    expect(shell.attributes('data-copy')).toBe('current')
    expect(shell.attributes('data-index')).toBe('1')
    expect(shell.attributes('data-visible')).toBe('true')
    expect(shell.attributes('style')).toContain('--info-slot-width: 230px;')
    expect(shell.attributes('style')).toContain('--info-frame-offset-y: 144px;')
    expect(wrapper.find('.showcase-info-surround').exists()).toBe(true)
    expect(wrapper.find('.showcase-info-frame').exists()).toBe(true)
    expect(wrapper.get('.showcase-info-time').text()).toBe('2026.05.17')
    expect(wrapper.get('.showcase-info-location').text()).toBe('Shanghai, China')
    expect(wrapper.find('.showcase-info-caption').exists()).toBe(false)
    expect(wrapper.find('.showcase-info-copy').exists()).toBe(false)
  })
})
