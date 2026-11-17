<template>
  <view class="skeleton-card" aria-busy="true">
    <view v-if="photo" class="skeleton-photo"></view>
    <view class="skeleton-lines">
      <view v-for="(w, i) in widths" :key="i" class="skeleton-line" :style="{ width: w }"></view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'SkeletonCard',
  props: {
    photo: { type: Boolean, default: false },
    widths: { type: Array, default: () => ['65%', '95%', '50%'] },
  },
}
</script>

<style scoped>
.skeleton-card { display:flex; gap:16rpx; padding:20rpx; margin-bottom:18rpx; border-radius:24rpx; background:var(--ng-surface,#fff); border:1rpx solid rgba(148,163,184,.16); }
.skeleton-photo { width:120rpx; height:120rpx; flex:none; border-radius:16rpx; background:linear-gradient(90deg,rgba(148,163,184,.16) 25%,rgba(148,163,184,.30) 37%,rgba(148,163,184,.16) 63%); background-size:400% 100%; animation:sk-shimmer 1.4s ease infinite; }
.skeleton-lines { flex:1; min-width:0; display:flex; flex-direction:column; justify-content:center; gap:14rpx; }
.skeleton-line { height:22rpx; border-radius:11rpx; background:linear-gradient(90deg,rgba(148,163,184,.16) 25%,rgba(148,163,184,.30) 37%,rgba(148,163,184,.16) 63%); background-size:400% 100%; animation:sk-shimmer 1.4s ease infinite; }
@keyframes sk-shimmer { 0% { background-position:100% 0; } 100% { background-position:0 0; } }
@media (prefers-reduced-motion: reduce) { .skeleton-photo, .skeleton-line { animation:none; } }
</style>
