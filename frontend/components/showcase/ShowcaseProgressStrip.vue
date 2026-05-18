<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import type { ShowcaseProgressStripProps, ShowcaseProgressJumpPayload } from '~/types/showcase'

const props = defineProps<ShowcaseProgressStripProps>()

const emit = defineEmits<{
  jump: [payload: ShowcaseProgressJumpPayload]
}>()

const thumbsRef = ref<HTMLElement | null>(null)
const thumbEls = ref<HTMLElement[]>([])

function onJump(index: number) {
  emit('jump', { index, source: 'thumb' })
}

function registerThumbEl(index: number, el: Element | null) {
  if (!(el instanceof HTMLElement)) return
  thumbEls.value[index] = el
}

function centerActiveThumb() {
  const container = thumbsRef.value
  const activeThumb = thumbEls.value[props.activeIndex]
  if (!container || !activeThumb || typeof container.scrollTo !== 'function') return

  const targetLeft = activeThumb.offsetLeft - (container.clientWidth - activeThumb.offsetWidth) / 2
  const maxLeft = Math.max(container.scrollWidth - container.clientWidth, 0)
  const left = Math.min(Math.max(targetLeft, 0), maxLeft)

  container.scrollTo({
    left,
    behavior: props.reducedMotion ? 'auto' : 'smooth',
  })
}

async function centerActiveThumbSoon() {
  await nextTick()
  centerActiveThumb()
}

onMounted(() => {
  void centerActiveThumbSoon()
})

watch(
  () => [props.activeIndex, props.photos.length],
  () => {
    void centerActiveThumbSoon()
  },
)
</script>

<template>
  <nav
    class="showcase-progress-strip"
    aria-label="Showcase progress"
    data-testid="showcase-progress-strip"
  >
    <div
      ref="thumbsRef"
      class="showcase-progress-thumbs"
    >
      <button
        v-for="(item, index) in props.photos"
        :key="item.photo.id"
        :ref="el => registerThumbEl(index, el)"
        type="button"
        class="showcase-progress-thumb"
        :data-active="index === props.activeIndex ? 'true' : 'false'"
        @click="onJump(index)"
      >
        <img
          v-if="item.thumbnail_url || item.preview_url"
          class="showcase-progress-thumb-image"
          :src="item.thumbnail_url || item.preview_url || ''"
          alt=""
        >
      </button>
    </div>

    <div class="showcase-progress-meta">
      <span class="showcase-progress-count">
        {{ props.photos.length ? `${props.activeIndex + 1} / ${props.photos.length}` : '0 / 0' }}
      </span>
    </div>
  </nav>
</template>
