<script setup lang="ts">
import type { MaskLayer } from '../types'

const props = defineProps<{
  layer: MaskLayer
}>()

const maskStyle = computed(() => {
  const l = props.layer
  return {
    position: 'absolute' as const,
    left: '0%',
    top: '0%',
    width: '100%',
    height: '100%',
    backgroundColor: l.style?.color || '#000000',
    opacity: l.style?.opacity !== undefined ? String(l.style.opacity) : '0.3',
    pointerEvents: 'none' as const,
  }
})
</script>

<template>
  <div
    class="kf-layer kf-layer--mask"
    :data-layer-id="layer.id || ''"
    :style="maskStyle"
  />
</template>
