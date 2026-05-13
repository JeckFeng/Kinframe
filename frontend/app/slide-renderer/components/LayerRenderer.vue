<script setup lang="ts">
import type { Layer } from '../types'
import ImageLayerComponent from './ImageLayer.vue'
import TextLayerComponent from './TextLayer.vue'
import TimelineLayerComponent from './TimelineLayer.vue'
import ShapeLayerComponent from './ShapeLayer.vue'
import BackgroundLayerComponent from './BackgroundLayer.vue'
import MaskLayerComponent from './MaskLayer.vue'

const props = defineProps<{
  layer: Layer
  previewUrl: string
  thumbnailUrl?: string
  photoIndex?: number
  photoCount?: number
  timeText?: string
  locationText?: string
}>()
</script>

<template>
  <ImageLayerComponent
    v-if="layer.type === 'image'"
    :layer="layer"
    :preview-url="previewUrl"
    :thumbnail-url="thumbnailUrl || previewUrl"
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
    :time-text="timeText"
    :location-text="locationText"
  />
  <ShapeLayerComponent
    v-else-if="layer.type === 'shape'"
    :layer="layer"
  />
  <BackgroundLayerComponent
    v-else-if="layer.type === 'background'"
    :layer="layer"
  />
  <MaskLayerComponent
    v-else-if="layer.type === 'mask'"
    :layer="layer"
  />
</template>
