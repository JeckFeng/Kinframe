/** Scoped CSS sanitizer — whitelist-based selector and property enforcement. */

export const ALLOWED_SELECTORS = new Set([
  '.kf-slide',
  '.kf-slide[data-template]',
  '.kf-slide[data-category]',
  '.kf-layer',
  '.kf-layer[data-layer-id]',
  '.kf-photo-layer',
  '.kf-text-layer',
  '.kf-shape-layer',
  '.kf-mask-layer',
  '.kf-timeline-layer',
  '.kf-background-layer',
  '.kf-texture-layer',
  '.kf-vignette-layer',
  '.kf-caption',
  '.kf-meta',
  '.kf-photo-frame',
  '.kf-caption-panel',
])

export const ALLOWED_PROPERTIES = new Set([
  'color',
  'background',
  'background-color',
  'background-image',
  'background-size',
  'background-position',
  'background-repeat',
  'background-attachment',
  'background-blend-mode',
  'opacity',
  'box-shadow',
  'text-shadow',
  'filter',
  'backdrop-filter',
  'mix-blend-mode',
  'border',
  'border-color',
  'border-style',
  'border-width',
  'border-top',
  'border-right',
  'border-bottom',
  'border-left',
  'border-top-color',
  'border-top-style',
  'border-top-width',
  'border-right-color',
  'border-right-style',
  'border-right-width',
  'border-bottom-color',
  'border-bottom-style',
  'border-bottom-width',
  'border-left-color',
  'border-left-style',
  'border-left-width',
  'border-radius',
  'border-top-left-radius',
  'border-top-right-radius',
  'border-bottom-left-radius',
  'border-bottom-right-radius',
  'letter-spacing',
  'line-height',
  'font',
  'font-family',
  'font-size',
  'font-weight',
  'font-style',
  'font-variant',
  'text-align',
  'text-decoration',
  'text-transform',
  'text-indent',
  'text-overflow',
  'text-wrap',
  'text-wrap-mode',
  'text-wrap-style',
  'white-space',
  'word-spacing',
  'word-break',
  'transition',
  'transition-delay',
  'transition-duration',
  'transition-property',
  'transition-timing-function',
  'animation',
  'animation-name',
  'animation-duration',
  'animation-timing-function',
  'animation-delay',
  'animation-iteration-count',
  'animation-direction',
  'animation-fill-mode',
  'animation-play-state',
  'transform',
  'transform-origin',
  'clip-path',
  'mask',
  'mask-image',
  'mask-size',
  'mask-position',
  'mask-repeat',
  'mask-composite',
  'mask-mode',
  'mask-type',
  'mask-origin',
  'mask-clip',
])

const FORBIDDEN_SELECTOR_PARTS = new Set([
  'html', 'body', '#app', '*', 'script', 'iframe', 'input', 'button',
  'a[href]', 'head', 'meta', 'link',
])

const DANGEROUS_PATTERNS = [
  /@import/i,
  /javascript\s*:/i,
  /expression\s*\(/i,
  /@font-face/i,
  /behavior\s*:/i,
  /url\s*\(\s*['"]?\s*https?:\/\//i,
  /url\s*\(\s*['"]?\s*data:/i,
]

const PROPERTY_REGEX = /([a-zA-Z-]+)\s*:/
const DANGEROUS_PSEUDO_FUNCTIONS = /:(has|is|where|not)\s*\(/

export interface SanitizeResult {
  safeCss: string
  warnings: string[]
  blockedCount: number
  isValid: boolean
}

function hasDangerousPatterns(block: string): boolean {
  return DANGEROUS_PATTERNS.some(p => p.test(block))
}

function checkSelector(selector: string): string[] {
  const stripped = selector.trim()
  if (!stripped) return ['empty selector']

  const parts = stripped.split(',').map(p => p.trim())

  for (const part of parts) {
    // Check forbidden selector parts
    for (const forbidden of FORBIDDEN_SELECTOR_PARTS) {
      if (part.includes(forbidden)) {
        return [`Blocked selector: ${stripped} (contains forbidden '${forbidden}')`]
      }
    }

    // Check dangerous pseudo-functions
    if (DANGEROUS_PSEUDO_FUNCTIONS.test(part)) {
      return [`Blocked selector: ${stripped} (dangerous pseudo-function)`]
    }

    // Must contain a recognized KinFrame class
    const attrMatch = part.match(/\.([a-zA-Z-]+)/)
    if (!attrMatch) {
      return [`Blocked selector: ${stripped} (no recognized KinFrame class)`]
    }

    const baseClass = `.${attrMatch[1]}`
    if (!ALLOWED_SELECTORS.has(baseClass)) {
      return [`Blocked selector: ${stripped} (unknown class '${baseClass}')`]
    }
  }

  return [] // Safe
}

function sanitizeDeclarations(declarations: string): { safeDecls: string; warnings: string[] } {
  const safeParts: string[] = []
  const warnings: string[] = []

  for (const decl of declarations.split(';')) {
    const d = decl.trim()
    if (!d) continue

    const match = d.match(PROPERTY_REGEX)
    if (!match) continue

    const propName = match[1].toLowerCase().trim()
    if (ALLOWED_PROPERTIES.has(propName)) {
      safeParts.push(d)
    } else {
      warnings.push(`Blocked property: ${propName}`)
    }
  }

  return { safeDecls: safeParts.join('; '), warnings }
}

export function sanitizeScopedCss(rawCss: string): SanitizeResult {
  if (!rawCss || !rawCss.trim()) {
    return { safeCss: '', warnings: [], blockedCount: 0, isValid: true }
  }

  const warnings: string[] = []
  let blockedCount = 0

  // Check for dangerous patterns across the whole CSS
  if (hasDangerousPatterns(rawCss)) {
    return {
      safeCss: '',
      warnings: ['entire block rejected: contains dangerous pattern (@import, url(), javascript:, expression())'],
      blockedCount: 1,
      isValid: false,
    }
  }

  // Parse CSS rule blocks
  const ruleRegex = /([^{}]+?)\s*\{\s*([^{}]*?)\s*}/g
  const safeRules: string[] = []
  let match: RegExpExecArray | null

  while ((match = ruleRegex.exec(rawCss)) !== null) {
    const rawSelector = match[1].trim()
    const rawBody = match[2].trim()

    const selectorWarnings = checkSelector(rawSelector)
    if (selectorWarnings.length > 0) {
      blockedCount++
      warnings.push(...selectorWarnings)
      continue
    }

    const { safeDecls, warnings: declWarnings } = sanitizeDeclarations(rawBody)
    if (declWarnings.length > 0) {
      warnings.push(...declWarnings)
    }

    if (safeDecls) {
      safeRules.push(`${rawSelector} { ${safeDecls}; }`)
    } else {
      blockedCount++
      warnings.push(`Rule blocked (no valid properties): ${rawSelector}`)
    }
  }

  const safeCss = safeRules.join('\n')

  return {
    safeCss,
    warnings,
    blockedCount,
    isValid: true,
  }
}
