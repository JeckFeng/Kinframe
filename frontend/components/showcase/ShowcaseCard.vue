<script setup lang="ts">
import { computed } from 'vue'
import type { ShowcaseCardProps } from '~/types/showcase'

const props = defineProps<ShowcaseCardProps>()

function formatArchiveTimeLabel(value: string): string {
  if (!value) return ''

  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) {
    return value
      .replaceAll('/', '.')
      .replaceAll('-', '.')
      .slice(0, 10)
  }

  const year = date.getUTCFullYear()
  const month = String(date.getUTCMonth() + 1).padStart(2, '0')
  const day = String(date.getUTCDate()).padStart(2, '0')
  return `${year}.${month}.${day}`
}

const shellStyle = computed(() => ({
  '--slot-width': `${props.layout.frameWidthPx}px`,
  '--slot-height': `${props.layout.holeHeightPx}px`,
  '--matte-width': `${props.layout.matteWidthPx}px`,
  '--matte-height': `${props.layout.matteHeightPx}px`,
  '--hole-width': `${props.layout.holeWidthPx}px`,
  '--hole-height': `${props.layout.holeHeightPx}px`,
  '--caption-translate-x': `${props.visual.captionTranslateX}px`,
  '--time-translate-x': `${props.visual.timeTranslateX}px`,
  '--slot-progress': String(props.visual.normalizedProgress),
}))

const formattedTimeLabel = computed(() => formatArchiveTimeLabel(props.timeLabel))
const resolvedLocationLabel = computed(() => props.locationLabel || props.item.photo.location_name || '')
const resolvedCaptionLabel = computed(() => props.captionLabel || props.item.photo.final_caption || props.item.photo.user_message || '')
</script>

<template>
  <article
    class="showcase-mask-slot-shell"
    :data-index="index"
    :data-active="visual.isActive ? 'true' : 'false'"
    :data-visible="visual.isVisible ? 'true' : 'false'"
    :style="shellStyle"
  >
    <div class="showcase-mask-slot">
      <div class="showcase-mask-matte showcase-mask-matte-top" aria-hidden="true" />
      <div class="showcase-mask-matte showcase-mask-matte-right" aria-hidden="true" />
      <div class="showcase-mask-matte showcase-mask-matte-bottom" aria-hidden="true" />
      <div class="showcase-mask-matte showcase-mask-matte-left" aria-hidden="true" />
      <div class="showcase-mask-hole" aria-hidden="true" />

      <time class="showcase-mask-time">{{ formattedTimeLabel }}</time>

      <div class="showcase-mask-caption-band">
        <div class="showcase-mask-caption">
          <p class="showcase-mask-location">{{ resolvedLocationLabel }}</p>
          <p class="showcase-mask-copy">{{ resolvedCaptionLabel }}</p>
        </div>
      </div>
    </div>
  </article>
</template>
