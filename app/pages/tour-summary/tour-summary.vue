<template>
  <view class="page eval-page">
    <view class="aurora-background" aria-hidden="true"></view>
    <view class="nav" :style="{paddingTop:statusH+'px'}">
      <view class="nav-back app-back-btn" @tap="goBack" role="button" aria-label="返回"><view class="app-back-icon" aria-hidden="true"></view></view>
      <text class="nav-title">结束评价</text>
    </view>
    <scroll-view scroll-y class="main" v-if="!submitted">
      <text class="heading">这次游览怎么样？</text>
      <view class="expressions">
        <view v-for="(item,i) in emotions" :key="item" class="expr" :class="{on:quick===i}" @tap="pick(i)">
          <view class="expr-icon" :class="'expr-icon-' + i"></view>
          <text class="expr-label">{{ item }}</text>
        </view>
      </view>
      <template v-if="quick!==undefined">
        <text class="section">哪些地方让你有这种感觉？</text>
        <view class="tags">
          <view v-for="tag in visibleTags" :key="tag" class="tag" :class="{on:tags.includes(tag)}" @tap="toggleTag(tag)"><text>{{ tag }}</text></view>
        </view>
        <view class="recommend">
          <text class="section">你愿意推荐这次游览吗？</text>
          <text class="recommend-value">{{ recommendation }} / 10</text>
          <slider :value="recommendation" :min="0" :max="10" :step="1" activeColor="#6a5ae0" backgroundColor="rgba(120,100,190,.18)" block-size="22" @change="recommendation=$event.detail.value" />
        </view>
      </template>
      <view class="bottom-space"></view>
    </scroll-view>
    <view v-else class="done"><text class="done-icon">✓</text><text class="done-title">评价已保存</text><text class="done-hint">谢谢你的反馈</text></view>
    <view class="foot" v-if="!submitted"><button class="cta" :disabled="quick===undefined" @tap="submit">{{ submitting ? '正在提交…' : '提交评价' }}</button></view>
    <view class="foot" v-else><button class="cta" @tap="backHome">返回首页</button></view>
  </view>
