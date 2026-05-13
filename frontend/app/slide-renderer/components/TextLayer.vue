<script setup lang="ts">
import type { TextLayer } from '../types'

const props = defineProps<{
  layer: TextLayer
}>()

const cappedFontSize = computed(() => {
  const raw = props.layer.style?.fontSize
  if (!raw) return undefined
  const px = parseFloat(raw)
  if (!Number.isNaN(px) && px > 120) return '120px'
  return raw
})

const textStyle = computed(() => {
  const l = props.layer
  return {
    position: 'absolute' as const,
    left: `${(l.rect.x * 100).toFixed(3)}%`,
    top: `${(l.rect.y * 100).toFixed(3)}%`,
    width: `${(l.rect.width * 100).toFixed(3)}%`,
    height: `${(l.rect.height * 100).toFixed(3)}%`,
    color: l.style?.color || 'var(--kf-text-color, #f8fafc)',
    fontSize: cappedFontSize.value || 'clamp(16px, 2vw, 28px)',
    textAlign: l.style?.textAlign || 'left',
    fontFamily: l.style?.fontFamily || undefined,
    fontWeight: l.style?.fontWeight !== undefined ? String(l.style.fontWeight) : undefined,
    letterSpacing: l.style?.letterSpacing || undefined,
    lineHeight: l.style?.lineHeight !== undefined ? String(l.style.lineHeight) : undefined,
  }
})

const displayContent = computed(() => {
  const c = props.layer.content
  return c.length > 200 ? c.slice(0, 200) : c
})
</script>

<template>
  <div
    v-if="displayContent"
    class="kf-layer kf-layer--text"
    :data-layer-id="layer.id || ''"
    :style="textStyle"
  >
    <p class="kf-text-content">{{ displayContent }}</p>
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
  word-break: break-word;
}
</style>
