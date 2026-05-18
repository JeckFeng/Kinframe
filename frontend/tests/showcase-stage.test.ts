import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ShowcaseStage from '~/components/showcase/ShowcaseStage.vue'
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

describe('ShowcaseStage', () => {
  it('renders the archive rail stage shell with rail viewport and progress strip', () => {
    const wrapper = mount(ShowcaseStage, {
      props: {
        photos: [makeShowcasePhotoItem('photo-1')],
        activeCategory: 'life',
      },
    })

    expect(wrapper.find('[data-testid="showcase-stage"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="showcase-rail"]').exists()).toBe(true)
    expect(wrapper.find('nav[aria-label="Showcase progress"]').exists()).toBe(true)
  })

  it('reflects suspended and resumed rail states on the stage shell', async () => {
    const wrapper = mount(ShowcaseStage, {
      props: {
        photos: [makeShowcasePhotoItem('photo-1')],
        activeCategory: 'life',
      },
    })

    ;(wrapper.vm as unknown as { suspend: () => void; resume: () => void }).suspend()
    await nextTick()
    expect(wrapper.get('[data-testid="showcase-stage"]').attributes('data-rail-state')).toBe('suspended')

    ;(wrapper.vm as unknown as { suspend: () => void; resume: () => void }).resume()
    await nextTick()
    expect(wrapper.get('[data-testid="showcase-stage"]').attributes('data-rail-state')).toBe('idle')
  })

  it('switches the showcase cursor from idle to image hover mode inside the stage', async () => {
    const wrapper = mount(ShowcaseStage, {
      props: {
        photos: [makeShowcasePhotoItem('photo-1')],
        activeCategory: 'life',
      },
    })

    const stage = wrapper.get('[data-testid="showcase-stage"]')
    const cursor = wrapper.get('[data-testid="showcase-cursor"]')

    await stage.trigger('pointerenter', { clientX: 120, clientY: 160, pointerType: 'mouse' })
    await stage.trigger('pointermove', { clientX: 120, clientY: 160, pointerType: 'mouse' })

    expect(cursor.attributes('data-visible')).toBe('true')
    expect(cursor.attributes('data-hover-state')).toBe('idle')
    expect(cursor.attributes('style')).toContain('translate3d(120px, 160px, 0)')

    await wrapper.get('.showcase-slide-image').trigger('pointermove', {
      clientX: 144,
      clientY: 184,
      pointerType: 'mouse',
    })

    expect(cursor.attributes('data-hover-state')).toBe('image')
    expect(cursor.attributes('style')).toContain('translate3d(144px, 184px, 0)')

    await stage.trigger('pointerleave')

    expect(cursor.attributes('data-visible')).toBe('false')
    expect(cursor.attributes('data-hover-state')).toBe('idle')
  })
})
