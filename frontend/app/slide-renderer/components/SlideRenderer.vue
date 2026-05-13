<script setup lang="ts">
import type { SlideDesign } from '../types'
import { validateSlideDesign, SlideDesignValidationError } from '../validators/validateSlideDesign'
import LayerRenderer from './LayerRenderer.vue'

const props = withDefaults(
  defineProps<{
    designJson: SlideDesign | null
    previewUrl: string
    thumbnailUrl?: string
    timeText?: string
    locationText?: string
    photoIndex?: number
    photoCount?: number
  }>(),
  {
    photoIndex: 0,
    photoCount: 0,
  },
)

const validatedDesign = computed<SlideDesign | null>(() => {
  if (!props.designJson) {
    return null
  }
  try {
    return validateSlideDesign(props.designJson)
  } catch (error) {
    if (error instanceof SlideDesignValidationError) {
      console.warn('Slide design validation failed:', error.message)
    }
    return null
  }
})

const cssVariables = computed<Record<string, string>>(() => {
  const tokens: Record<string, string> = {}
  if (validatedDesign.value) {
    Object.assign(tokens, validatedDesign.value.styleTokens)
  }
  return tokens
})

const templateId = computed(() => validatedDesign.value?.templateId || '')

const sortedLayers = computed(() => {
  if (!validatedDesign.value) {
    return []
  }
  return [...validatedDesign.value.layers].sort((a, b) => a.zIndex - b.zIndex)
})
</script>

<template>
  <section
    v-if="validatedDesign"
    class="kf-slide"
    :data-template="templateId"
    :style="cssVariables"
  >
    <LayerRenderer
      v-for="layer in sortedLayers"
      :key="layer.id || `${layer.type}-${layer.zIndex}`"
      :layer="layer"
      :preview-url="previewUrl"
      :thumbnail-url="thumbnailUrl"
      :photo-index="photoIndex"
      :photo-count="photoCount"
      :time-text="timeText"
      :location-text="locationText"
    />
  </section>
  <section v-else class="kf-slide kf-slide--fallback">
    <div class="kf-fallback-message">
      <p>Slide design unavailable</p>
      <img
        v-if="previewUrl"
        :src="previewUrl"
        alt=""
        class="kf-fallback-photo"
      >
    </div>
  </section>
</template>

<style scoped>
.kf-slide {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: var(--kf-background-color, #111111);
  color: var(--kf-text-color, #f8fafc);
}

.kf-slide--fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #111111;
}

.kf-fallback-message {
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
}

.kf-fallback-photo {
  max-width: 90%;
  max-height: 80vh;
  object-fit: contain;
  margin-top: 16px;
  border-radius: 8px;
}
</style>