</template>
<script>
import { BASE_URL } from '../../common/config.js'
export default {
  data: function () {
    return { statusH: 20, sid: 0, quick: undefined, tags: [], recommendation: 8, submitted: false, submitting: false,
      emotions: ['不太满意', '一般', '很满意'],
      positive: ['讲解清楚', '路线方便', '风景优美', '内容有趣'],
      negative: ['定位不准', '讲解需改进', '步行较累'] }
  },
  computed: {
    visibleTags: function () {
      if (this.quick === 2) return this.positive
      if (this.quick === 0) return this.negative
      return this.positive.concat(this.negative)
    }
  },
  onLoad: function (opts) {
    const s = uni.getSystemInfoSync(); this.statusH = (s.statusBarHeight || 20) + 6
    this.sid = Number((opts && opts.sid) || 0)
  },
  methods: {
    goBack: function () {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.reLaunch({ url: '/pages/tabs/tabs' })
    },
    pick: function (i) { this.quick = i; this.tags = [] },
    toggleTag: function (tag) { this.tags = this.tags.includes(tag) ? this.tags.filter(t => t !== tag) : this.tags.concat(tag) },
    submit: function () {
      if (this.quick === undefined || this.submitting) return
      this.submitting = true
      let device = ''
      try { device = uni.getStorageSync('device_id') || '' } catch (e) {}
      if (!device) {
        device = 'dev-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
        try { uni.setStorageSync('device_id', device) } catch (e) {}
      }
      try {
        const key = 'tour_eval:v1:' + device + ':' + this.sid
        uni.setStorageSync(key, { quick: this.quick, tags: this.tags, recommendation: this.recommendation, savedAt: Date.now() })
      } catch (e) {}
      const self = this
      const header = { 'X-Device-Id': device }
      let token = ''
      try { token = uni.getStorageSync('token') || '' } catch (e) {}
      if (token) header.Authorization = 'Bearer ' + token
      uni.request({
        url: BASE_URL + '/tour-experience/reviews/app',
        method: 'POST',
        header: header,
        data: { session_id: this.sid, quick: this.quick, tags: this.tags, recommendation: this.recommendation },
        complete: function () { self.submitting = false; self.submitted = true }
      })
    },
    backHome: function () { uni.reLaunch({ url: '/pages/tabs/tabs' }) }
  }
}
</script>
<style scoped>
.eval-page { min-height: 100vh; background: #f7f4ff; }
.aurora-background { position: fixed; inset: 0; z-index: 0; background: linear-gradient(160deg, #f8f5ff 0%, #f1edfe 52%, #edf3fb 100%); }
.nav { position: relative; z-index: 2; display: flex; align-items: center; padding: 0 24rpx 20rpx; }
.nav-back { width: 72rpx; height: 72rpx; display: flex; align-items: center; justify-content: center; background: transparent; }
.back-icon { width: 40rpx; height: 40rpx; background-color: #282332; -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M19 12H5M11 6l-6 6 6 6'/%3E%3C/svg%3E") center / contain no-repeat; mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M19 12H5M11 6l-6 6 6 6'/%3E%3C/svg%3E") center / contain no-repeat; }
.nav-title { flex: 1; text-align: center; font-size: 34rpx; font-weight: 600; color: #282332; margin-right: 64rpx; }
.main { position: relative; z-index: 1; height: calc(100vh - 150rpx); padding: 12rpx 28rpx 0; box-sizing: border-box; }
.heading { display: block; margin: 18rpx 0 26rpx; font-size: 40rpx; font-weight: 600; color: #282332; }
.expressions { display: flex; gap: 16rpx; }
.expr { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 12rpx; padding: 24rpx 10rpx; border-radius: 22rpx; background: linear-gradient(135deg, rgba(255,255,255,.96), rgba(249,246,255,.92)); border: 1rpx solid rgba(130,110,210,.18); box-shadow: 0 14rpx 30rpx -26rpx rgba(70,50,130,.35); transition: transform 160ms cubic-bezier(.2,.8,.2,1), border-color 160ms, background-color 160ms; }
.expr.on { border-color: #8b78e6; background: #f1ecff; }
.expr:active { transform: scale(.97); }
.expr-icon{width:64rpx;height:64rpx;background-color:#6f6685;-webkit-mask:var(--icon) center/contain no-repeat;mask:var(--icon) center/contain no-repeat;transition:background-color 160ms}
.expr.on .expr-icon{background-color:#6a5ae0}
.expr-icon-0{--icon:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='9'/%3E%3Cpath d='M8.6 10h.01M15.4 10h.01M8.6 16c1-1.5 2.2-2.2 3.4-2.2s2.4.7 3.4 2.2'/%3E%3C/svg%3E")}
.expr-icon-1{--icon:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='9'/%3E%3Cpath d='M8.6 10h.01M15.4 10h.01M8.5 15.5h7'/%3E%3C/svg%3E")}
.expr-icon-2{--icon:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='9'/%3E%3Cpath d='M8.6 10h.01M15.4 10h.01M8.5 14.5c1 1.7 2.3 2.5 3.5 2.5s2.5-.8 3.5-2.5'/%3E%3C/svg%3E")}
.expr-label { font-size: 26rpx; color: #3a3150; }
.section { display: block; margin: 34rpx 0 16rpx; font-size: 30rpx; font-weight: 600; color: #282332; }
.tags { display: flex; flex-wrap: wrap; gap: 16rpx; }
.tag { padding: 16rpx 26rpx; border-radius: 18rpx; background: linear-gradient(135deg, rgba(255,255,255,.96), rgba(248,246,255,.92)); border: 1rpx solid rgba(130,110,210,.22); font-size: 27rpx; color: #3a3150; transition: transform 140ms, background-color 140ms, border-color 140ms; }
.tag.on { border-color: #8b78e6; background: #f0ebff; color: #44358f; }
.tag:active { transform: scale(.96); }
.recommend { margin-top: 34rpx; }
.recommend-value { display: block; margin: 4rpx 0 10rpx; font-size: 28rpx; color: #6f6685; }
.bottom-space { height: 40rpx; }
.foot { position: fixed; left: 0; right: 0; bottom: 0; z-index: 3; padding: 16rpx 28rpx calc(16rpx + env(safe-area-inset-bottom)); background: linear-gradient(180deg, rgba(247,244,255,0), rgba(247,244,255,.96) 40%); }
.cta { width: 100%; min-height: 92rpx; line-height: 92rpx; margin: 0; border-radius: 24rpx; background: linear-gradient(135deg, rgba(255,255,255,.98), rgba(246,242,255,.94)); border: 1rpx solid rgba(139,120,230,.4); box-shadow: inset 0 1rpx 0 #fff, 0 12rpx 28rpx -24rpx rgba(70,50,130,.4); color: #4a3aa8; font-size: 31rpx; font-weight: 600; }
.cta:active { transform: scale(.97); }
.cta[disabled] { opacity: .45; }
.done { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; padding-top: 28vh; }
.done-icon { width: 120rpx; height: 120rpx; line-height: 120rpx; text-align: center; border-radius: 50%; background: #f1ecff; color: #6a5ae0; font-size: 52rpx; }
.done-title { margin-top: 26rpx; font-size: 36rpx; font-weight: 600; color: #282332; }
.done-hint { margin-top: 12rpx; font-size: 27rpx; color: #7d7590; }
</style>
