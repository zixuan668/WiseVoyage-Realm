<template>
  <scroll-view class="dashboard" :scroll-y="true" :show-scrollbar="false">
    <view class="dashboard-content">
      <view class="dashboard-header">
        <image class="dashboard-blossom" src="/static/park-dashboard/blossom.webp" mode="aspectFit" aria-hidden="true" />
        <image class="dashboard-brand" src="/static/park-dashboard/brand.webp" mode="aspectFit" :aria-label="t('智游知境')" />
        <view class="dashboard-divider" aria-hidden="true"></view>
        <button class="dashboard-region" @tap="chooseRegion">
          <text>{{ t('北京 · 颐和园') }}</text><view class="dashboard-triangle" aria-hidden="true"></view>
        </button>
      </view>
      <view class="dashboard-hero">
        <ParkHero :active="active && pageShown" />
      </view>
      <view class="dashboard-intro" :class="{ 'dashboard-intro-ready': introStarted }">
        <view class="dashboard-title" role="heading" :aria-label="t('颐和园 · 山水入画')">
          <image v-if="t('颐和园 · 山水入画') === '颐和园 · 山水入画'" src="/static/park-dashboard/headline.webp"
            mode="aspectFit" class="dashboard-headline" aria-hidden="true" />
          <text v-else class="dashboard-headline-text">{{ t('颐和园 · 山水入画') }}</text>
        </view>
        <text class="dashboard-subtitle">{{ t('湖光山色，尽览皇家园林之美') }}</text>
      </view>
      <view class="dashboard-grid">
        <button v-for="item in entries" :key="item.key" class="dashboard-tile"
          :aria-label="t(item.label)" @tap="open(item.key)">
          <view class="dashboard-tile-icon" :class="{'planning-icon':item.key==='plan'}"><DashboardIcon :name="item.icon" /></view>
          <text>{{ t(item.label) }}</text>
        </button>
      </view>
      <button class="dashboard-map" :aria-label="t('查看景区地图')" @tap="open('map')">
        <view class="dashboard-map-art" aria-hidden="true"><image src="/static/park-dashboard/guide-banner.webp" mode="scaleToFill" /></view>
        <view class="dashboard-map-content"><DashboardIcon name="map" /><view class="dashboard-divider" aria-hidden="true"></view><text>{{ t('查看景区地图') }}</text><DashboardIcon name="next" /></view>
      </button>
      <button class="dashboard-notice" :aria-label="t('官方通知')" @tap="open('notice')">
        <view class="dashboard-notice-icon"><DashboardIcon name="bell" /></view>
        <text class="dashboard-notice-title">{{ t('官方通知') }}</text>
        <view class="dashboard-divider" aria-hidden="true"></view>
        <text class="dashboard-notice-copy">{{ t('颐和园游览提示及开放时间') }}</text>
        <DashboardIcon name="next" />
      </button>
    </view>
  </scroll-view>
  <FloatingTourButton v-if="pendingRoute" :label="t('继续导览')" @activate="resumeRoute" />
</template>

<script>
import { loadScenicCatalog, nativeCompanionUrl } from '../../common/scenic-api.js'
import ParkHero from '../../components/ParkHero.vue'
import DashboardIcon from '../../components/DashboardIcon.vue'
import FloatingTourButton from '../../components/FloatingTourButton.vue'
import { CLAIM_ROUTE, parseClaim, saveClaim } from '../../common/station-claim.js'
import { isLocalStationOrigin } from '../../common/config.js'

const entries = [
  { key: 'catalog', label: '景点图鉴', icon: 'pavilion' },
  { key: 'plan', label: '路径规划', icon: 'planning' },
  { key: 'wander', label: '随心逛', icon: 'compass' },
  { key: 'featured', label: '推荐主题路线', icon: 'layers' },
  { key: 'notice', label: '官方通知', icon: 'megaphone' },
  { key: 'scan', label: '扫码领取路线', icon: 'scan' },
]
const destinations = {
  catalog: '/pages/scenic/scenic',
  plan: '/pages/scenic/scenic?view=plan',
  wander: '/pages/tour-guide/tour-guide?wander=1',
  featured: '/pages/featured/featured',
  map: '/pages/park-map/park-map',
  notice: '/pages/park-map/park-map?view=notices',
}

