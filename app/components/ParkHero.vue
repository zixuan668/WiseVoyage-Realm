<template>
  <view class="park-hero" :class="{ 'hero-running': running }" role="img"
    :aria-label="t('昆明湖、十七孔桥与佛香阁')">
    <image class="hero-art" src="/static/park-dashboard/hero.webp" mode="aspectFill" @load="artReady = true" />
    <view class="hero-sky-tint" aria-hidden="true"></view>
    <view class="hero-mist" aria-hidden="true"></view>
    <image class="hero-ripples" src="/static/park-dashboard/ripples.webp" mode="scaleToFill" aria-hidden="true" />
    <image class="hero-willow" src="/static/park-dashboard/willow.webp" mode="scaleToFill" aria-hidden="true" />
    <view class="hero-flight" aria-hidden="true"><view class="hero-bird"></view></view>
  </view>
</template>

<script>
export default {
  props: {
    active: Boolean,
  },
  data() {
    return { artReady: false, foreground: true }
  },
  computed: {
    running() { return this.active && this.foreground && this.artReady },
  },
  mounted() {
    if (typeof uni.onAppHide === 'function') uni.onAppHide(this.pause)
    if (typeof uni.onAppShow === 'function') uni.onAppShow(this.resume)
    // #ifdef H5
    document.addEventListener('visibilitychange', this.updateVisibility)
    this.updateVisibility()
    // #endif
  },
  beforeUnmount() {
    if (typeof uni.offAppHide === 'function') uni.offAppHide(this.pause)
    if (typeof uni.offAppShow === 'function') uni.offAppShow(this.resume)
    // #ifdef H5
    document.removeEventListener('visibilitychange', this.updateVisibility)
    // #endif
  },
  methods: {
    pause() { this.foreground = false },
    resume() { this.foreground = true },
    // #ifdef H5
    updateVisibility() { this.foreground = !document.hidden },
    // #endif
  },
}
</script>

<style scoped>
.park-hero {
  position: relative; width: 100%; aspect-ratio: 812 / 463;
  overflow: hidden; border-radius: 37rpx; isolation: isolate; background: #e4edf4;
}
.hero-art, .hero-sky-tint, .hero-mist, .hero-ripples, .hero-willow, .hero-flight { position: absolute; pointer-events: none; }
.hero-art { inset: 0; width: 100%; height: 100%; animation: hero-arrive .75s ease-out both; }
.hero-sky-tint{inset:0;background:linear-gradient(180deg,rgba(185,216,236,.95),rgba(194,222,238,.72) 24%,rgba(204,228,240,.18) 43%,transparent 55%);mix-blend-mode:color}
.hero-mist {
  top: 9%; left: 19%; width: 62%; height: 17%;
  background: radial-gradient(ellipse closest-side, #fff8ea66, transparent);
  opacity: .32; animation: hero-mist 16s ease-in-out infinite alternate paused;
}
.hero-ripples {
  top: 73%; left: 7%; width: 84%; height: 26%; opacity: .09;
  animation: hero-ripple 4.3s ease-in-out infinite paused;
}
.hero-willow {
  top: -4%; right: -2%; width: 35%; height: 54%; opacity: .46;
  transform-origin: 100% 0; animation: hero-willow 5.2s ease-in-out infinite paused;
}
.hero-flight {
  inset: 0; opacity: 0; transform-origin: 0 0;
  animation: hero-flight 6.2s linear infinite paused;
}
.hero-bird {
  position: absolute; left: 0; top: 0; width: 60rpx; height: 60rpx;
  background: url('/static/park-dashboard/swallow.webp') left top / 200% 200%;
  transform: scaleX(-1);
  animation: hero-wing 1s step-end infinite paused;
}
.hero-running :is(.hero-mist, .hero-willow, .hero-ripples, .hero-flight, .hero-bird) { animation-play-state: running; }
@keyframes hero-arrive { from { opacity: .35; } to { opacity: 1; } }
@keyframes hero-mist { from { transform: translateX(-11%); } to { transform: translateX(12%); } }
@keyframes hero-willow { 0%, 100% { transform: rotate(-.5deg); } 50% { transform: rotate(1.8deg); } }
@keyframes hero-ripple {
  0%, 100% { transform: scale(.95, .9); opacity: .07; }
  55% { transform: scale(1.07, 1.04); opacity: .23; }
}
@keyframes hero-flight {
  0% { transform: translate3d(78%, 27%, 0) scale(.83); opacity: 0; }
  6% { transform: translate3d(74%, 32%, 0) scale(.98); opacity: .95; }
  24% { transform: translate3d(61%, 53%, 0) scale(1.01); opacity: 1; }
  44% { transform: translate3d(45%, 64%, 0) scale(.92); opacity: .98; }
  64% { transform: translate3d(31%, 61%, 0) scale(.73); opacity: .9; }
  85% { transform: translate3d(19%, 49%, 0) scale(.49); opacity: .7; }
  100% { transform: translate3d(10%, 39%, 0) scale(.26); opacity: 0; }
}
@keyframes hero-wing {
  0%, 99% { background-position: left top; }
  17%, 79% { background-position: right top; }
  36%, 62% { background-position: left bottom; }
  51% { background-position: right bottom; }
}
@media (prefers-reduced-motion: reduce) {
  .park-hero :is(.hero-art, .hero-mist, .hero-willow, .hero-ripples, .hero-flight, .hero-bird) { animation: none; }
  .hero-flight, .hero-willow, .hero-mist, .hero-ripples { display: none; }
}
</style>
