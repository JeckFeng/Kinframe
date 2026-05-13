export type UserRole = 'admin' | 'member'
export type PhotoCategory = 'life' | 'travel' | 'photography' | 'pet'
export type ShowcaseCategory = 'life' | 'photography' | 'pet'
export type PhotoStatus =
  | 'uploaded'
  | 'processing'
  | 'exif_parsed'
  | 'preview_generated'
  | 'vision_analyzed'
  | 'design_generated'
  | 'ready'
  | 'failed'
  | string

export interface PhotoCategoryDefinition {
  id: string
  slug: ShowcaseCategory
  name: string
  description: string | null
  legacy_slug: string | null
  sort_order: number
  is_active: boolean
}

export interface User {
  id: string
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

export interface Photo {
  id: string
  owner_id: string
  category: PhotoCategory
  category_source: string
  caption_source: string
  user_message: string | null
  ai_caption: string | null
  final_caption: string | null
  ai_category_suggestion: string | null
  ai_analysis_json: Record<string, unknown> | null
  ai_caption_enabled: boolean
  ai_category_enabled: boolean
  include_in_showcase: boolean
  time_source: string
  bucket: string
  object_key_original: string
  object_key_thumbnail: string
  object_key_preview: string | null
  mime_type: string
  file_size: number
  sha256: string
  width: number | null
  height: number | null
  taken_at: string
  uploaded_at: string
  gps_lat: number | null
  gps_lng: number | null
  camera_make: string | null
  camera_model: string | null
  exif_json: Record<string, unknown> | null
  location_name: string | null
  location_country: string | null
  location_region: string | null
  location_city: string | null
  location_district: string | null
  location_road: string | null
  geocoding_status: string
  geocoding_provider: string | null
  geocoding_error: string | null
  geocoded_at: string | null
  status: PhotoStatus
  processing_message: string | null
  created_at: string
  updated_at: string
}

export interface PresignedUrlResponse {
  url: string
}

export interface PhotoProcessingStatusResponse {
  photo_id: string
  photo_status: PhotoStatus
  job_type: string | null
  job_status: string | null
  attempts: number | null
  max_attempts: number | null
  error_message: string | null
  slide_design_status: string | null
  slide_design_source: string | null
}

export interface PhotoBatchUploadItem {
  filename: string
  success: boolean
  photo: Photo | null
  error: string | null
}

export interface PhotoBatchUploadResponse {
  success_count: number
  failure_count: number
  results: PhotoBatchUploadItem[]
}

export interface LoginResponse {
  user: User
}

export interface MeResponse {
  user: User
}

export interface ApiErrorBody {
  detail?: string
}

export interface ShowcasePhotoItem {
  photo: Photo
  preview_url: string | null
  slide_design: Record<string, unknown> | null
}

export interface ShowcaseResponse {
  categories: PhotoCategoryDefinition[]
  photos: ShowcasePhotoItem[]
}

export interface AdminJobItem {
  id: string
  photo_id: string
  job_type: string
  status: string
  attempts: number
  max_attempts: number
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  photo_category: string
  photo_status: string
  photo_file_size: number | null
  photo_width: number | null
  photo_height: number | null
  photo_taken_at: string | null
  photo_user_message: string | null
}

export interface AdminPhoto {
  id: string
  owner_id: string
  category: string
  category_source: string
  caption_source: string
  user_message: string | null
  ai_caption: string | null
  final_caption: string | null
  ai_category_suggestion: string | null
  ai_analysis_json: Record<string, unknown> | null
  ai_caption_enabled: boolean
  ai_category_enabled: boolean
  include_in_showcase: boolean
  time_source: string
  gps_lat: number | null
  gps_lng: number | null
  camera_make: string | null
  camera_model: string | null
  exif_json: Record<string, unknown> | null
  location_name: string | null
  location_country: string | null
  location_region: string | null
  location_city: string | null
  location_district: string | null
  location_road: string | null
  geocoding_status: string
  geocoding_provider: string | null
  geocoding_error: string | null
  geocoded_at: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface AdminCategory {
  id: string
  slug: string
  name: string
  description: string | null
  legacy_slug: string | null
  sort_order: number
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface AuditLogItem {
  id: string
  admin_id: string | null
  action: string
  target_type: string
  target_id: string | null
  detail: Record<string, unknown> | null
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogItem[]
  total: number
  limit: number
  offset: number
}
