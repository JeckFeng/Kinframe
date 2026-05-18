<script setup lang="ts">
import { computed } from 'vue'
import type { ShowcaseInfoOverlayItemProps } from '~/types/showcase'

const props = defineProps<ShowcaseInfoOverlayItemProps>()

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
  '--info-slot-width': `${props.layout.frameWidthPx}px`,
  '--info-slot-height': `${props.layout.holeHeightPx}px`,
  '--info-frame-width': `${props.layout.frameWidthPx}px`,
  '--info-frame-height': `${props.layout.frameHeightPx}px`,
  '--info-frame-offset-y': `${props.layout.backgroundImageOffsetYPx}px`,
}))

const formattedTimeLabel = computed(() => formatArchiveTimeLabel(props.timeLabel))
const resolvedLocationLabel = computed(() => props.locationLabel || props.item.photo.location_name || '')
</script>

<template>
  <article
    class="showcase-info-slot-shell"
    :data-copy="copyLabel"
    :data-index="index"
    :data-visible="visible ? 'true' : 'false'"
    :style="shellStyle"
  >
    <div class="showcase-info-frame">
      <time class="showcase-info-time">{{ formattedTimeLabel }}</time>
      <p class="showcase-info-location">{{ resolvedLocationLabel }}</p>
    </div>
  </article>
</template>
