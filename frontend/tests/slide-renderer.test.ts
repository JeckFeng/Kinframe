import { describe, expect, it } from 'vitest'
import { validateSlideDesign, SlideDesignValidationError } from '~/app/slide-renderer/validators/validateSlideDesign'
import type { SlideDesign } from '~/app/slide-renderer/types'

function makeDesign(overrides: Partial<SlideDesign> = {}): SlideDesign {
  return {
    photoId: 'photo-001',
    templateId: 'cinematic_fullscreen',
    templateParams: { imageFit: 'contain', orientation: 'landscape' },
    layers: [
      {
        id: 'img-1',
        type: 'image',
        role: 'photo',
        zIndex: 1,
        rect: { x: 0, y: 0, width: 1, height: 1 },
        source: 'preview',
        fit: 'contain',
      },
      {
        id: 'txt-1',
        type: 'text',
        role: 'caption',
        zIndex: 2,
        rect: { x: 0.05, y: 0.88, width: 0.9, height: 0.08 },
        content: 'A quiet morning',
        style: { color: '#f8fafc', fontSize: '16px', textAlign: 'center' },
      },
    ],
    styleTokens: {
      '--kf-background-color': '#111111',
      '--kf-text-color': '#f8fafc',
    },
    renderPolicy: { mode: 'fallback', allowHtml: false, allowJavaScript: false },
    ...overrides,
  }
}

// ── 3 template designs ──────────────────────────────────────────

describe('validateSlideDesign — valid designs', () => {
  it('accepts cinematic_fullscreen template', () => {
    const design = makeDesign({ templateId: 'cinematic_fullscreen' })
    const result = validateSlideDesign(design)
    expect(result.templateId).toBe('cinematic_fullscreen')
    expect(result.layers).toHaveLength(2)
  })

  it('accepts warm_memory template', () => {
    const design = makeDesign({
      templateId: 'warm_memory',
      styleTokens: { '--kf-background-color': '#f7f5ef', '--kf-text-color': '#171717' },
    })
    const result = validateSlideDesign(design)
    expect(result.templateId).toBe('warm_memory')
  })

  it('accepts minimal_white template', () => {
    const design = makeDesign({
      templateId: 'minimal_white',
      styleTokens: { '--kf-background-color': '#f7f5ef', '--kf-text-color': '#171717' },
    })
    const result = validateSlideDesign(design)
    expect(result.templateId).toBe('minimal_white')
  })
})

// ── Unknown layer filtering ─────────────────────────────────────

describe('validateSlideDesign — unknown layer filtering', () => {
  it('filters a single unknown layer type, keeps valid layers', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          type: 'unknown_ai_layer',
          zIndex: 2,
          rect: { x: 0.1, y: 0.1, width: 0.8, height: 0.8 },
          content: 'should be filtered',
        },
        {
          type: 'text',
          zIndex: 3,
          rect: { x: 0.05, y: 0.9, width: 0.9, height: 0.06 },
          content: 'This survives',
        },
      ],
    })
    const result = validateSlideDesign(design)
    expect(result.layers).toHaveLength(2)
    expect(result.layers[0].type).toBe('image')
    expect(result.layers[1].type).toBe('text')
  })

  it('does not break the page when ALL layers are unknown', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'unknown_type_a',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
        },
        {
          type: 'unknown_type_b',
          zIndex: 2,
          rect: { x: 0.1, y: 0.1, width: 0.8, height: 0.8 },
        },
      ],
    })
    // Should not throw — returns valid design with empty layers
    const result = validateSlideDesign(design)
    expect(result.templateId).toBe('cinematic_fullscreen')
    expect(result.layers).toHaveLength(0)
  })

  it('filters a layer with missing type field entirely', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          zIndex: 2, // no type field
          rect: { x: 0.1, y: 0.1, width: 0.8, height: 0.8 },
        },
      ],
    })
    const result = validateSlideDesign(design)
    expect(result.layers).toHaveLength(1)
    expect(result.layers[0].type).toBe('image')
  })
})

// ── Structural errors still throw ───────────────────────────────

describe('validateSlideDesign — structural errors', () => {
  it('throws for missing templateId', () => {
    const design = makeDesign({ templateId: undefined as unknown as string })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })

  it('throws for unknown templateId', () => {
    const design = makeDesign({ templateId: 'nonexistent_template' })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })

  it('throws when layers is not an array', () => {
    const design = makeDesign({ layers: 'not-an-array' as unknown as SlideDesign['layers'] })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })

  it('throws when renderPolicy allows HTML', () => {
    const design = makeDesign({
      renderPolicy: { mode: 'fallback', allowHtml: true, allowJavaScript: false },
    })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })
})

// ── Style token sanitization ────────────────────────────────────

describe('validateSlideDesign — style token sanitization', () => {
  it('keeps whitelisted kf- tokens', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: { '--kf-background-color': '#0a0a0a', '--kf-text-color': '#ffffff' },
    }))
    expect(result.styleTokens['--kf-background-color']).toBe('#0a0a0a')
    expect(result.styleTokens['--kf-text-color']).toBe('#ffffff')
  })

  it('filters non-whitelisted CSS tokens', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: { '--kf-background-color': '#111', '--evil-token': 'url(javascript:alert(1))' },
    }))
    expect(result.styleTokens['--kf-background-color']).toBe('#111')
    expect(result.styleTokens).not.toHaveProperty('--evil-token')
  })

  it('filters tokens with dangerous values', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: {
        '--kf-background-color': 'javascript:alert(1)',
        '--kf-text-color': '#ffffff',
      },
    }))
    expect(result.styleTokens).not.toHaveProperty('--kf-background-color')
    expect(result.styleTokens['--kf-text-color']).toBe('#ffffff')
  })
})

// ── Timeline layer ──────────────────────────────────────────────

describe('validateSlideDesign — timeline layer', () => {
  it('accepts a valid timeline layer', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          type: 'timeline',
          zIndex: 5,
          rect: { x: 0.05, y: 0.02, width: 0.9, height: 0.04 },
          label: '2024-03-15',
          style: { color: '#d8b26e' },
        },
      ],
    })
    const result = validateSlideDesign(design)
    const timeline = result.layers.find(l => l.type === 'timeline')
    expect(timeline).toBeDefined()
    if (timeline && timeline.type === 'timeline') {
      expect(timeline.label).toBe('2024-03-15')
    }
  })
})
