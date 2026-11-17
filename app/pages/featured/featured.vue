<template>
  <view class="featured-page">
    <view class="nav" :style="{ paddingTop: statusH + 'px' }">
      <button class="nav-back app-back-btn" :aria-label="t('返回')" @tap="goBack"><view class="app-back-icon" aria-hidden="true"></view></button>
      <text class="nav-title">{{ t('推荐主题路线') }}</text>
      <view class="nav-spacer" aria-hidden="true"></view>
    </view>

    <scroll-view scroll-y class="route-scroll" :show-scrollbar="false">
      <view class="route-inner">
        <text class="route-lead">{{ t('精选动线，按时间与兴趣出发') }}</text>

        <view v-if="loading" class="route-skeleton" aria-busy="true" aria-label="主题路线加载中">
          <view v-for="n in 3" :key="n" class="sk-card">
            <view class="sk-cover"></view>
            <view class="sk-line w70"></view>
            <view class="sk-line w40"></view>
            <view class="sk-line w90"></view>
          </view>
        </view>

        <view v-else-if="error" class="state">
          <text>{{ t(error) }}</text>
          <button @tap="load">{{ t('重试') }}</button>
        </view>

        <view v-else-if="!routes.length" class="state"><text>{{ t('暂无主题路线') }}</text></view>

        <view v-else class="route-list">
          <button v-for="(r, index) in routes" :key="r.route_id" class="route-card" @tap="openRoute(r)">
            <view class="route-cover">
              <image v-if="r.cover && !failed[r.route_id]" :src="r.cover" mode="aspectFill" @error="failed[r.route_id] = true" />
              <view v-else class="route-cover-fallback"></view>
              <view class="route-cover-shade"></view>
              <text class="route-time">{{ r.estimated_time_minutes ? r.estimated_time_minutes + t('分钟') : t('时长待配置') }}</text>
              <text class="route-index">0{{ index + 1 }}</text>
            </view>
            <view class="route-body">
              <text class="route-name">{{ t(r.name) }}</text>
              <view class="route-meta-row">
                <text class="route-meta">{{ (r.spot_ids || []).length }} {{ t('个景点') }} · {{ distanceText(r) }}</text>
                <view class="route-chips">
                  <text v-for="name in (r.spot_names || []).slice(0, 4)" :key="name">{{ t(name) }}</text>
                </view>
              </view>
              <text v-if="r.description" class="route-desc">{{ t(r.description) }}</text>
            </view>
          </button>
        </view>
      </view>
    </scroll-view>

    <view class="dock-fixed"><PageDock :active="0" /></view>

    <view v-if="detail" class="sheet-mask" @tap="detail = null">
      <view class="sheet" @tap.stop>
        <view class="sheet-head">
          <text>{{ t('路线详情') }}</text>
          <button :aria-label="t('关闭')" @tap="detail = null">×</button>
        </view>
        <scroll-view scroll-y class="sheet-scroll" :show-scrollbar="false">
          <text class="sheet-title">{{ t(detail.name) }}</text>
          <text class="sheet-meta">{{ (detail.spot_ids || []).length }} {{ t('个景点') }}<template v-if="detail.estimated_time_minutes"> · {{ detail.estimated_time_minutes }} {{ t('分钟') }}</template></text>
          <text v-if="detail.description" class="sheet-desc">{{ t(detail.description) }}</text>
          <view class="stop-list">
            <view v-for="(name, i) in (detail.spot_names || [])" :key="name + i" class="stop-item">
              <text class="stop-no">{{ i + 1 }}</text>
              <text class="stop-name">{{ t(name) }}</text>
              <text class="stop-metric">{{ stopMetric(i) }}</text>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL, assetUrl } from '../../common/config.js'
import PageDock from '../../components/PageDock.vue'

