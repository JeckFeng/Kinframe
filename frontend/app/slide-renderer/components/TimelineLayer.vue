<script setup lang="ts">
import type { TimelineLayer } from '../types'

const props = defineProps<{
  layer: TimelineLayer
  photoIndex?: number
  photoCount?: number
}>()

const timelineStyle = computed(() => {
  const l = props.layer
  return {
    position: 'absolute' as const,
    left: `${(l.rect.x * 100).toFixed(3)}%`,
    top: `${(l.rect.y * 100).toFixed(3)}%`,
    width: `${(l.rect.width * 100).toFixed(3)}%`,
    height: `${(l.rect.height * 100).toFixed(3)}%`,
    color: l.style?.color || 'var(--kf-text-color, #f8fafc)',
    fontSize: l.style?.fontSize || '13px',
  }
})

const displayLabel = computed(() => props.layer.label || '')
</script>

<template>
  <div
    class="kf-layer kf-layer--timeline"
    :data-layer-id="layer.id || ''"
    :style="timelineStyle"
  >
    <div class="kf-timeline-track">
      <div class="kf-timeline-line" />
      <div
        v-if="photoCount && photoCount > 1"
        class="kf-timeline-dot"
        :style="{
          left: `${((photoIndex || 0) / Math.max(photoCount - 1, 1)) * 100}%`,
        }"
      />
    </div>
    <span v-if="displayLabel" class="kf-timeline-label">{{ displayLabel }}</span>
  </div>
</template>

<style scoped>
.kf-timeline-track {
  position: relative;
  height: 2px;
  width: 100%;
}

.kf-timeline-line {
  position: absolute;
  inset: 0;
  background-color: currentColor;
  opacity: 0.25;
  border-radius: 2px;
}

.kf-timeline-dot {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
  transition: left 720ms var(--kf-ease-cinematic, cubic-bezier(0.22, 1, 0.36, 1));
}

.kf-timeline-label {
  display: block;
  margin-top: 6px;
  font-size: 0.8em;
  opacity: 0.65;
}
</style>