export default {
  components: { ParkHero, DashboardIcon, FloatingTourButton },
  props: { active: { type: Boolean, default: true } },
  emits: ['ai', 'map-change'],
  data() {
    return { entries, pageShown: false, introStarted: false, scanning: false, pendingRoute: null }
  },
  onShow() {
    this.pageShown = true
    this.introStarted = true
    this.loadPendingRoute()
    loadScenicCatalog().catch(() => {})
  },
  onHide() { this.pageShown = false },
  methods: {
    chooseRegion() { uni.showActionSheet({ itemList: [this.t('北京 · 颐和园')] }) },
    open(key) {
      if (key === 'scan') { this.scan(); return }
      if (key === 'plan') { this.openPlan(); return }
      if (destinations[key]) uni.navigateTo({ url: destinations[key] })
    },
    openPlan() {
      // 不带任何“看过”的景点；路径规划只显示用户手动加入的景点。
      uni.navigateTo({ url: destinations.plan })
    },
    loadPendingRoute() {
      try {
        const route = uni.getStorageSync('pending-tour-route')
        const ids = Array.isArray(route?.ids) ? route.ids : []
        this.pendingRoute = ids.length ? route : null
      } catch (_) { this.pendingRoute = null }
    },
    resumeRoute() {
      const route = this.pendingRoute
      if (!route?.ids?.length) return
      try {
        // 已经进入过数字人讲解页时，悬浮球直接回到讲解页，不再经过「选择伴游」
        let last = null
        try { last = uni.getStorageSync('xingyun-last-session') } catch (_) {}
        const sid = Number(last && last.sessionId)
        if (Number.isInteger(sid) && sid > 0) {
          uni.navigateTo({ url: '/pages/tour/tour?sessionId=' + sid })
          return
        }
        // 没有讲解会话：打开「生成方案」后的路线结果页（含景点列表和开始导览）
        uni.navigateTo({ url: '/pages/scenic/scenic?view=plan&result=1' })
      } catch (error) {
        uni.showToast({ title: this.t('路线已失效，请重新规划'), icon: 'none' })
        this.pendingRoute = null
      }
    },
    scan() {
      if (this.scanning) return
      // #ifdef H5
      uni.navigateTo({ url: CLAIM_ROUTE })
      // #endif
      // #ifndef H5
      if (typeof uni.scanCode !== 'function') { uni.navigateTo({ url: CLAIM_ROUTE }); return }
      this.scanning = true
      uni.scanCode({
        onlyFromCamera: false,
        scanType: ['qrCode'],
        success: result => {
          let claim
          try { claim = parseClaim(result?.result) } catch (_) {}
          if (!claim || (claim.origin && !isLocalStationOrigin(claim.origin))) {
            uni.showToast({ title: this.t('请扫描网页上的路线领取码'), icon: 'none' })
            return
          }
          // 走统一的 pending 记录，保留二维码里的网页端规划条件（prefs）。
          try { saveClaim(result?.result || '') } catch (_) {}
          uni.navigateTo({ url: CLAIM_ROUTE })
        },
        fail: error => {
          if (!String(error?.errMsg || '').includes('cancel')) uni.navigateTo({ url: CLAIM_ROUTE })
        },
        complete: () => { this.scanning = false },
      })
      // #endif
    },
  },
}
</script>

