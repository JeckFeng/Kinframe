<script setup lang="ts">
import type { Layer } from '../types'
import ImageLayerComponent from './ImageLayer.vue'
import TextLayerComponent from './TextLayer.vue'
import TimelineLayerComponent from './TimelineLayer.vue'

const props = defineProps<{
  layer: Layer
  previewUrl: string
  photoIndex?: number
  photoCount?: number
}>()

const shapeStyle = computed(() => {
  const layer = props.layer
  if (layer.type !== 'shape') {
    return {}
  }
  return {
    position: 'absolute' as const,
    left: `${(layer.rect.x * 100).toFixed(3)}%`,
    top: `${(layer.rect.y * 100).toFixed(3)}%`,
    width: `${(layer.rect.width * 100).toFixed(3)}%`,
    height: `${(layer.rect.height * 100).toFixed(3)}%`,
    backgroundColor: (layer.style?.fill as string) || 'transparent',
    borderRadius: (layer.style?.borderRadius as string) || '0',
    opacity: layer.style?.opacity !== undefined ? String(layer.style.opacity) : '1',
  }
})
</script>

<template>
  <ImageLayerComponent
    v-if="layer.type === 'image'"
    :layer="layer"
    :preview-url="previewUrl"
  />
  <TextLayerComponent
    v-else-if="layer.type === 'text'"
    :layer="layer"
  />
  <TimelineLayerComponent
    v-else-if="layer.type === 'timeline'"
    :layer="layer"
    :photo-index="photoIndex"
    :photo-count="photoCount"
  />
  <div
    v-else-if="layer.type === 'shape'"
    class="kf-layer kf-layer--shape"
    :data-layer-id="layer.id || ''"
    :style="shapeStyle"
  />
</template>
