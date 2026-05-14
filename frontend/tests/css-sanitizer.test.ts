import { describe, expect, it } from 'vitest'
import {
  sanitizeScopedCss,
  ALLOWED_SELECTORS,
  ALLOWED_PROPERTIES,
} from '~/app/slide-renderer/utils/cssSanitizer'

describe('cssSanitizer — Selector whitelist', () => {
  it('contains all KinFrame-specific selectors', () => {
    const required = [
      '.kf-slide', '.kf-layer', '.kf-photo-layer', '.kf-text-layer',
      '.kf-shape-layer', '.kf-mask-layer', '.kf-timeline-layer',
      '.kf-caption', '.kf-meta', '.kf-photo-frame', '.kf-caption-panel',
    ]
    for (const sel of required) {
      expect(ALLOWED_SELECTORS.has(sel)).toBe(true)
    }
  })

  it('does not contain forbidden selectors', () => {
    const forbidden = ['html', 'body', '#app', '*', 'script', 'iframe', 'input', 'button']
    for (const sel of forbidden) {
      expect(ALLOWED_SELECTORS.has(sel)).toBe(false)
    }
  })
})

describe('cssSanitizer — Property whitelist', () => {
  it('contains all visual-only properties', () => {
    const required = ['color', 'background-color', 'opacity', 'box-shadow',
      'border-radius', 'font-size', 'text-align', 'filter', 'transform']
    for (const prop of required) {
      expect(ALLOWED_PROPERTIES.has(prop)).toBe(true)
    }
  })

  it('does not contain layout-breaking properties', () => {
    const forbidden = ['position', 'top', 'left', 'width', 'height',
      'z-index', 'display', 'flex', 'overflow', 'visibility']
    for (const prop of forbidden) {
      expect(ALLOWED_PROPERTIES.has(prop)).toBe(false)
    }
  })
})

describe('cssSanitizer — sanitizeScopedCss', () => {
  it('passes valid simple CSS through', () => {
    const result = sanitizeScopedCss('.kf-caption { color: #ffffff; }')
    expect(result.isValid).toBe(true)
    expect(result.safeCss).toContain('.kf-caption')
    expect(result.safeCss).toContain('color')
  })

  it('strips forbidden selector rules', () => {
    const result = sanitizeScopedCss('.kf-caption { color: #fff; } body { background: red; }')
    expect(result.isValid).toBe(true)
    expect(result.safeCss).toContain('.kf-caption')
    expect(result.safeCss).not.toContain('body')
  })

  it('strips forbidden property declarations', () => {
    const result = sanitizeScopedCss('.kf-caption { color: #fff; position: fixed; }')
    expect(result.isValid).toBe(true)
    expect(result.safeCss).toContain('color')
    expect(result.safeCss).not.toContain('position')
  })

  it('rejects entire block on @import', () => {
    const result = sanitizeScopedCss('.kf-caption { color: #fff; } @import url("evil.css");')
    expect(result.isValid).toBe(false)
  })

  it('rejects entire block on javascript:', () => {
    const result = sanitizeScopedCss('.kf-caption { background: javascript:alert(1); }')
    expect(result.isValid).toBe(false)
  })

  it('rejects entire block on expression()', () => {
    const result = sanitizeScopedCss('.kf-caption { width: expression(alert(1)); }')
    expect(result.isValid).toBe(false)
  })

  it('rejects entire block on external url()', () => {
    const result = sanitizeScopedCss('.kf-caption { background: url("http://evil.com/x.png"); }')
    expect(result.isValid).toBe(false)
  })

  it('handles empty CSS', () => {
    const result = sanitizeScopedCss('')
    expect(result.isValid).toBe(true)
    expect(result.safeCss).toBe('')
  })

  it('handles only forbidden rules gracefully', () => {
    const result = sanitizeScopedCss('body { background: red; } html { opacity: 0; }')
    expect(result.isValid).toBe(true)
    expect(result.safeCss).toBe('')
  })

  it('strips comma selectors containing forbidden parts', () => {
    const result = sanitizeScopedCss('.kf-caption, body { color: #fff; }')
    expect(result.isValid).toBe(true)
    expect(result.safeCss).not.toContain('body')
  })

  it('preserves data-attribute selectors on allowed bases', () => {
    const result = sanitizeScopedCss('.kf-slide[data-template="dark"] { color: #fff; }')
    expect(result.isValid).toBe(true)
    expect(result.safeCss).toContain('kf-slide')
  })

  it('provides warnings for blocked rules', () => {
    const result = sanitizeScopedCss('body { background: red; } .kf-caption { color: #fff; }')
    expect(result.warnings.length).toBeGreaterThan(0)
  })
})
