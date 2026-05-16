<script setup lang="ts">
import type { VignetteLayer } from '../types'

const props = defineProps<{
  layer: VignetteLayer
}>()

function buildRadialGradient(fill: VignetteLayer['fill']): string {
  if (!fill || fill.type !== 'radialGradient') return 'radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,0.5) 100%)'
  const stops = fill.stops
  if (!stops || stops.length < 2) return 'radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,0.5) 100%)'
  const stopParts = stops.map(s => {
    const color = s.color || '#000000'
    const opacity = s.opacity !== undefined ? s.opacity : 1
    return `${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')} ${(s.position * 100).toFixed(1)}%`
  })
  return `radial-gradient(ellipse at center, ${stopParts.join(', ')})`
}

const vigStyle = computed(() => {
  const l = props.layer
  const opacity = l.opacity !== undefined ? l.opacity : 0.3
  return {
    position: 'absolute' as const,
    left: '0%',
    top: '0%',
    width: '100%',
    height: '100%',
    opacity: String(opacity),
    mixBlendMode: 'multiply' as const,
    pointerEvents: 'none' as const,
    background: buildRadialGradient(l.fill),
  }
})
</script>

<template>
  <div
    class="kf-layer kf-layer--vignette kf-vignette-layer"
    :data-layer-id="layer.id || ''"
    :style="vigStyle"
  />
</template>
