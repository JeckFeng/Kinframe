<script setup lang="ts">
import { ref } from 'vue'
import type { ShowcaseStageExpose, ShowcaseStageProps } from '~/types/showcase'
import ShowcaseProgressStrip from './ShowcaseProgressStrip.vue'
import ShowcaseRail from './ShowcaseRail.vue'

const props = withDefaults(defineProps<ShowcaseStageProps>(), {
  initialSnapshot: null,
  reducedMotion: false,
  showProgress: true,
})

const emit = defineEmits<{
  'active-change': [payload: import('~/types/showcase').ShowcaseRailActiveChangePayload]
  settle: [snapshot: import('~/types/showcase').ShowcaseRailSnapshot]
  'interaction-state-change': [payload: import('~/types/showcase').ShowcaseRailInteractionStatePayload]
}>()

const railRef = ref<InstanceType<typeof ShowcaseRail> | null>(null)
const internalActiveIndex = ref(props.initialSnapshot?.activeIndex ?? 0)
const railState = ref<import('~/types/showcase').ShowcaseRailInteractionState>('idle')

function handleActiveChange(payload: import('~/types/showcase').ShowcaseRailActiveChangePayload) {
  internalActiveIndex.value = payload.activeIndex
  emit('active-change', payload)
}

function handleInteractionStateChange(payload: import('~/types/showcase').ShowcaseRailInteractionStatePayload) {
  railState.value = payload.state
  emit('interaction-state-change', payload)
}

function jumpToIndex(index: number, source: import('~/types/showcase').ShowcaseRailInteractionSource = 'programmatic') {
  railRef.value?.jumpToIndex(index, source)
}

function jumpBy(step: number, source: import('~/types/showcase').ShowcaseRailInteractionSource = 'programmatic') {
  railRef.value?.jumpBy(step, source)
}

function restoreSnapshot(snapshot: import('~/types/showcase').ShowcaseRailSnapshot | null | undefined) {
  railRef.value?.restoreSnapshot(snapshot)
  if (snapshot) internalActiveIndex.value = snapshot.activeIndex
}

function getSnapshot() {
  return railRef.value?.getSnapshot() ?? {
    currentX: 0,
    targetX: 0,
    activeIndex: internalActiveIndex.value,
    activePhotoId: props.photos[internalActiveIndex.value]?.photo.id ?? null,
    itemPitchPx: 0,
    loopSpanPx: 0,
    timestamp: Date.now(),
  }
}

function suspend() {
  railState.value = 'suspended'
  railRef.value?.suspend()
}

function resume() {
  railRef.value?.resume()
  railState.value = 'idle'
}

defineExpose<ShowcaseStageExpose>({
  jumpToIndex,
  jumpBy,
  restoreSnapshot,
  getSnapshot,
  suspend,
  resume,
})
</script>

<template>
  <section
    class="showcase-stage"
    data-testid="showcase-stage"
    :data-category="props.activeCategory"
    :data-rail-state="railState"
  >
    <div class="showcase-stage-viewport">
      <ShowcaseRail
        ref="railRef"
        :photos="props.photos"
        :initial-snapshot="props.initialSnapshot"
        :reduced-motion="props.reducedMotion"
        @active-change="handleActiveChange"
        @settle="emit('settle', $event)"
        @interaction-state-change="handleInteractionStateChange"
      />
    </div>

    <footer
      v-if="props.showProgress"
      class="showcase-stage-progress"
    >
      <ShowcaseProgressStrip
        :photos="props.photos"
        :active-index="internalActiveIndex"
        :reduced-motion="props.reducedMotion"
        @jump="jumpToIndex($event.index, $event.source)"
      />
    </footer>
  </section>
</template>
