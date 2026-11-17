<template>
  <view class="page aurora-page checkins-page">
    <!-- #ifdef APP-PLUS -->
    <view class="app-status-bar-shield" aria-hidden="true"></view>
    <!-- #endif -->
    <view class="aurora-background" aria-hidden="true"></view>
    <view class="hand-paper" aria-hidden="true"></view>
    <view class="nav" :style="{paddingTop:headerTop+'px'}">
      <view class="nav-back app-back-btn" @tap="goBack" role="button" aria-label="返回">
        <view class="app-back-icon"></view>
      </view>
      <text class="nav-title">我的打卡</text>
    </view>
    <scroll-view scroll-y class="main" refresher-enabled :refresher-triggered="refreshing" @refresherrefresh="onRefresh">
      <view v-if="!items.length" class="empty">
        <view class="empty-badge">
          <image class="empty-icon" src="/static/icons/checkin.png" mode="aspectFit" />
        </view>
        <text class="empty-title">还没有打卡记录</text>
        <text class="empty-hint">打开景点详情 → 开始导览 → 地图步行 → 到达打卡，打卡后会出现在这里。</text>
        <button class="empty-cta" @tap="goScenic">去景点打卡</button>
      </view>
      <view v-else>
        <view class="hand-head">
          <text class="hand-head-count">已集章 <text class="hand-num">{{ items.length }}</text> 枚</text>
        </view>
        <view class="stack">
        <view
          v-for="(item, idx) in stackItems"
          :key="item.id"
          class="stack-card"
          :class="{ top: idx === 0, flying: flying }"
          :style="cardStyle(idx)"
          @touchstart="onStart"
          @touchmove.stop.prevent="onMove"
          @touchend="onEnd"
          @tap="idx === 0 ? preview(item) : null"
        >
          <view class="hand-card">
            <view class="hand-tape" aria-hidden="true"></view>
            <view class="hand-photo-wrap">
              <image v-if="item.image" class="hand-photo" :src="item.image" mode="aspectFill" />
              <view v-else class="hand-photo hand-photo-empty"></view>
              <view class="hand-seal" aria-hidden="true">
                <text class="seal-park">颐和园</text>
                <text class="seal-name">{{ item.spot_name }}</text>
                <text class="seal-date">{{ item.dayText || '打卡' }}</text>
              </view>
            </view>
            <view class="hand-panel">
              <text class="card-name">{{ item.spot_name }}</text>
              <text class="card-quote">{{ item.quote ? '「' + item.quote + '」' : '「不知道去哪的时候，就随便走吧」' }}</text>
              <view class="card-stats">
                <view class="card-stat"><text class="stat-label">步行</text><text class="stat-value">{{ item.walk || '—' }}</text></view>
                <view class="card-stat"><text class="stat-label">用时</text><text class="stat-value">{{ item.duration || '—' }}</text></view>
                <view class="card-stat"><text class="stat-label">日期</text><text class="stat-value">{{ item.dayText || '—' }}</text></view>
              </view>
              <view class="card-del" @tap.stop="remove(item)" role="button" aria-label="删除"><text>删除</text></view>
            </view>
          </view>
        </view>
        </view>
      </view>
    </scroll-view>
    <PageDock :active="2" />
  </view>
</template>