<style scoped>
.dashboard {
  --dash-ink: #282332; --dash-accent: #7861bd;
  width: 100%; height: 100%; color: var(--dash-ink);
  background: #ffffff;
}
.dashboard-content {
  padding: var(--status-bar-height, 0px) 0 calc(76px + env(safe-area-inset-bottom));
  box-sizing: border-box; min-height: 100%; font-family: var(--app-font-family, sans-serif);
}
.dashboard button {
  color: inherit; margin: 0; padding: 0; background: none; border: 0; line-height: inherit;
  font: inherit; text-align: inherit; -webkit-tap-highlight-color: transparent;
}
.dashboard button::after { border: 0; }
.dashboard button:focus-visible { outline: 2px solid #7963cc; outline-offset: 2px; }
.dashboard-header {
  height: 137rpx; display: flex; align-items: flex-start; padding: 12rpx 38rpx 0;
  gap: 24rpx; box-sizing: border-box; position: relative; isolation: isolate;
}
.dashboard-brand,.dashboard-blossom,.dashboard-headline{filter:brightness(1.06)}
.dashboard-brand { width: 208rpx; height: 82rpx; flex: none; }
.dashboard-blossom {
  width: 269rpx; height: 131rpx; position: absolute; top: 0; right: 0;
  z-index: -1; pointer-events: none;
}
.dashboard-divider { flex: none; width: 2rpx; background: #574780; }
.dashboard-header > .dashboard-divider { height: 47rpx; margin-top: 22rpx; }
.dashboard .dashboard-region {
  display: flex; align-items: center; gap: 11rpx; min-height: 76rpx;
  font-size: 25rpx; font-weight: 600; white-space: nowrap;
}
.dashboard-triangle {
  width: 0; height: 0; border-left: 8rpx solid transparent; border-right: 8rpx solid transparent;
  border-top: 11rpx solid #2b205e;
}
.dashboard-hero { margin: 1rpx 18rpx 0; }
.dashboard-intro { text-align: center; margin-top: 23rpx; }
.dashboard-intro-ready { animation: dashboard-caption .6s ease-out both; }
@keyframes dashboard-caption { from { opacity: 0; } to { opacity: 1; } }
.dashboard-title { display: flex; justify-content: center; align-items: center; min-height: 64rpx; }
.dashboard-headline { display: block; width: 642rpx; height: 64rpx; max-width: 91%; mix-blend-mode: multiply; }
.dashboard-headline-text { font-size: 43rpx; font-weight: 700; color: #594a93; }
.dashboard-subtitle { display: block; margin: 14rpx 16rpx 23rpx; font-size: 25rpx; color: #8975be; letter-spacing: .055em; }
.dashboard-grid {
  display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 20rpx 17rpx;
  margin: 0 25rpx; padding: 0; border-radius: 0;
  background: transparent; box-shadow: none;
}
.dashboard .dashboard-tile {
  border-radius: 31rpx; min-height: 143rpx; min-width: 0; display: flex;
  flex-direction: column; align-items: center; justify-content: center; gap: 8rpx;
  background: #ffffff; color: #282332; border: 1px solid #dcd3ee;
  box-shadow: none; padding: 10rpx 2rpx;
  box-sizing: border-box; text-align: center; font-size: 24.5rpx; font-weight: 600;
  transition: transform .16s ease;
}
.dashboard .dashboard-tile text { color: #282332; }
.dashboard .dashboard-tile:active, .dashboard .dashboard-map:active, .dashboard .dashboard-notice:active { transform: scale(.97); }
.dashboard-tile-icon {
  width: 70rpx; height: 70rpx; display: flex; align-items: center; justify-content: center;
  border-radius: 22rpx; background: #f5f5f7; flex: none;
}
.dashboard-tile-icon.planning-icon{border-radius:50%;background:#f5f5f7;color:#7861bd}
.dashboard-tile-icon.planning-icon :deep(.wander-icon){color:#7861bd}
.dashboard-tile :deep(.wander-icon) { width: 46rpx; height: 46rpx; color: var(--dash-accent); }
.dashboard .dashboard-map {
  width: calc(100% - 50rpx); height: 123rpx; display: block; position: relative;
  margin: 29rpx 25rpx 0; border-radius: 29rpx; overflow: hidden; background: #ffffff; border:1px solid #dcd3ee;box-sizing:border-box;
  transition: transform .16s ease;
}
.dashboard-map image, .dashboard-map uni-image { width: 100%; height: 100%; display: block; }
.dashboard-map-art{position:absolute;top:0;right:0;width:38%;height:100%;overflow:hidden;pointer-events:none;-webkit-mask-image:linear-gradient(90deg,transparent,#000 48%);mask-image:linear-gradient(90deg,transparent,#000 48%)}
.dashboard .dashboard-map-art image{position:absolute;right:0;top:0;width:263.16%;height:100%;filter:brightness(1.06)}
.dashboard-map-content{position:relative;z-index:1;display:flex;align-items:center;gap:18rpx;height:100%;padding:0 42rpx;color:#536379}
.dashboard-map-content>text{font-size:30rpx;font-weight:600;white-space:nowrap;color:#282332}
.dashboard-map-content>.dashboard-divider{height:48rpx;background:#a7b3c2}
.dashboard-map-content :deep(.wander-icon){width:44rpx;height:44rpx;flex:none}
.dashboard-map-content :deep(.wander-icon:first-child){width:54rpx;height:54rpx;color:var(--dash-accent)}
.dashboard .dashboard-notice {
  display: flex; align-items: center; gap: 12rpx; width: calc(100% - 50rpx); min-height: 80rpx;
  margin: 28rpx 25rpx 0; padding: 7rpx 15rpx; border-radius: 29rpx; box-sizing: border-box;
  border: 1px solid #dcd3ee; background: #ffffff; box-shadow: none; transition: transform .16s ease;
}
.dashboard-notice-icon {
  display: grid; place-items: center; width: 59rpx; height: 59rpx; flex: none;
  border-radius: 50%; color: #7861bd; background: #f5f5f7; box-shadow: none;
}
.dashboard-notice-icon :deep(.wander-icon) { width: 33rpx; height: 33rpx; }
.dashboard-notice-title { font-size: 25rpx; font-weight: 700; white-space: nowrap; }
.dashboard-notice .dashboard-divider { height: 27rpx; margin: 0 4rpx 0 12rpx; }
.dashboard-notice-copy { flex: 1; min-width: 0; font-size: 19rpx; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dashboard-notice > :deep(.wander-icon) { width: 30rpx; height: 30rpx; flex: none; color: #51408c; }
@media (prefers-reduced-motion: reduce) {
  .dashboard-intro-ready { animation: none; }
  .dashboard button { transition: none; }
}
</style>
