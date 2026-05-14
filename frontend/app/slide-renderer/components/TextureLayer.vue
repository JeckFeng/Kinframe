<script setup lang="ts">
import type { TextureLayer } from '../types'

const props = defineProps<{
  layer: TextureLayer
}>()

const texStyle = computed(() => {
  const l = props.layer
  const opacity = l.opacity !== undefined ? l.opacity : 0.15
  return {
    position: 'absolute' as const,
    left: '0%',
    top: '0%',
    width: '100%',
    height: '100%',
    opacity: String(opacity),
    mixBlendMode: l.blendMode || 'overlay',
    pointerEvents: 'none' as const,
    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
  }
})
</script>

<template>
  <div
    class="kf-layer kf-layer--texture"
    :data-layer-id="layer.id || ''"
    :style="texStyle"
  />
</template>
