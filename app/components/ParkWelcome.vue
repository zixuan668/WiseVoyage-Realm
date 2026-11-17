<template>
  <view class="park-welcome" @touchstart="startSwipe" @touchmove="moveSwipe"
    @touchend="endSwipe" @touchcancel="resetSwipe">
    <view class="park-welcome-content" :class="{ 'is-dragging': dragging, 'is-leaving': leaving }"
      :style="{ '--welcome-offset': offset + 'px' }">
      <view class="park-welcome-heading" role="heading"
        :aria-label="english ? 'Hi! welcome to Summer Palace' : 'Hi! welcome to 颐和园'">
        <image class="park-welcome-hi" src="/static/welcome-summer-palace/hi.svg" mode="scaleToFill" aria-hidden="true" />
        <view class="park-welcome-line" aria-hidden="true">
          <text class="park-welcome-word">welcome to</text>
          <text class="park-welcome-place" :class="{ 'is-english': english }">{{ english ? 'Summer Palace' : '颐和园' }}</text>
        </view>
      </view>
      <button class="park-welcome-enter" :disabled="leaving"
        :aria-label="english ? 'Swipe up or tap to continue' : '上滑或点击继续'" @tap="enter">
        <image class="park-welcome-chevron" src="/static/welcome-summer-palace/chevrons.svg" mode="aspectFit" aria-hidden="true" />
      </button>
    </view>
  </view>
</template>

<script>
export default {
  props: { english: Boolean },
  emits: ['continue'],
  data() {
    return { start: null, offset: 0, dragging: false, leaving: false }
  },
  beforeUnmount() { clearTimeout(this.exitTimer) },
  methods: {
    startSwipe(event) {
      if (this.leaving || event.touches.length !== 1) return
      this.start = event.touches[0].clientY
    },
    moveSwipe(event) {
      if (this.start === null || this.leaving || event.touches.length !== 1) return
      this.offset = Math.max(-110, Math.min(0, event.touches[0].clientY - this.start))
      this.dragging = this.offset < 0
    },
    endSwipe(event) {
      if (this.start !== null && this.start - (event.changedTouches[0]?.clientY ?? this.start) >= 56) this.enter()
      else this.resetSwipe()
    },
    resetSwipe() { this.start = null; this.offset = 0; this.dragging = false },
    enter() {
      if (this.leaving) return
      this.start = null
      this.dragging = false
      this.leaving = true
      this.exitTimer = setTimeout(() => this.$emit('continue'), 360)
    },
  },
}
</script>

<style scoped>
@font-face {
  font-family: 'Palace Welcome';
  src: url('/static/welcome-summer-palace/palace-welcome-bold.woff2') format('woff2');
  font-weight: 700;
  font-display: swap;
}
.park-welcome {
  position: absolute; inset: 0; z-index: 9; overflow: hidden; touch-action: none; color: #fff;
  background: linear-gradient(0deg,#122643 0%,#15284148 39%,transparent 68%),
    url('/static/welcome-summer-palace/seventeen-arch-bridge.jpg') 46.5% top / auto 112% no-repeat #182942;
}
.park-welcome-content {
  position: absolute; left: 0; right: 0; bottom: max(8%,env(safe-area-inset-bottom));
  transform: translateY(var(--welcome-offset)); transition: transform 360ms ease-out, opacity 360ms ease-out;
}
.park-welcome-content.is-dragging { transition: none; }
.park-welcome-content.is-leaving { transform: translateY(calc(var(--welcome-offset) - 105px)); opacity: 0; }
.park-welcome-heading { width: 81%; max-width: 480px; margin: 0 auto; }
.park-welcome-hi { display: block; width: min(44vw, 27vh); height: min(25vw, 17vh); }
.park-welcome-line { display: flex; align-items: baseline; gap: 8px; white-space: nowrap; margin-top: 7px; }
.park-welcome-word { font: 300 min(8.2vw,4.2vh)/1.15 'Segoe UI',sans-serif; }
.park-welcome-place { font: 700 min(7.4vw,4vh)/1.16 'Palace Welcome','KaiTi',serif; }
.park-welcome-place.is-english { font: 700 min(4.7vw,2.5vh)/1.16 'Segoe UI',sans-serif; }
.park-welcome .park-welcome-enter {
  margin: 23px auto 0; padding: 10px; width: 70px; height: 64px; border: 0;
  display: flex; align-items: center; justify-content: center; background: transparent;
}
.park-welcome-enter::after { border: 0; }
.park-welcome-chevron { width: 39px; height: 41px; animation: park-welcome-float 2.15s ease-in-out infinite; }
@keyframes park-welcome-float { 0%, 100% { transform: translateY(2px); } 50% { transform: translateY(-6px); } }
@media (prefers-reduced-motion: reduce) {
  .park-welcome-chevron { animation: none; }
  .park-welcome-content { transition: none; }
}
</style>