export default {
  components: { PageDock },
  data() {
    return { statusH: 20, loading: true, error: '', routes: [], failed: {}, detail: null }
  },
  onLoad() {
    const info = uni.getSystemInfoSync()
    this.statusH = info.statusBarHeight || 20
    this.load()
  },
  methods: {
    load() {
      this.loading = true
      this.error = ''
      uni.request({
        url: BASE_URL + '/tour-session/routes',
        method: 'GET',
        timeout: 15000,
        success: response => {
          const list = response.data && response.data.data && response.data.data.route_list
          if (response.statusCode === 200 && Array.isArray(list)) {
            this.routes = list.map(item => Object.assign({}, item, { cover: assetUrl(item.cover_image || '') }))
          } else {
            this.error = '路线加载失败，请重试'
          }
        },
        fail: () => { this.error = '网络连接失败，请重试' },
        complete: () => { this.loading = false },
      })
    },
    distanceText(route) {
      const meters = Number(route.walking_distance_meters)
      if (!Number.isFinite(meters) || meters <= 0) return this.t('园内步行')
      return this.formatMeters(meters)
    },
    formatMeters(meters) {
      return meters >= 1000 ? (meters / 1000).toFixed(1) + ' km' : Math.round(meters) + ' m'
    },
    // 详情弹层里每一站右侧标注“到下一站的步行时间与距离”，末站标注终点。
    stopMetric(index) {
      const count = (this.detail && this.detail.spot_names ? this.detail.spot_names : []).length
      if (index >= count - 1) return this.t('终点')
      const leg = this.detail && this.detail.walking_legs ? this.detail.walking_legs[index] : null
      const meters = leg ? Number(leg.meters) : NaN
      const minutes = leg ? Number(leg.minutes) : NaN
      if (!leg || !leg.available || !Number.isFinite(meters) || !Number.isFinite(minutes) || meters <= 0) {
        return this.t('暂无步行数据')
      }
      return this.t('步行') + ' ' + minutes + this.t('分钟') + ' · ' + this.formatMeters(meters)
    },
    openRoute(route) { this.detail = route },
    goBack() {
      uni.navigateBack({ delta: 1, fail: () => uni.reLaunch({ url: '/pages/tabs/tabs?tab=home' }) })
    },
  },
}
</script>

