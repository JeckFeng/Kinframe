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

  it('accepts timeline layer with timeText and locationText', () => {
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
          timeText: '14:30',
          locationText: 'Beijing, China',
          style: { color: '#d8b26e', fontSize: '14px' },
        },
      ],
    })
    const result = validateSlideDesign(design)
    const timeline = result.layers.find(l => l.type === 'timeline')
    expect(timeline).toBeDefined()
    if (timeline && timeline.type === 'timeline') {
      expect(timeline.timeText).toBe('14:30')
      expect(timeline.locationText).toBe('Beijing, China')
    }
  })
})

// ── Background & mask layers (Phase 4) ───────────────────────────

describe('validateSlideDesign — background and mask layers', () => {
  it('accepts a background layer with gradient', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'background',
          zIndex: 0,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          style: { gradient: 'linear-gradient(135deg, #1a1a2e, #16213e)' },
        },
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
      ],
    })
    const result = validateSlideDesign(design)
    const bg = result.layers.find(l => l.type === 'background')
    expect(bg).toBeDefined()
    if (bg && bg.type === 'background') {
      expect(bg.style?.gradient).toBe('linear-gradient(135deg, #1a1a2e, #16213e)')
    }
  })

  it('accepts a background layer with solid color', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'background',
          zIndex: 0,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          style: { color: '#f7f5ef' },
        },
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
      ],
    })
    const result = validateSlideDesign(design)
    const bg = result.layers.find(l => l.type === 'background')
    expect(bg).toBeDefined()
    if (bg && bg.type === 'background') {
      expect(bg.style?.color).toBe('#f7f5ef')
    }
  })

  it('accepts a mask layer with opacity', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          type: 'mask',
          zIndex: 2,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          style: { color: '#000000', opacity: 0.4 },
        },
      ],
    })
    const result = validateSlideDesign(design)
    const mask = result.layers.find(l => l.type === 'mask')
    expect(mask).toBeDefined()
    if (mask && mask.type === 'mask') {
      expect(mask.style?.opacity).toBe(0.4)
    }
  })

  it('clamps mask opacity > 1 to 1', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          type: 'mask',
          zIndex: 2,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          style: { color: '#000000', opacity: 1.5 },
        },
      ],
    })
    const result = validateSlideDesign(design)
    const mask = result.layers.find(l => l.type === 'mask')
    expect(mask).toBeDefined()
    if (mask && mask.type === 'mask') {
      expect(mask.style?.opacity).toBe(1)
    }
  })

  it('clamps mask opacity < 0 to 0', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          type: 'mask',
          zIndex: 2,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          style: { color: '#000000', opacity: -0.3 },
        },
      ],
    })
    const result = validateSlideDesign(design)
    const mask = result.layers.find(l => l.type === 'mask')
    expect(mask).toBeDefined()
    if (mask && mask.type === 'mask') {
      expect(mask.style?.opacity).toBe(0)
    }
  })

  it('background layer appears first when zIndex is lowest', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'text',
          zIndex: 3,
          rect: { x: 0.05, y: 0.9, width: 0.9, height: 0.06 },
          content: 'On top',
        },
        {
          type: 'background',
          zIndex: 0,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          style: { gradient: 'linear-gradient(to bottom, #111, #222)' },
        },
        {
          type: 'image',
          zIndex: 2,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
      ],
    })
    const result = validateSlideDesign(design)
    expect(result.layers[0].type).toBe('background')
    expect(result.layers[1].type).toBe('image')
    expect(result.layers[2].type).toBe('text')
  })
})

// ── Text length and font-size limits (Phase 4) ───────────────────

describe('validateSlideDesign — text layer limits', () => {
  it('truncates text content longer than 200 characters', () => {
    const longText = 'A'.repeat(250)
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          type: 'text',
          zIndex: 2,
          rect: { x: 0.05, y: 0.9, width: 0.9, height: 0.06 },
          content: longText,
        },
      ],
    })
    const result = validateSlideDesign(design)
    const text = result.layers.find(l => l.type === 'text')
    expect(text).toBeDefined()
    if (text && text.type === 'text') {
      expect(text.content).toHaveLength(200)
      expect(text.content).toBe('A'.repeat(200))
    }
  })

  it('keeps text content at exactly 200 characters', () => {
    const exactText = 'B'.repeat(200)
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          type: 'text',
          zIndex: 2,
          rect: { x: 0.05, y: 0.9, width: 0.9, height: 0.06 },
          content: exactText,
        },
      ],
    })
    const result = validateSlideDesign(design)
    const text = result.layers.find(l => l.type === 'text')
    expect(text).toBeDefined()
    if (text && text.type === 'text') {
      expect(text.content).toHaveLength(200)
    }
  })

  it('caps fontSize at 120px for text layer', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          type: 'text',
          zIndex: 2,
          rect: { x: 0.05, y: 0.9, width: 0.9, height: 0.06 },
          content: 'Hello',
          style: { fontSize: '200px' },
        },
      ],
    })
    const result = validateSlideDesign(design)
    const text = result.layers.find(l => l.type === 'text')
    expect(text).toBeDefined()
    if (text && text.type === 'text') {
      expect(text.style?.fontSize).toBe('120px')
    }
  })

  it('caps fontSize at 120px for timeline layer', () => {
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
          zIndex: 2,
          rect: { x: 0.05, y: 0.02, width: 0.9, height: 0.04 },
          style: { fontSize: '300px' },
        },
      ],
    })
    const result = validateSlideDesign(design)
    const timeline = result.layers.find(l => l.type === 'timeline')
    expect(timeline).toBeDefined()
    if (timeline && timeline.type === 'timeline') {
      expect(timeline.style?.fontSize).toBe('120px')
    }
  })

  it('allows fontSize at or below 120px', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
        {
          type: 'text',
          zIndex: 2,
          rect: { x: 0.05, y: 0.9, width: 0.9, height: 0.06 },
          content: 'Normal',
          style: { fontSize: '48px' },
        },
      ],
    })
    const result = validateSlideDesign(design)
    const text = result.layers.find(l => l.type === 'text')
    expect(text).toBeDefined()
    if (text && text.type === 'text') {
      expect(text.style?.fontSize).toBe('48px')
    }
  })
})

