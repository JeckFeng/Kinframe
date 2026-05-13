/** Slide design layer types supported in v0.2. */
export type LayerType = 'shape' | 'image' | 'text' | 'timeline' | 'background' | 'mask'

/** Normalized 0–1 rectangle. */
export interface LayerRect {
  x: number
  y: number
  width: number
  height: number
}

/** Common fields shared by all layers. */
export interface LayerBase {
  id?: string
  type: LayerType
  role?: string
  zIndex: number
  rect: LayerRect
}

/** Shape layer — used for backgrounds, panels, decorative shapes. */
export interface ShapeLayer extends LayerBase {
  type: 'shape'
  style?: {
    fill?: string
    borderRadius?: string
    opacity?: number
  }
}

/** Image layer — the main photo. */
export interface ImageLayer extends LayerBase {
  type: 'image'
  source: 'preview' | 'thumbnail' | 'original'
  fit?: 'contain' | 'cover'
}

/** Text layer — caption, metadata, or labels. */
export interface TextLayer extends LayerBase {
  type: 'text'
  content: string
  style?: {
    color?: string
    fontSize?: string
    textAlign?: 'left' | 'center' | 'right'
    fontFamily?: string
    fontWeight?: number | string
    letterSpacing?: string
    lineHeight?: number | string
  }
}

/** Timeline layer — date label at the bottom of the slide. */
export interface TimelineLayer extends LayerBase {
  type: 'timeline'
  label?: string
  timeText?: string
  locationText?: string
  style?: {
    color?: string
    fontSize?: string
  }
}

/** Background layer — full-screen gradient or solid color. */
export interface BackgroundLayer extends LayerBase {
  type: 'background'
  style?: {
    gradient?: string
    color?: string
  }
}

/** Mask layer — semi-transparent overlay for mood/depth. */
export interface MaskLayer extends LayerBase {
  type: 'mask'
  style?: {
    color?: string
    opacity?: number
  }
}

export type Layer = ShapeLayer | ImageLayer | TextLayer | TimelineLayer | BackgroundLayer | MaskLayer

/** Template parameters provided by the design. */
export interface TemplateParams {
  imageRect?: LayerRect
  safeArea?: LayerRect
  orientation?: 'landscape' | 'portrait'
  imageFit?: 'contain' | 'cover'
  [key: string]: unknown
}

/** Render policy flags — must deny HTML/JS. */
export interface RenderPolicy {
  mode?: string
  allowHtml: boolean
  allowJavaScript: boolean
}

/** AI generation metadata — optional provenance info. */
export interface SlideAiMeta {
  provider?: string
  model?: string
  promptVersion?: string
}

/** Top-level slide design document. */
export interface SlideDesign {
  photoId: string
  templateId: string
  templateParams: TemplateParams
  layers: Layer[]
  styleTokens: Record<string, string>
  renderPolicy: RenderPolicy
  aiMeta?: SlideAiMeta
}

/** Template definition from slide_templates.json. */
export interface TemplateDefinition {
  id: string
  name: string
  description: string
  preferredCategories: string[]
  aspectRatios: string[]
  defaultParams: Record<string, unknown>
  paramSchema: Record<string, unknown>
  allowedLayerTypes: LayerType[]
  maxExtraLayers: number
  defaultStyleTokens: Record<string, string>
}
