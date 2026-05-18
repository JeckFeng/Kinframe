import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ShowcaseProgressStrip from '~/components/showcase/ShowcaseProgressStrip.vue'
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

describe('ShowcaseProgressStrip', () => {
  it('recenters the active thumbnail when the active index changes', async () => {
    const wrapper = mount(ShowcaseProgressStrip, {
      props: {
        photos: [
          makeShowcasePhotoItem('photo-1'),
          makeShowcasePhotoItem('photo-2'),
          makeShowcasePhotoItem('photo-3'),
          makeShowcasePhotoItem('photo-4'),
          makeShowcasePhotoItem('photo-5'),
        ],
        activeIndex: 0,
        reducedMotion: false,
      },
    })

    const thumbs = wrapper.get('.showcase-progress-thumbs').element as HTMLElement & {
      scrollTo: ReturnType<typeof vi.fn>
    }
    thumbs.scrollTo = vi.fn()
    Object.defineProperty(thumbs, 'clientWidth', { value: 120, configurable: true })
    Object.defineProperty(thumbs, 'scrollWidth', { value: 360, configurable: true })

    wrapper.findAll('.showcase-progress-thumb').forEach((thumb, index) => {
      Object.defineProperty(thumb.element, 'offsetLeft', {
        value: index * 72,
        configurable: true,
      })
      Object.defineProperty(thumb.element, 'offsetWidth', {
        value: 72,
        configurable: true,
      })
    })

    await wrapper.setProps({ activeIndex: 3 })

    expect(thumbs.scrollTo).toHaveBeenLastCalledWith({
      behavior: 'smooth',
      left: 192,
    })
  })
})