<script>
import { BASE_URL } from '../../common/config.js'
import { SCENIC_COVERS } from '../../common/scenic-covers.js'
import PageDock from '../../components/PageDock.vue'
export default {
  components: { PageDock },
  data: function () {
    return { headerTop: 48, items: [], deviceId: '', refreshing: false, flying: false, dx: 0, dy: 0, startX: 0, startY: 0, dragging: false }
  },
  onLoad: function () {
    const s = uni.getSystemInfoSync()
    this.headerTop = (s.statusBarHeight || 20) + 6
    let device = ''
    try { device = uni.getStorageSync('device_id') || '' } catch (e) {}
    if (!device) {
      device = 'dev-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
      try { uni.setStorageSync('device_id', device) } catch (e) {}
    }
    this.deviceId = device
    this.loadCheckins()
  },
  computed: {
    stackItems: function () { return this.items.slice(0, 3) }
  },
  methods: {
    cardStyle: function (idx) {
      if (idx === 0) {
        if (this.flying) {
          var dir = this.dx >= 0 ? 1 : -1
          return { transform: 'translateY(-90px) scale(.82) rotate(' + (dir * 10) + 'deg)', opacity: 0, zIndex: 3, transition: 'transform 240ms ease, opacity 240ms ease' }
        }
        var rot = this.dx / 20
        return { transform: 'translate(' + this.dx + 'px,' + this.dy + 'px) rotate(' + rot + 'deg)', zIndex: 3, transition: this.dragging ? 'none' : 'transform 220ms cubic-bezier(.2,.8,.2,1)' }
      }
      return { transform: 'translateY(' + (idx * 16) + 'px) scale(' + (1 - idx * 0.05) + ')', zIndex: 3 - idx, transition: 'transform 220ms cubic-bezier(.2,.8,.2,1)' }
    },
    onStart: function (e) {
      var t = e.touches && e.touches[0]
      if (!t) return
      this.startX = t.clientX; this.startY = t.clientY; this.dragging = true; this.dx = 0; this.dy = 0
    },
    onMove: function (e) {
      if (!this.dragging) return
      var t = e.touches && e.touches[0]
      if (!t) return
      this.dx = t.clientX - this.startX
      this.dy = t.clientY - this.startY
    },
    onEnd: function () {
      if (!this.dragging) return
      this.dragging = false
      var threshold = 100
      if (Math.abs(this.dx) < threshold) { this.dx = 0; this.dy = 0; return }
      var self = this
      this.flying = true
      setTimeout(function () {
        var first = self.items.shift()
        if (first) self.items.push(first)
        self.flying = false; self.dx = 0; self.dy = 0
      }, 250)
    },
    goBack: function () { uni.navigateBack() },
    preview: function (item) {
      if (item && item.image) {
        uni.previewImage({ urls: [item.image], current: item.image })
      } else {
        uni.showToast({ title: '这条打卡没有图片', icon: 'none' })
      }
    },
    goScenic: function () { uni.navigateTo({ url: '/pages/scenic/scenic?spotId=18' }) },
    imageUrl: function (path) {
      if (!path) return ''
      if (/^https?:/.test(path)) return path
      if (path.indexOf('/scenic/') === 0) return '/static' + path
      return path
    },
    onRefresh: function () {
      this.refreshing = true
      this.loadCheckins()
    },
    remove: function (item) {
      var self = this
      uni.showModal({
        title: '删除打卡',
        content: '确定删除「' + item.spot_name + '」的打卡记录吗？',
        success: function (res) {
          if (!res.confirm) return
          var header = { 'X-Device-Id': self.deviceId }
          var token = ''
          try { token = uni.getStorageSync('token') || '' } catch (e) {}
          if (token) header.Authorization = 'Bearer ' + token
          uni.request({
            url: BASE_URL + '/tour-experience/checkins/' + item.id,
            method: 'DELETE',
            header: header,
            complete: function () { self.loadCheckins() }
          })
        }
      })
    },
    loadCheckins: function () {
      const self = this
      const header = { 'X-Device-Id': self.deviceId }
      let token = ''
      try { token = uni.getStorageSync('token') || '' } catch (e) {}
      if (token) header.Authorization = 'Bearer ' + token
      uni.request({
        url: BASE_URL + '/tour-experience/checkins',
        header: header,
        success: function (res) {
          const rows = Array.isArray(res.data) ? res.data : []
          if (!rows.length) { self.loadLocal(); return }
          let localCards = {}
          try { localCards = uni.getStorageSync('my_checkin_cards') || {} } catch (e) {}
          self.items = rows.map(function (r) {
            var img = self.imageUrl(r.image_path)
            if (!img && SCENIC_COVERS[r.spot_name]) img = SCENIC_COVERS[r.spot_name]
            var d = new Date(r.time)
            var dayText = isNaN(d.getTime()) ? '' : (d.getMonth() + 1) + '月' + d.getDate() + '日'
            return { id: r.id, spot_name: r.spot_name, time: self.formatTime(r.time), image: img,
              quote: r.quote || '', walk: r.walk || '', duration: r.duration || '', dayText: dayText }
          })
          self.refreshing = false
        },
        fail: function () { self.loadLocal() }
      })
    },
    loadLocal: function () {
      try { this.items = uni.getStorageSync('my_checkins') || [] } catch (e) { this.items = [] }
      this.refreshing = false
    },
    formatTime: function (value) {
      if (!value) return ''
      const d = new Date(value)
      if (isNaN(d.getTime())) return value
      const pad = function (n) { return n < 10 ? '0' + n : '' + n }
      return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes())
    }
  }
}
</script>