<style scoped>
.featured-page {
  --feat-ink: #282332; --feat-accent: #6a5ae0;
  height: 100vh; height: 100dvh; display: flex; flex-direction: column; overflow: hidden;
  background: radial-gradient(ellipse at 50% 0%, #fbfaff 0%, #f4f1fd 55%, #efeaf9 100%);
  color: var(--feat-ink);
  box-sizing: border-box; font-family: var(--app-font-family, sans-serif);
}
.featured-page button { margin: 0; padding: 0; border: 0; background: none; font: inherit; color: inherit; line-height: 1.4; }
.featured-page button::after { border: 0; }
.featured-page button:active { transform: scale(0.985); }
.nav { display: flex; align-items: center; gap: 12px; padding: 8px 16px 10px; flex: none; }
.nav-back { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; background: #fff; box-shadow: 0 3px 12px rgba(70, 50, 130, .08); }
.nav-title { flex: 1; text-align: center; font-size: 17px; font-weight: 600; }
.nav-spacer { width: 44px; flex: none; }
.route-scroll { flex: 1; height: 0; min-height: 0; }
.route-inner { padding: 6px 16px calc(92px + env(safe-area-inset-bottom)); max-width: 560px; margin: 0 auto; box-sizing: border-box; }
.dock-fixed { position: fixed; left: 0; right: 0; bottom: 0; z-index: 950; background: #fff; }
.route-lead { display: block; font-size: 13px; color: #7a708f; margin: 2px 2px 14px; }
.route-list { display: flex; flex-direction: column; gap: 16px; }
.route-card { display: block; width: 100%; text-align: left; border-radius: 22px; overflow: hidden; background: #fff; box-shadow: 0 10px 28px -18px rgba(55, 36, 110, .35); }
.route-cover { position: relative; height: 172px; overflow: hidden; background: #ded6f4; }
.route-cover image, .route-cover-fallback { width: 100%; height: 100%; display: block; }
.route-cover-fallback { background: linear-gradient(135deg, #cfc4ee, #e8def8); }
.route-cover-shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(23, 16, 42, .02) 35%, rgba(23, 16, 42, .55) 100%); }
.route-time { position: absolute; left: 12px; top: 12px; padding: 4px 10px; border-radius: 999px; font-size: 12px; color: #33284f; background: rgba(255, 255, 255, .88); backdrop-filter: blur(4px); }
.route-index { position: absolute; right: 14px; bottom: 10px; font-size: 30px; font-weight: 700; color: rgba(255, 255, 255, .82); letter-spacing: 1px; font-variant-numeric: tabular-nums; }
.route-body { padding: 14px 16px 16px; }
.route-name { display: block; font-size: 19px; font-weight: 650; letter-spacing: .2px; }
.route-meta-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 5px; }
.route-meta { flex: none; font-size: 13px; color: #6e6587; }
.route-desc { display: -webkit-box; margin-top: 8px; font-size: 13px; line-height: 1.65; color: #5d5573; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.route-chips { flex: 1; min-width: 0; display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 5px; }
.route-chips text { padding: 2px 7px; border-radius: 999px; background: #f2eefc; color: #63538f; font-size: 10px; line-height: 1.4; }
.state { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 60px 20px; font-size: 14px; color: #6e6587; }
.state button { padding: 8px 20px; border-radius: 999px; background: #eae3fb; color: #5b48a4; }
.route-skeleton { display: flex; flex-direction: column; gap: 16px; }
.sk-card { padding: 0 0 16px; border-radius: 22px; background: #fff; overflow: hidden; box-shadow: 0 10px 28px -18px rgba(55, 36, 110, .28); }
.sk-cover { height: 172px; background: linear-gradient(90deg, #f0edf8 25%, #faf9fe 37%, #f0edf8 63%); background-size: 400% 100%; animation: feat-shimmer 1.4s ease infinite; }
.sk-line { height: 14px; margin: 14px 16px 0; border-radius: 7px; background: linear-gradient(90deg, #f0edf8 25%, #faf9fe 37%, #f0edf8 63%); background-size: 400% 100%; animation: feat-shimmer 1.4s ease infinite; }
.sk-line.w70 { width: 60%; } .sk-line.w40 { width: 34%; } .sk-line.w90 { width: 82%; }
@keyframes feat-shimmer { 0% { background-position: 100% 0; } 100% { background-position: 0 0; } }
.sheet-mask { position: fixed; inset: 0; z-index: 980; background: rgba(28, 19, 47, .34); display: flex; align-items: flex-end; }
.sheet {
  width: 100%; max-height: 78vh; display: flex; flex-direction: column; box-sizing: border-box;
  border-radius: 26px 26px 0 0; padding: 14px 18px calc(18px + env(safe-area-inset-bottom));
  background: linear-gradient(165deg, rgba(255, 255, 255, .92) 0%, rgba(250, 246, 255, .86) 55%, rgba(243, 236, 255, .84) 100%);
  border: 1px solid rgba(126, 102, 222, .46); border-bottom: 0;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, .35), 0 -22px 60px -34px rgba(58, 36, 120, .6), inset 0 1px 0 rgba(255, 255, 255, .95);
  -webkit-backdrop-filter: blur(26px) saturate(1.25); backdrop-filter: blur(26px) saturate(1.25);
}
.sheet-head { display: flex; align-items: center; justify-content: space-between; font-size: 14px; color: #7b7291; }
.sheet-head button { width: 40px; height: 40px; font-size: 22px; color: #4d4562; }
.sheet-scroll { flex: 1; min-height: 0; max-height: 60vh; }
.sheet-title { display: block; font-size: 22px; font-weight: 700; margin: 2px 0 6px; }
.sheet-meta { display: block; font-size: 13px; color: #6e6587; }
.sheet-desc { display: block; margin-top: 10px; font-size: 13px; line-height: 1.7; color: #57506b; }
.stop-list { margin-top: 14px; display: flex; flex-direction: column; gap: 8px; }
.stop-item {
  display: flex; align-items: center; gap: 10px; min-height: 48px; box-sizing: border-box;
  padding: 10px 12px; border-radius: 16px; font-size: 14px;
  background: rgba(255, 255, 255, .62); border: 1px solid rgba(126, 102, 222, .26);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .9), 0 10px 22px -20px rgba(74, 53, 142, .55);
  -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px);
}
.stop-no { width: 24px; height: 24px; flex: none; display: grid; place-items: center; border-radius: 50%; background: rgba(228, 218, 249, .92); color: #5b48a4; font-size: 12px; }
.stop-name { flex: 1; min-width: 0; line-height: 24px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stop-metric { flex: none; margin-left: auto; line-height: 24px; font-size: 12px; color: #7b7291; white-space: nowrap; font-variant-numeric: tabular-nums; }
@media (prefers-reduced-motion: reduce) { .sk-cover, .sk-line { animation: none; } .featured-page button:active { transform: none; } }
</style>
