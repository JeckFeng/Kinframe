<script setup lang="ts">
import type { BackgroundLayer } from '../types'

const props = defineProps<{
  layer: BackgroundLayer
}>()

const bgStyle = computed(() => {
  const l = props.layer
  const style: Record<string, string> = {
    position: 'absolute',
    left: '0%',
    top: '0%',
    width: '100%',
    height: '100%',
    zIndex: '0',
  }
  if (l.style?.gradient) {
    style.background = l.style.gradient
  } else if (l.style?.color) {
    style.backgroundColor = l.style.color
  }
  return style
})
</script>

<template>
  <div
    class="kf-layer kf-layer--background"
    :data-layer-id="layer.id || ''"
    :style="bgStyle"
  />
</template>