<style scoped>
.checkins-page { height: 100vh; background: #f7f4ff; -webkit-font-smoothing: antialiased; padding-bottom: 0 !important; overflow: hidden; display: flex; flex-direction: column; }
.aurora-background { position: fixed; inset: 0; background: linear-gradient(160deg, #f8f5ff 0%, #f1edfe 52%, #edf3fb 100%); z-index: 0; }
.nav { position: relative; z-index: 2; display: flex; align-items: center; padding: 0 24rpx 20rpx; }
.nav-back { width: 72rpx; height: 72rpx; border-radius: 0; display: flex; align-items: center; justify-content: center; background: transparent; box-shadow: none; transition: transform 160ms cubic-bezier(.2,.8,.2,1); }
.nav-back:active { transform: scale(.96); }
.nav-back .iconfont { font-size: 34rpx; color: #3a3150; }
.nav-title { flex: 1; text-align: center; font-size: 34rpx; font-weight: 600; color: #282332; margin-right: 64rpx; }
.main { position: relative; z-index: 1; flex: 1; min-height: 0; padding: 12rpx max(3px, env(safe-area-inset-right, 0px)) 24rpx max(3px, env(safe-area-inset-left, 0px)); box-sizing: border-box; }
.empty { display: flex; flex-direction: column; align-items: center; padding-top: 22vh; }
.empty-badge { width: 140rpx; height: 140rpx; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, rgba(255,255,255,.95), rgba(235,228,255,.9)); box-shadow: inset 0 1rpx 0 #fff, 0 18rpx 40rpx -24rpx rgba(70,50,130,.35); }
.empty-icon { width: 64rpx; height: 64rpx; }
.empty-title { margin-top: 28rpx; font-size: 34rpx; font-weight: 600; color: #282332; text-wrap: balance; }
.empty-hint { margin-top: 14rpx; max-width: 560rpx; font-size: 26rpx; line-height: 1.75; color: #7d7590; text-align: center; }
.empty-cta { margin-top: 36rpx; min-height: 88rpx; padding: 0 48rpx; border-radius: 24rpx; background: linear-gradient(135deg, rgba(255,255,255,.98), rgba(246,242,255,.94)); border: 1rpx solid rgba(130,110,210,.32); box-shadow: inset 0 1rpx 0 #fff, 0 14rpx 30rpx -22rpx rgba(70,50,130,.35); color: #44358f; font-size: 30rpx; line-height: 88rpx; transition: transform 160ms cubic-bezier(.2,.8,.2,1), opacity 160ms; }
.empty-cta:active { transform: scale(.96); }
.list { padding-top: 12rpx; }
.hand-paper { position: fixed; inset: 0; z-index: 0; pointer-events: none; background: repeating-linear-gradient(0deg, rgba(120,100,190,.035) 0 1rpx, transparent 1rpx 6rpx); }
.hand-head { display: flex; align-items: baseline; justify-content: flex-end; margin: 10rpx 32rpx 18rpx; }
.hand-head-count { font-size: 22rpx; color: #a29aad; }
.hand-num { font-size: 30rpx; color: #6547ad; font-weight: 600; margin: 0 4rpx; }
.stack { position: relative; height: 1040rpx; margin: 0 calc(32rpx - 3px); overflow: visible; }
.stack-card { position: absolute; left: 0; right: 0; top: 0; width: auto; box-sizing: border-box; overflow: visible; border-radius: 0; background: transparent; transform-origin: 50% 100%; will-change: transform; }
.hand-card { position: relative; padding: 16rpx 16rpx 0; background: #ffffff; border: 1rpx solid rgba(130,110,210,.14); border-radius: 26rpx; box-shadow: 0 26rpx 54rpx -34rpx rgba(64,44,120,.42); transform: rotate(-.8deg); }
.stack-card:not(.top) .hand-card { transform: rotate(.6deg); }
.hand-tape { position: absolute; top: -14rpx; left: 50%; width: 170rpx; height: 44rpx; margin-left: -85rpx; z-index: 4; transform: rotate(-2.5deg); background: rgba(208,198,240,.72); border-left: 1rpx dashed rgba(120,100,190,.45); border-right: 1rpx dashed rgba(120,100,190,.45); box-shadow: 0 2rpx 6rpx rgba(70,50,130,.12); }
.hand-photo-wrap { position: relative; border-radius: 18rpx; background: #f1ecff; }
.hand-photo { display: block; width: 100%; height: 600rpx; border-radius: 18rpx; overflow: hidden; }
.hand-photo-empty { background: linear-gradient(135deg, #f4efff, #e9f3ff); }
.hand-seal { position: absolute; right: 24rpx; bottom: 24rpx; width: 126rpx; height: 126rpx; border-radius: 50%; border: 3rpx solid rgba(101,71,173,.72); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2rpx; color: #6547ad; transform: rotate(-11deg); background: rgba(251,248,255,.38); }
.hand-seal::after { content: ""; position: absolute; inset: 8rpx; border: 1rpx solid rgba(101,71,173,.45); border-radius: 50%; }
.seal-park { font-size: 16rpx; line-height: 1; letter-spacing: 4rpx; }
.seal-name { font-size: 22rpx; line-height: 1.2; font-weight: 600; letter-spacing: 1rpx; }
.seal-date { font-size: 15rpx; line-height: 1; letter-spacing: 1rpx; opacity: .85; }
.hand-panel { position: relative; padding: 24rpx 18rpx 30rpx; }
.card-quote { display: block; margin: 12rpx 0 0; font-size: 28rpx; line-height: 1.65; color: #5c5370; }
.card-stats { display: flex; align-items: stretch; margin-top: 22rpx; padding-top: 18rpx; border-top: 1rpx dashed rgba(130,110,210,.28); }
.card-stat { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; align-items: center; padding: 0 14rpx; }
.card-stat:first-child { align-items: flex-start; padding-left: 0; }
.card-stat:last-child { padding-right: 0; }
.card-stat + .card-stat { border-left: 1rpx dashed rgba(130,110,210,.24); }
.stat-label { font-size: 20rpx; line-height: 1.3; letter-spacing: 3rpx; color: #a29aad; margin-bottom: 8rpx; }
.stat-value { display: block; max-width: 100%; font-size: 28rpx; line-height: 1.3; color: #3e3652; font-weight: 600; letter-spacing: 1rpx; font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hand-panel .card-del { position: absolute; right: 18rpx; top: 24rpx; color: #a29aad; }
.stack-card.top .hand-card { box-shadow: 0 30rpx 60rpx -34rpx rgba(64,44,120,.5); }
.card { display: flex; flex-direction: column; margin-bottom: 26rpx; border-radius: 28rpx; overflow: hidden; background: #ffffff; border: 1rpx solid rgba(130,110,210,.16); box-shadow: 0 18rpx 40rpx -30rpx rgba(70,50,130,.38); }
.card-cover { width: 100%; height: 420rpx; display: block; background: #f1ecff; }
.card-cover-empty { background: linear-gradient(135deg, #f4efff, #e9f3ff); }
.card-body { display: flex; align-items: center; padding: 24rpx 26rpx; }
.card-info { flex: 1; min-width: 0; }
.card-del { flex: none; padding: 8rpx 12rpx; margin-left: 8rpx; border-radius: 10rpx; font-size: 24rpx; color: #a29aad; }
.card-del:active { background: #f4f0ff; color: #6a5ae0; }


.card-icon { width: 36rpx; height: 36rpx; }
.card-name { display: block; padding-right: 92rpx; font-size: 36rpx; line-height: 1.3; font-weight: 600; color: #282332; }
.card-time { display: block; margin-top: 6rpx; font-size: 25rpx; color: #7d7590; font-variant-numeric: tabular-nums; }

/* 状态栏/导航栏保持白色；中间内容区铺紫色，左上右上圆角 */
.checkins-page.aurora-page { background: #fff !important; }
.checkins-page .aurora-background,
.checkins-page .hand-paper { display: none !important; }
.checkins-page .app-status-bar-shield { background: #fff !important; }
.checkins-page .nav { background: #fff !important; padding-bottom: 18rpx; }
.checkins-page .main {
  margin: 0 6rpx;
  padding: 20rpx 8rpx 24rpx;
  background: #f0eefb !important;
  border-radius: 32rpx 32rpx 0 0;
}
</style>
