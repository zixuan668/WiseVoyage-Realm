<template>
  <view class="home-orb" :class="{dragging}" :style="{left:x+'px',top:y+'px',width:size+'px',height:size+'px'}" role="button" :aria-label="'返回首页'" @touchstart.stop="start" @touchmove.stop.prevent="move" @touchend.stop="end" @tap="home">
    <text class="iconfont icon-fangzi home-orb-icon" :style="{fontSize:Math.round(size*0.46)+'px'}" aria-hidden="true"></text>
  </view>
</template>

<script>
// 讲解页左上角的悬浮小房子：可拖动，点击回首页。
export default {
  props: { top: { type: Number, default: 80 }, size: { type: Number, default: 36 } },
  emits: ['home'],
  data() { return { ready: false, dragging: false, x: 16, y: 80 } },
  mounted() {
    const info = uni.getWindowInfo ? uni.getWindowInfo() : uni.getSystemInfoSync()
    this._width = info.windowWidth
    this._height = info.windowHeight
    this.y = Math.max(info.safeAreaInsets?.top || 20, this.top)
    this.x = 16
    this.ready = true
  },
  methods: {
    start(e) {
      const p = e.touches && e.touches[0]
      if (!p) return
      this._touch = { x: p.clientX, y: p.clientY, left: this.x, top: this.y }
      clearTimeout(this._hold)
      this._hold = setTimeout(() => { this.dragging = true }, 180)
    },
    move(e) {
      if (!this._touch) return
      const p = e.touches && e.touches[0]
      if (!p) return
      const dx = p.clientX - this._touch.x
      const dy = p.clientY - this._touch.y
      if (Math.abs(dx) + Math.abs(dy) > 8) this.dragging = true
      if (!this.dragging) return
      const maxX = this._width - this.size - 8, maxY = this._height - this.size - 8
      this.x = Math.max(8, Math.min(maxX, this._touch.left + dx))
      this.y = Math.max(8, Math.min(maxY, this._touch.top + dy))
    },
    end() {
      clearTimeout(this._hold)
      this._touch = null
      this.dragging = false
      this.x = this.x + this.size / 2 < this._width / 2 ? 12 : this._width - this.size - 12
    },
    home() {
      if (this.dragging) return
      this.$emit('home')
      uni.reLaunch({ url: '/pages/tabs/tabs?tab=home' })
    },
  },
}
</script>

<style scoped>
.home-orb {
  position: fixed; z-index: 2000;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; background: rgba(255,255,255,.92);
  border: 1px solid rgba(139,120,230,.5);
  box-shadow: 0 6px 20px rgba(90,70,180,.18), inset 0 1px 0 rgba(255,255,255,.95);
  -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
  transition: left .18s ease, top .18s ease, transform .12s ease;
}
.home-orb.dragging { transition: none; transform: scale(1.06); }
.home-orb-icon { color: #5b4a9e; }
</style>
