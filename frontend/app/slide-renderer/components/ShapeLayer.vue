<script setup lang="ts">
import type { ShapeLayer } from '../types'

const props = defineProps<{
  layer: ShapeLayer
}>()

const shapeStyle = computed(() => {
  const l = props.layer
  return {
    position: 'absolute' as const,
    left: `${(l.rect.x * 100).toFixed(3)}%`,
    top: `${(l.rect.y * 100).toFixed(3)}%`,
    width: `${(l.rect.width * 100).toFixed(3)}%`,
    height: `${(l.rect.height * 100).toFixed(3)}%`,
    backgroundColor: l.style?.fill || 'transparent',
    borderRadius: l.style?.borderRadius || '0',
    opacity: l.style?.opacity !== undefined ? String(l.style.opacity) : '1',
  }
})
</script>

<template>
  <div
    class="kf-layer kf-layer--shape"
    :data-layer-id="layer.id || ''"
    :style="shapeStyle"
  />
</template>
