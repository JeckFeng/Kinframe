<script setup lang="ts">
import type { ImageLayer } from '../types'

const props = defineProps<{
  layer: ImageLayer
  previewUrl: string
  thumbnailUrl?: string
}>()

const imageUrl = computed(() => {
  if (props.layer.source === 'thumbnail' && props.thumbnailUrl) {
    return props.thumbnailUrl
  }
  return props.previewUrl
})
</script>

<template>
  <div
    class="kf-layer kf-layer--image"
    :data-layer-id="layer.id || ''"
    :style="{
      position: 'absolute',
      left: `${(layer.rect.x * 100).toFixed(3)}%`,
      top: `${(layer.rect.y * 100).toFixed(3)}%`,
      width: `${(layer.rect.width * 100).toFixed(3)}%`,
      height: `${(layer.rect.height * 100).toFixed(3)}%`,
    }"
  >
    <img
      :src="imageUrl"
      alt=""
      class="kf-image"
      :style="{ objectFit: layer.fit || 'contain' }"
      loading="lazy"
      draggable="false"
    >
  </div>
</template>

<style scoped>
.kf-image {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
