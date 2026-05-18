<script setup lang="ts">
import { computed } from 'vue'
import type { ShowcaseCardProps } from '~/types/showcase'

const props = defineProps<ShowcaseCardProps>()

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
    </div>
  </article>
</template>
