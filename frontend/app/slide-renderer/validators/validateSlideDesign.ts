import templatesConfig from '../configs/slide_templates.json'
import whitelistConfig from '../configs/ai_css_whitelist.json'
import type {
  Layer,
  LayerBase,
  LayerRect,
  RenderPolicy,
  SlideDesign,
} from '../types'

const ALLOWED_TEMPLATE_IDS = new Set(
  templatesConfig.templates.map((template) => template.id),
)
const ALLOWED_LAYER_TYPES: Set<string> = new Set(['shape', 'image', 'text', 'timeline', 'background', 'mask'])
const ALLOWED_CSS_PREFIX = whitelistConfig.variablePrefix as string
const RECT_KEYS = new Set(['x', 'y', 'width', 'height'])

/** Layout-breaking CSS property tokens that must be blocked. */
const BLOCKED_CSS_TOKENS = [
  'position:',
  'display:',
  'flex',
  'grid',
  'transform:',
  'z-index:',
  'overflow:',
  'visibility:',
  'pointer-events:',
]

export class SlideDesignValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'SlideDesignValidationError'
  }
}

function isUnitInterval(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1
}

function validateRect(layerIndex: number, rect: unknown): LayerRect {
  if (rect === null || typeof rect !== 'object') {
    throw new SlideDesignValidationError(`layer ${layerIndex}: rect must be an object`)
  }
  const r = rect as Record<string, unknown>
  for (const key of RECT_KEYS) {
    if (!(key in r)) {
      throw new SlideDesignValidationError(`layer ${layerIndex}: rect missing "${key}"`)
    }
    if (!isUnitInterval(r[key])) {
      throw new SlideDesignValidationError(`layer ${layerIndex}: rect.${key} must be a number between 0 and 1`)
    }
  }
  return { x: r.x as number, y: r.y as number, width: r.width as number, height: r.height as number }
}

function validateLayer(layer: unknown, index: number): Layer | null {
  if (layer === null || typeof layer !== 'object') {
    throw new SlideDesignValidationError(`layer ${index}: must be an object`)
  }
  const l = layer as Record<string, unknown>

  // Reject executable content
  if ('html' in l || 'script' in l) {
    throw new SlideDesignValidationError(`layer ${index}: cannot include executable content`)
  }

  // Validate type — filter unknown types instead of rejecting the whole slide
  const type = l.type
  if (typeof type !== 'string' || !ALLOWED_LAYER_TYPES.has(type)) {
    console.warn(`layer ${index}: unknown type "${String(type)}" — layer filtered from render`)
    return null
  }

  // Validate zIndex
  const zIndex = l.zIndex
  if (typeof zIndex !== 'number' || !Number.isInteger(zIndex) || zIndex < 0 || zIndex > 100) {
    throw new SlideDesignValidationError(`layer ${index}: zIndex must be an integer between 0 and 100`)
  }

  // Validate rect
  const rect = validateRect(index, l.rect)

  const base: LayerBase = {
    id: typeof l.id === 'string' ? l.id : undefined,
    type: type as Layer['type'],
    role: typeof l.role === 'string' ? l.role : undefined,
    zIndex,
    rect,
  }

  if (type === 'text') {
    if (typeof l.content !== 'string') {
      throw new SlideDesignValidationError(`layer ${index}: text layer missing "content"`)
    }
    let content = l.content as string
    if (content.length > 200) {
      content = content.slice(0, 200)
    }
    const style = l.style && typeof l.style === 'object' ? (l.style as Record<string, unknown>) : undefined
    let fontSize = typeof style?.fontSize === 'string' ? style.fontSize : undefined
    if (fontSize) {
      const px = parseFloat(fontSize)
      if (!Number.isNaN(px) && px > 120) {
        fontSize = '120px'
      }
    }
    return {
      ...base,
      type: 'text',
      content,
      style: style && typeof style === 'object' ? {
        color: typeof style.color === 'string' ? style.color : undefined,
        fontSize,
        textAlign: style.textAlign as 'left' | 'center' | 'right' | undefined,
      } : undefined,
    }
  }

  if (type === 'image') {
    if (typeof l.source !== 'string') {
      throw new SlideDesignValidationError(`layer ${index}: image layer missing "source"`)
    }
    const fit = l.fit
    return {
      ...base,
      type: 'image',
      source: l.source as 'preview' | 'thumbnail' | 'original',
      fit: fit === 'contain' || fit === 'cover' ? fit : 'contain',
    }
  }

  if (type === 'timeline') {
    const style = l.style && typeof l.style === 'object' ? (l.style as Record<string, unknown>) : undefined
    let fontSize = typeof style?.fontSize === 'string' ? style.fontSize : undefined
    if (fontSize) {
      const px = parseFloat(fontSize)
      if (!Number.isNaN(px) && px > 120) {
        fontSize = '120px'
      }
    }
    return {
      ...base,
      type: 'timeline',
      label: typeof l.label === 'string' ? l.label : undefined,
      timeText: typeof l.timeText === 'string' ? l.timeText : undefined,
      locationText: typeof l.locationText === 'string' ? l.locationText : undefined,
      style: style && typeof style === 'object' ? {
        color: typeof style.color === 'string' ? style.color : undefined,
        fontSize,
      } : undefined,
    }
  }

  if (type === 'background') {
    const style = l.style && typeof l.style === 'object' ? (l.style as Record<string, unknown>) : undefined
    return {
      ...base,
      type: 'background',
      style: style && typeof style === 'object' ? {
        gradient: typeof style.gradient === 'string' ? style.gradient : undefined,
        color: typeof style.color === 'string' ? style.color : undefined,
      } : undefined,
    }
  }

  if (type === 'mask') {
    const style = l.style && typeof l.style === 'object' ? (l.style as Record<string, unknown>) : undefined
    let opacity = typeof style?.opacity === 'number' ? style.opacity : undefined
    if (opacity !== undefined) {
      opacity = Math.max(0, Math.min(1, opacity))
    }
    return {
      ...base,
      type: 'mask',
      style: style && typeof style === 'object' ? {
        color: typeof style.color === 'string' ? style.color : undefined,
        opacity,
      } : undefined,
    }
  }

  // shape
  const style = l.style && typeof l.style === 'object' ? (l.style as Record<string, unknown>) : undefined
  return {
    ...base,
    type: 'shape',
    style: style && typeof style === 'object' ? {
      fill: typeof style.fill === 'string' ? style.fill : undefined,
      borderRadius: typeof style.borderRadius === 'string' ? style.borderRadius : undefined,
      opacity: typeof style.opacity === 'number' ? style.opacity : undefined,
    } : undefined,
  }
}

