<template>
  <view class="confirm-overlay" @touchstart.stop="" @touchmove.stop.prevent="" @touchend.stop="" @touchcancel.stop="" @tap="$emit('cancel')">
    <view class="confirm-panel" :class="{ 'confirm-panel-plain': plain }" @tap.stop>
      <text class="confirm-title">{{ title }}</text>
      <text class="confirm-content">{{ content }}</text>
      <view class="confirm-actions">
        <button class="confirm-cancel" @tap="$emit('cancel')">{{ cancelLabel }}</button>
        <button class="confirm-primary" @tap="$emit('confirm')">{{ confirmLabel }}</button>
      </view>
    </view>
  </view>
</template>
<script>
export default {
  props: {title: {type: String, default: ''}, content: {type: String, default: ''}, cancelLabel: {type:String,default:'取消'}, confirmLabel: {type:String,default:'确定'}, plain: {type: Boolean, default: false}},
  emits: ['confirm', 'cancel'],
}
</script>
<style scoped>
.confirm-overlay{position:fixed!important;top:0;right:0;bottom:0;left:0;z-index:2000!important;display:flex;align-items:center;justify-content:center;padding:40rpx;box-sizing:border-box;background:rgba(30,41,59,0.32)}
.confirm-panel{width:100%;max-width:600rpx;padding:40rpx;box-sizing:border-box;border-radius:48rpx;background:#ffffff;background-image:linear-gradient(135deg,rgba(99,102,241,0.12),transparent 50%);border:1rpx solid rgba(99,102,241,0.12);box-shadow:var(--ng-glass-shadow);backdrop-filter: none}
.confirm-title{display:block;color:#1f2937;font-size:36rpx;font-family:var(--app-font-family);text-align:center}
.confirm-content{display:block;margin:24rpx 0 36rpx;color:#64748b;font-size:28rpx;line-height:1.8;text-align:center}
.confirm-actions{display:flex;gap:20rpx}.confirm-actions button{flex:1;margin:0;font-size:28rpx;line-height:80rpx;border-radius:32rpx;background:rgba(99,102,241,0.06);color:#1f2937;border:1rpx solid rgba(99,102,241,0.12)}.confirm-actions button::after{border:0}.confirm-actions .confirm-primary{background:rgba(99,102,241,0.15);border-color:rgba(99,102,241,0.25);color:#4338ca}.confirm-primary:active{background:rgba(99,102,241,0.22)}
</style>

<style scoped>
.confirm-panel{background:var(--ng-glass-blue-bg);background-image:none;border:0;box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.95),0 18px 54px rgba(59,43,110,.22),0 3px 12px rgba(59,43,110,.1);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}.confirm-actions .confirm-cancel{background:#fff;border-color:#ddd7f3}.confirm-actions .confirm-primary{background:#4f46e5;color:#fff;border-color:transparent}.confirm-actions .confirm-primary:active{background:#4338ca;color:#fff}
.confirm-panel.confirm-panel-plain{background:#ffffff;background-image:none;border:1rpx solid #e3ddf3;box-shadow:0 18px 54px rgba(59,43,110,.18),0 3px 12px rgba(59,43,110,.08)}
.confirm-panel-plain .confirm-primary{background:var(--ng-glass-blue-bg);color:var(--ng-soft-blue-text);border:0;box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.92)}
.confirm-panel-plain .confirm-primary:active{background:#e6f0ff;color:var(--ng-soft-blue-text)}
</style>