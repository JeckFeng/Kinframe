<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, toRef, watch } from 'vue'
import type { ShowcaseRailProps, ShowcaseStripItemLayout } from '~/types/showcase'
import { getShowcaseRenderCopyLabels, useShowcaseRail } from '~/composables/useShowcaseRail'
import ShowcaseCard from './ShowcaseCard.vue'

const props = withDefaults(defineProps<ShowcaseRailProps>(), {
  initialSnapshot: null,
  reducedMotion: false,
  config: undefined,
})

const emit = defineEmits<{
  'active-change': [payload: import('~/types/showcase').ShowcaseRailActiveChangePayload]
  settle: [snapshot: import('~/types/showcase').ShowcaseRailSnapshot]
  'interaction-state-change': [payload: import('~/types/showcase').ShowcaseRailInteractionStatePayload]
}>()

const initialSnapshotRef = toRef(props, 'initialSnapshot')
const reducedMotionRef = toRef(props, 'reducedMotion')
const photosRef = toRef(props, 'photos')

const rail = useShowcaseRail({
  photos: photosRef,
  reducedMotion: reducedMotionRef,
  initialSnapshot: initialSnapshotRef,
  config: props.config,
  onActiveChange: payload => emit('active-change', payload),
  onSettle: snapshot => emit('settle', snapshot),
  onInteractionStateChange: payload => emit('interaction-state-change', payload),
})

const cardStates = computed(() => rail.cardStates.value)
const layouts = computed(() => rail.layouts.value)
const layerCopies = getShowcaseRenderCopyLabels()
const backgroundLayerStyle = computed(() => ({
  transform: 'rotate(var(--showcase-slide-tilt))',
}))
const foregroundLayerStyle = computed(() => ({
  transform: 'rotate(var(--showcase-slide-tilt))',
}))
const backgroundTrackStyle = computed(() => ({
  transform: `translate3d(${rail.backgroundOffsetXPx.value + rail.backgroundTravelXPx.value}px, ${rail.backgroundOffsetYPx.value}px, 0)`,
}))
const foregroundTrackStyle = computed(() => ({
  transform: `translate3d(${rail.foregroundOffsetXPx.value + rail.foregroundTravelXPx.value}px, ${rail.foregroundOffsetYPx.value}px, 0)`,
}))

function getBackgroundSlotStyle(layout: ShowcaseStripItemLayout) {
  return {
    width: `${layout.frameWidthPx}px`,
    height: `${layout.holeHeightPx}px`,
  }
}

function getBackgroundImageStyle(layout: ShowcaseStripItemLayout) {
  return {
    height: `${layout.frameHeightPx}px`,
    transform: `translate3d(0, ${layout.backgroundImageOffsetYPx}px, 0)`,
  }
}

let resizeObserver: ResizeObserver | null = null

function recalcSoon() {
  void nextTick(() => {
    rail.recalc()
  })
}

onMounted(() => {
  recalcSoon()

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      rail.recalc()
    })

    if (rail.viewportRef.value) {
      resizeObserver.observe(rail.viewportRef.value)
    }
  } else {
    window.addEventListener('resize', rail.recalc)
  }
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  } else {
    window.removeEventListener('resize', rail.recalc)
  }

  rail.destroy()
})

watch(
  () => props.photos.map(item => item.photo.id).join(':'),
  () => recalcSoon(),
)

defineExpose({
  jumpToIndex: rail.jumpToIndex,
  jumpBy: rail.jumpBy,
  restoreSnapshot: rail.restoreSnapshot,
  getSnapshot: rail.getSnapshot,
  suspend: rail.suspend,
  resume: rail.resume,
  recalc: rail.recalc,
})
</script>

<template>
  <div
    ref="rail.viewportRef"
    class="showcase-viewport"
    data-testid="showcase-rail"
    :data-rail-state="rail.interactionState.value"
    :data-reduced-motion="props.reducedMotion ? 'true' : 'false'"
    @wheel.prevent="rail.onWheel"
    @touchstart.passive="rail.onTouchStart"
    @touchmove.prevent="rail.onTouchMove"
    @touchend="rail.onTouchEnd"
  >
    <div ref="rail.railRef" class="showcase-parallax-scene">
      <div class="showcase-slide-layer showcase-slide-layer-background" :style="backgroundLayerStyle">
        <div class="showcase-slide showcase-slide-background" :style="backgroundTrackStyle">
          <div
            v-for="copy in layerCopies"
            :key="`bg:${copy}`"
            class="showcase-slide-copy showcase-slide-copy-background"
            :data-copy="copy"
          >
            <div
              v-for="(item, index) in props.photos"
              :key="`bg:${copy}:${item.photo.id}`"
              class="showcase-slide-slot showcase-slide-slot-background"
              :style="layouts[index] ? getBackgroundSlotStyle(layouts[index]) : undefined"
            >
              <img
                v-if="item.preview_url && layouts[index]"
                class="showcase-slide-image"
                :src="item.preview_url"
                alt=""
                draggable="false"
                :style="getBackgroundImageStyle(layouts[index])"
              >
            </div>
          </div>
        </div>
      </div>

      <div class="showcase-slide-layer showcase-slide-layer-mask" :style="foregroundLayerStyle">
        <div class="showcase-slide showcase-slide-mask" :style="foregroundTrackStyle">
          <div
            v-for="copy in layerCopies"
            :key="`fg:${copy}`"
            class="showcase-slide-copy showcase-slide-copy-mask"
            :data-copy="copy"
          >
            <template v-for="(item, index) in props.photos" :key="`fg:${copy}:${item.photo.id}`">
              <ShowcaseCard
                v-if="layouts[index] && cardStates[index]"
                :item="item"
                :index="index"
                :layout="layouts[index]"
                :visual="cardStates[index]"
                :time-label="item.photo.taken_at"
                :location-label="item.photo.location_city || item.photo.location_name || ''"
                :caption-label="item.photo.final_caption || item.photo.user_message || ''"
              />
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
