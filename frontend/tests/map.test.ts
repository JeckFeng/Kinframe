import { describe, expect, it } from 'vitest'
import type { MapPhotoItem, MapPhotosResponse } from '~/types/api'

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function buildLocationText(photo: MapPhotoItem): string {
  return [photo.location_city, photo.location_region]
    .filter(Boolean)
    .join(', ') || photo.location_name || ''
}

describe('map page — escapeHtml', () => {
  it('escapes HTML special characters', () => {
    expect(escapeHtml('<script>alert("xss")</script>'))
      .toBe('&lt;script&gt;alert("xss")&lt;/script&gt;')
  })

  it('passes through plain text', () => {
    expect(escapeHtml('成都市, 四川省')).toBe('成都市, 四川省')
  })

  it('handles empty string', () => {
    expect(escapeHtml('')).toBe('')
  })
})

describe('map page — buildLocationText', () => {
  const basePhoto: MapPhotoItem = {
    photo_id: 'p1',
    preview_url: '',
    thumbnail_url: '',
    category: 'life',
    gps_lat: 30.5,
    gps_lng: 104.0,
    location_name: null,
    location_city: null,
    location_region: null,
    location_country: null,
    location_district: null,
    final_caption: null,
    taken_at: null,
  }

  it('returns city + region joined by comma', () => {
    expect(buildLocationText({ ...basePhoto, location_city: '成都市', location_region: '四川省' }))
      .toBe('成都市, 四川省')
  })

  it('falls back to location_name when city is null', () => {
    expect(buildLocationText({ ...basePhoto, location_name: '锦里古街' }))
      .toBe('锦里古街')
  })

  it('returns empty string when all location fields are null', () => {
    expect(buildLocationText(basePhoto)).toBe('')
  })
})

describe('map page — MapPhotosResponse type', () => {
  it('conforms to expected response shape', () => {
    const response: MapPhotosResponse = {
      photos: [
        {
          photo_id: 'abc-123',
          preview_url: 'https://storage.test/preview',
          thumbnail_url: 'https://storage.test/thumbnail',
          category: 'life',
          gps_lat: 30.5728,
          gps_lng: 104.0668,
          location_name: null,
          location_city: '成都市',
          location_region: '四川省',
          location_country: '中国',
          location_district: null,
          final_caption: '测试文案',
          taken_at: '2025-03-15T06:30:00Z',
        },
      ],
    }
    expect(response.photos).toHaveLength(1)
    expect(response.photos[0].photo_id).toBe('abc-123')
    expect(response.photos[0].gps_lat).toBe(30.5728)
    expect(response.photos[0].gps_lng).toBe(104.0668)
  })
})
