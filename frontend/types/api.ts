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
  user_message: string | null
  ai_caption: string | null
  final_caption: string | null
  ai_category_suggestion: string | null
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