// ── CSS property hardening (Phase 4) ─────────────────────────────

describe('validateSlideDesign — CSS property hardening', () => {
  it('blocks token containing position:fixed', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: {
        '--kf-bg': 'position:fixed;top:0;left:0;',
        '--kf-safe': '#ffffff',
      },
    }))
    expect(result.styleTokens).not.toHaveProperty('--kf-bg')
    expect(result.styleTokens['--kf-safe']).toBe('#ffffff')
  })

  it('blocks token containing display:none', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: {
        '--kf-danger': 'display:none !important',
        '--kf-safe': '#ffffff',
      },
    }))
    expect(result.styleTokens).not.toHaveProperty('--kf-danger')
    expect(result.styleTokens['--kf-safe']).toBe('#ffffff')
  })

  it('blocks token containing flex layout keyword', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: {
        '--kf-layout': 'display:flex',
        '--kf-safe': '#ffffff',
      },
    }))
    expect(result.styleTokens).not.toHaveProperty('--kf-layout')
    expect(result.styleTokens['--kf-safe']).toBe('#ffffff')
  })

  it('blocks token containing grid layout keyword', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: {
        '--kf-grid': 'display:grid',
        '--kf-safe': '#ffffff',
      },
    }))
    expect(result.styleTokens).not.toHaveProperty('--kf-grid')
    expect(result.styleTokens['--kf-safe']).toBe('#ffffff')
  })

  it('blocks token containing transform:', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: {
        '--kf-transform': 'transform:scale(2)',
        '--kf-safe': '#ffffff',
      },
    }))
    expect(result.styleTokens).not.toHaveProperty('--kf-transform')
    expect(result.styleTokens['--kf-safe']).toBe('#ffffff')
  })

  it('blocks token containing z-index:', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: {
        '--kf-z': 'z-index:9999',
        '--kf-safe': '#ffffff',
      },
    }))
    expect(result.styleTokens).not.toHaveProperty('--kf-z')
    expect(result.styleTokens['--kf-safe']).toBe('#ffffff')
  })

  it('blocks token containing overflow:', () => {
    const result = validateSlideDesign(makeDesign({
      styleTokens: {
        '--kf-overflow': 'overflow:visible',
        '--kf-safe': '#ffffff',
      },
    }))
    expect(result.styleTokens).not.toHaveProperty('--kf-overflow')
  })
})

// ── renderPolicy & structural validation (Phase 4) ───────────────

describe('validateSlideDesign — renderPolicy and bounds', () => {
  it('throws when renderPolicy.allowJavaScript is true', () => {
    const design = makeDesign({
      renderPolicy: { mode: 'fallback', allowHtml: false, allowJavaScript: true },
    })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })

  it('throws when zIndex is negative', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: -1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
      ],
    })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })

  it('throws when zIndex exceeds 100', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 101,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
      ],
    })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })

  it('throws when rect.x is outside [0,1]', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 1.5, y: 0, width: 1, height: 1 },
          source: 'preview',
        },
      ],
    })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })

  it('throws when rect.width is outside [0,1]', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: -0.1, height: 1 },
          source: 'preview',
        },
      ],
    })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })

  it('throws when layer has html field', () => {
    const design = makeDesign({
      layers: [
        {
          type: 'image',
          zIndex: 1,
          rect: { x: 0, y: 0, width: 1, height: 1 },
          source: 'preview',
          html: '<script>alert(1)</script>',
        },
      ],
    })
    expect(() => validateSlideDesign(design)).toThrow(SlideDesignValidationError)
  })
})

// ── aiMeta pass-through (Phase 4) ────────────────────────────────

describe('validateSlideDesign — aiMeta pass-through', () => {
  it('passes through aiMeta with provider, model, promptVersion', () => {
    const design = makeDesign({
      aiMeta: {
        provider: 'ollama',
        model: 'qwen3-vl:8b',
        promptVersion: 'v0.2-s1',
      },
    })
    const result = validateSlideDesign(design)
    expect(result.aiMeta).toBeDefined()
    expect(result.aiMeta?.provider).toBe('ollama')
    expect(result.aiMeta?.model).toBe('qwen3-vl:8b')
    expect(result.aiMeta?.promptVersion).toBe('v0.2-s1')
  })

  it('returns undefined aiMeta when not provided', () => {
    const design = makeDesign({})
    const result = validateSlideDesign(design)
    expect(result.aiMeta).toBeUndefined()
  })

  it('filters non-string aiMeta fields', () => {
    const design = makeDesign({
      aiMeta: {
        provider: 'ollama',
        model: 123,
        promptVersion: true,
        extraField: 'should be dropped',
      },
    })
    const result = validateSlideDesign(design)
    expect(result.aiMeta).toBeDefined()
    expect(result.aiMeta?.provider).toBe('ollama')
    expect(result.aiMeta?.model).toBeUndefined()
    expect(result.aiMeta?.promptVersion).toBeUndefined()
  })
})