function sanitizeStyleTokens(tokens: unknown): Record<string, string> {
  if (tokens === null || typeof tokens !== 'object') {
    return {}
  }
  const input = tokens as Record<string, unknown>
  const output: Record<string, string> = {}
  for (const [key, value] of Object.entries(input)) {
    if (!key.startsWith(ALLOWED_CSS_PREFIX)) {
      continue
    }
    // Reject tokens containing dangerous patterns
    if (typeof value !== 'string') {
      continue
    }
    const lower = value.toLowerCase()
    if (
      lower.includes('javascript:') ||
      lower.includes('expression(') ||
      lower.includes('@import') ||
      lower.includes('url(')
    ) {
      continue
    }
    if (BLOCKED_CSS_TOKENS.some(token => lower.includes(token))) {
      continue
    }
    output[key] = value
  }
  return output
}

/**
 * Validate and sanitize a slide design JSON document.
 * Returns a cleaned copy safe for rendering.
 */
export function validateSlideDesign(value: unknown): SlideDesign {
  if (value === null || typeof value !== 'object') {
    throw new SlideDesignValidationError('slide design must be an object')
  }
  const doc = value as Record<string, unknown>

  // Required keys
  const requiredKeys = ['photoId', 'templateId', 'templateParams', 'layers', 'styleTokens', 'renderPolicy']
  for (const key of requiredKeys) {
    if (!(key in doc)) {
      throw new SlideDesignValidationError(`slide design missing required key: "${key}"`)
    }
  }

  // Validate templateId
  const templateId = doc.templateId
  if (typeof templateId !== 'string' || !ALLOWED_TEMPLATE_IDS.has(templateId)) {
    throw new SlideDesignValidationError(`templateId "${String(templateId)}" is not supported`)
  }

  // Validate templateParams
  if (doc.templateParams === null || typeof doc.templateParams !== 'object') {
    throw new SlideDesignValidationError('templateParams must be an object')
  }

  // Validate renderPolicy — must deny HTML/JS
  const renderPolicy = doc.renderPolicy
  if (renderPolicy === null || typeof renderPolicy !== 'object') {
    throw new SlideDesignValidationError('renderPolicy must be an object')
  }
  const rp = renderPolicy as Record<string, unknown>
  if (rp.allowHtml !== false || rp.allowJavaScript !== false) {
    throw new SlideDesignValidationError('renderPolicy must deny HTML and JavaScript')
  }

  // Validate layers — filter unknown types, keep valid layers
  const layers = doc.layers
  if (!Array.isArray(layers)) {
    throw new SlideDesignValidationError('layers must be an array')
  }
  const validatedLayers: Layer[] = layers
    .map((layer, index) => validateLayer(layer, index))
    .filter((l): l is Layer => l !== null)

  // Sort layers by zIndex
  validatedLayers.sort((a, b) => a.zIndex - b.zIndex)

  // Sanitize style tokens
  const styleTokens = sanitizeStyleTokens(doc.styleTokens)

  const aiMeta = doc.aiMeta
  const validatedAiMeta = aiMeta && typeof aiMeta === 'object'
    ? {
        provider: typeof (aiMeta as Record<string, unknown>).provider === 'string' ? (aiMeta as Record<string, unknown>).provider as string : undefined,
        model: typeof (aiMeta as Record<string, unknown>).model === 'string' ? (aiMeta as Record<string, unknown>).model as string : undefined,
        promptVersion: typeof (aiMeta as Record<string, unknown>).promptVersion === 'string' ? (aiMeta as Record<string, unknown>).promptVersion as string : undefined,
      }
    : undefined

  return {
    photoId: doc.photoId as string,
    templateId: templateId as string,
    templateParams: doc.templateParams as SlideDesign['templateParams'],
    layers: validatedLayers,
    styleTokens,
    renderPolicy: {
      mode: typeof rp.mode === 'string' ? rp.mode : undefined,
      allowHtml: false,
      allowJavaScript: false,
    },
    aiMeta: validatedAiMeta,
  }
}
