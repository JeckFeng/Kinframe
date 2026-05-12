<script setup lang="ts">
import type { TextLayer } from '../types'

const props = defineProps<{
  layer: TextLayer
}>()

const textStyle = computed(() => {
  const l = props.layer
  return {
    position: 'absolute' as const,
    left: `${(l.rect.x * 100).toFixed(3)}%`,
    top: `${(l.rect.y * 100).toFixed(3)}%`,
    width: `${(l.rect.width * 100).toFixed(3)}%`,
    height: `${(l.rect.height * 100).toFixed(3)}%`,
    color: l.style?.color || 'var(--kf-text-color, #f8fafc)',
    fontSize: l.style?.fontSize || 'clamp(16px, 2vw, 28px)',
    textAlign: l.style?.textAlign || 'left',
    fontFamily: l.style?.fontFamily || undefined,
    fontWeight: l.style?.fontWeight !== undefined ? String(l.style.fontWeight) : undefined,
    letterSpacing: l.style?.letterSpacing || undefined,
    lineHeight: l.style?.lineHeight !== undefined ? String(l.style.lineHeight) : undefined,
  }
})
</script>

<template>
  <div
    v-if="layer.content"
    class="kf-layer kf-layer--text"
    :data-layer-id="layer.id || ''"
    :style="textStyle"
  >
    <p class="kf-text-content">{{ layer.content }}</p>
  </div>
</template>

<style scoped>
.kf-text-content {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
</style>
