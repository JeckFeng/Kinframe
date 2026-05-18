import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ShowcaseRail from '~/components/showcase/ShowcaseRail.vue'
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

describe('ShowcaseRail component', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders seven repeated background copies and seven repeated mask copies for seamless infinite scrolling', () => {
    const wrapper = mount(ShowcaseRail, {
      props: {
        photos: [makeShowcasePhotoItem('photo-1'), makeShowcasePhotoItem('photo-2')],
      },
    })

    expect(wrapper.findAll('.showcase-slide-copy-background')).toHaveLength(7)
    expect(wrapper.findAll('.showcase-slide-copy-mask')).toHaveLength(7)
    expect(wrapper.findAll('.showcase-mask-slot-shell')).toHaveLength(14)
    expect(wrapper.findAll('.showcase-slide-image')).toHaveLength(14)
  })

  it('updates the active foreground mask slot inside the current copy when jumpToIndex is called', async () => {
    const wrapper = mount(ShowcaseRail, {
      props: {
        photos: [
          makeShowcasePhotoItem('photo-1'),
          makeShowcasePhotoItem('photo-2'),
          makeShowcasePhotoItem('photo-3'),
        ],
      },
    })

    ;(wrapper.vm as unknown as { jumpToIndex: (index: number) => void }).jumpToIndex(1)
    await nextTick()

    const activeSlot = wrapper.get('.showcase-slide-copy-mask[data-copy="current"] .showcase-mask-slot-shell[data-active="true"]')
    expect(activeSlot.attributes('data-index')).toBe('1')
  })
})
