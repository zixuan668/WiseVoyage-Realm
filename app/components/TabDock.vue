<template>
  <view class="dock" :style="dockStyle">
    <view class="dock-inner">
      <view class="dock-pill" :style="pillStyle"></view>
      <view v-for="(tab, i) in tabs" :key="tab.key" class="dock-item" :class="{ on: current === i }" @tap="pick(i)">
        <text class="dock-icon iconfont" :class="tab.icon" :style="iconStyle(i)"></text>
        <view class="dock-label-wrap">
          <text class="dock-label" :style="labelStyle(i)">{{ t(tab.label) }}</text>
        </view>
      </view>
    </view>
    <view class="dock-safe"></view>
  </view>
</template>
<script>
const MUTED = [75, 85, 99]
const INK = [31, 41, 55]
const clamp = (v, min, max) => Math.max(min, Math.min(max, v))
export default {
  name: 'TabDock',
  props: {
    current: { type: Number, default: 0 },
    progress: { type: Number, default: 0 },
    hidden: { type: Boolean, default: false },
    aiHidden: { type: Boolean, default: false },
  },
  emits: ['select'],
  data() {
    return {
      tabs: [
        { key: 'tour', icon: 'icon-daolan', label: '智能导览' },
        { key: 'ai', icon: 'icon-aishuziren', label: 'AI小导游' },
        { key: 'mine', icon: 'icon-wode1', label: '我的' },
      ],
    }
  },
  computed: {
    // Match the pager transition without sending per-frame updates across the App bridge.
    hideAmount() { return this.aiHidden || this.hidden ? 1 : 0 },
    dockStyle() {
      const h = clamp(this.hideAmount, 0, 1)
      return {
        transform: 'translate3d(0,' + (h * 108) + '%,0) scale(' + (1 - 0.06 * h) + ')',
        opacity: String(1 - 0.66 * h),
        pointerEvents: h > 0.5 ? 'none' : 'auto',
      }
    },
    pillStyle() {
      return { transform: 'translate3d(' + (clamp(this.progress, 0, 2) * 100) + '%,0,0)' }
    },
  },
  methods: {
    pick(i) { this.$emit('select', i) },
    focus(i) { return clamp(1 - Math.abs(clamp(this.progress, 0, 2) - i), 0, 1) },
    color(i) {
      const focus = this.focus(i)
      const rgb = MUTED.map((c, k) => Math.round(c + (INK[k] - c) * focus))
      return 'rgb(' + rgb.join(',') + ')'
    },
    labelStyle(i) { return { color: this.color(i) } },
    iconStyle(i) {
      const focus = this.focus(i)
      return { color: this.color(i), transform: 'translateY(' + (-1.6 * focus).toFixed(2) + 'px) scale(' + (1 + 0.07 * focus).toFixed(3) + ')' }
    },

  },
}
</script>
<style scoped>
.dock{position:fixed;bottom:0;left:0;right:0;z-index:999;background:var(--ng-surface);border-top:1rpx solid var(--ng-border);will-change:transform,opacity;transform-origin:50% 100%;transition:transform .22s ease,opacity .22s ease}
.dock-inner{position:relative;display:flex;align-items:stretch;padding:6px;min-height:64px;box-sizing:border-box}
.dock-pill{position:absolute;top:2px;bottom:2px;left:6px;width:calc((100% - 12px)/3);box-sizing:border-box;border:0;border-radius:30px;background:var(--ng-raised);pointer-events:none;will-change:transform;transition:transform .26s cubic-bezier(.22,.61,.36,1)}
.dock-item{position:relative;flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:50px;gap:3px;padding:0;background:transparent}
.dock-icon{font-size:26px;line-height:1.15;transition:transform .26s ease,color .26s ease}
.dock-label-wrap{position:relative;width:100%;min-height:22px;display:flex;align-items:center;justify-content:center}
.dock-label{transition:color .26s ease;display:block;max-width:100%;font-size:13px;line-height:1.3;white-space:normal;letter-spacing:0;text-align:center}
.dock-item.on .dock-label{font-weight:700}
.dock-safe{height:env(safe-area-inset-bottom);min-height:0}
@media(prefers-reduced-motion:reduce){.dock,.dock-pill,.dock-icon,.dock-label{transition:none}}
</style>
