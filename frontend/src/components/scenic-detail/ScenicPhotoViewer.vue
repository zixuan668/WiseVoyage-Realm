<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowLeft, ArrowRight, Close } from '@/icons'
import type { ScenicGalleryPhoto } from '@/data/scenicDetail'

const props = defineProps<{
  photos: ScenicGalleryPhoto[]
  index: number
}>()

const emit = defineEmits<{
  'update:index': [index: number]
  close: []
}>()

const total = computed(() => props.photos.length)
const currentIndex = computed(() => {
  if (!total.value) return 0
  return Math.min(Math.max(props.index, 0), total.value - 1)
})
const current = computed(() => props.photos[currentIndex.value])
const slideKey = computed(() => current.value?.id ?? String(currentIndex.value))
const closeEl = ref<HTMLButtonElement | null>(null)

/* ---------- 切换 ---------- */
function goTo(next: number) {
  if (total.value < 2) return
  emit('update:index', ((next % total.value) + total.value) % total.value)
}
function prev() {
  goTo(currentIndex.value - 1)
}
function next() {
  goTo(currentIndex.value + 1)
}

/* ---------- 左右滑动 ---------- */
let tracking = false
let startX = 0
let startY = 0
const dragX = ref(0)
const swiping = ref(false)

function onSwipeStart(event: PointerEvent) {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  if (total.value < 2) return
  tracking = true
  startX = event.clientX
  startY = event.clientY
  dragX.value = 0
  swiping.value = false
  ;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId)
}
function onSwipeMove(event: PointerEvent) {
  if (!tracking) return
  const dx = event.clientX - startX
  const dy = event.clientY - startY
  if (!swiping.value) {
    if (Math.abs(dx) < 10 || Math.abs(dx) <= Math.abs(dy)) return
    swiping.value = true
  }
  dragX.value = Math.max(-140, Math.min(140, dx))
}
function onSwipeEnd() {
  if (!tracking) return
  tracking = false
  const distance = dragX.value
  dragX.value = 0
  swiping.value = false
  if (Math.abs(distance) < 48) return
  if (distance < 0) next()
  else prev()
}

const frameStyle = computed(() => ({
  transform: dragX.value ? `translateX(${dragX.value}px)` : undefined,
  opacity: dragX.value ? String(1 - Math.min(Math.abs(dragX.value) / 420, 0.35)) : undefined
}))

/* ---------- 键盘 ---------- */
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    prev()
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    next()
  } else if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  void nextTick(() => closeEl.value?.focus())
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="photo-viewer" role="dialog" aria-modal="true" aria-label="景点照片查看器">
    <header class="viewer-bar">
      <span class="viewer-count" aria-live="polite">{{ total ? currentIndex + 1 : 0 }} / {{ total }}</span>
      <button ref="closeEl" class="viewer-close" type="button" aria-label="关闭大图" @click="emit('close')">
        <Close :size="22" />
      </button>
    </header>

    <div
      class="viewer-stage"
      :class="{ 'is-swiping': swiping }"
      @pointerdown="onSwipeStart"
      @pointermove="onSwipeMove"
      @pointerup="onSwipeEnd"
      @pointercancel="onSwipeEnd"
    >
      <button
        v-if="total > 1"
        class="viewer-nav viewer-nav--prev"
        type="button"
        aria-label="上一张照片"
        @pointerdown.stop
        @click.stop="prev"
      >
        <ArrowLeft :size="24" />
      </button>

      <div class="viewer-frame" :class="{ 'is-dragging': swiping }" :style="frameStyle">
        <img
          v-if="current"
          :key="slideKey"
          class="viewer-image"
          :src="current.src"
          :alt="current.caption"
          draggable="false"
          decoding="async"
        />
        <p v-else class="viewer-empty">暂无可以查看的照片</p>
      </div>

      <button
        v-if="total > 1"
        class="viewer-nav viewer-nav--next"
        type="button"
        aria-label="下一张照片"
        @pointerdown.stop
        @click.stop="next"
      >
        <ArrowRight :size="24" />
      </button>
    </div>

    <footer v-if="current" class="viewer-caption">
      <p class="viewer-caption__text">{{ current.caption }}</p>
      <p class="viewer-caption__note">{{ current.note }}</p>
    </footer>
  </div>
</template>

<style scoped lang="scss">
.photo-viewer {
  position: absolute;
  inset: 0;
  z-index: 50;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgba(11, 9, 18, 0.94);
  color: #fff;
  user-select: none;
  animation: viewer-in 0.24s ease both;
}

.viewer-bar {
  display: flex;
  flex: none;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: calc(env(safe-area-inset-top, 0px) + 12px) 16px 6px;
}

.viewer-count {
  padding-left: 4px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 18px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.06em;
}

.viewer-close {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.viewer-close:hover {
  background: rgba(255, 255, 255, 0.2);
}

.viewer-close:active {
  transform: scale(0.94);
}

.viewer-close:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.7);
  outline-offset: 2px;
}

.viewer-stage {
  position: relative;
  display: grid;
  flex: 1;
  place-items: center;
  min-height: 0;
  padding: 6px 4px;
  touch-action: none;
  cursor: grab;
}

.viewer-stage.is-swiping {
  cursor: grabbing;
}

.viewer-frame {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  min-height: 0;
  transition: transform 0.28s cubic-bezier(0.22, 0.68, 0.28, 1), opacity 0.2s ease;
}

.viewer-frame.is-dragging {
  transition: none;
}

.viewer-image {
  display: block;
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 100%;
  border-radius: 10px;
  object-fit: contain;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.5);
  animation: photo-fade 0.28s ease both;
  -webkit-user-drag: none;
}

.viewer-empty {
  margin: 0;
  padding: 0 24px;
  color: rgba(255, 255, 255, 0.66);
  font-size: 18px;
  text-align: center;
}

.viewer-nav {
  position: absolute;
  top: 50%;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  cursor: pointer;
  transform: translateY(-50%);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: background 0.2s ease, transform 0.2s ease;
}

.viewer-nav:hover {
  background: rgba(255, 255, 255, 0.2);
}

.viewer-nav:active {
  transform: translateY(-50%) scale(0.94);
}

.viewer-nav:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.7);
  outline-offset: 2px;
}

.viewer-nav--prev {
  left: 10px;
}

.viewer-nav--next {
  right: 10px;
}

.viewer-caption {
  flex: none;
  padding: 10px 26px calc(env(safe-area-inset-bottom, 0px) + 24px);
  text-align: center;
}

.viewer-caption__text {
  margin: 0;
  color: #fff;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.5;
}

.viewer-caption__note {
  margin: 6px 0 0;
  color: rgba(255, 255, 255, 0.62);
  font-size: 18px;
  line-height: 1.5;
}

@keyframes viewer-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes photo-fade {
  from {
    opacity: 0;
    transform: scale(0.985);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .photo-viewer,
  .viewer-image {
    animation: none;
  }

  .viewer-frame,
  .viewer-close,
  .viewer-nav {
    transition: none;
  }
}
</style>
