<template>
  <view class="zhiyou-logo" :class="{ stacked, animated, english: tourLanguage === 'en' }" :aria-label="tourLanguage === 'en' ? 'Zhiyou Zhijing' : '智游知境'">
    <view class="zhiyou-icon"><image class="zhiyou-app-icon" src="/static/brand/brand-user.png" mode="scaleToFill" /></view>
    <view class="zhiyou-wordmark"><image class="zhiyou-wordmark-sheet" src="/static/brand/brand-user.png" mode="scaleToFill" /></view>
  </view>
</template>
<script>
export default { props: { stacked: { type: Boolean, default: false }, animated: { type: Boolean, default: false } } }
</script>
<style scoped>
.zhiyou-logo { display:flex; align-items:center; justify-content:center; gap:12rpx; height:72rpx; }
.zhiyou-icon,.zhiyou-wordmark { position:relative; overflow:hidden; flex-shrink:0; }
.zhiyou-icon { width:72rpx; height:72rpx; border-radius:16rpx; }
.zhiyou-wordmark { width:210rpx; height:64.02rpx; }
.zhiyou-app-icon { position:absolute; display:block; width:321.778%; height:208.846%; left:-31.111%; top:-23.077%; }
.zhiyou-wordmark-sheet { position:absolute; width:206.857%; height:387.857%; left:-85.714%; top:-107.143%; }
.english .zhiyou-wordmark-sheet { width:321.778%;height:493.636%;left:-211.111%;top:-345.455%; }
.stacked { height:auto; flex-direction:column; gap:20rpx; }
.stacked .zhiyou-icon { width:184rpx; height:212.62rpx; border-radius:0; }
.stacked .zhiyou-wordmark { width:390rpx; height:156rpx; }
.stacked.english .zhiyou-wordmark { width:390rpx; height:190.67rpx; }

.animated .zhiyou-icon{animation:logoBounce 3.2s ease-in-out infinite;transform-origin:center bottom;}
@keyframes logoBounce{0%,70%,100%{transform:translateY(0)}80%{transform:translateY(-16rpx)}90%{transform:translateY(0)}95%{transform:translateY(-5rpx)}}
@media(prefers-reduced-motion:reduce){.animated .zhiyou-icon{animation:none;}}
</style>
