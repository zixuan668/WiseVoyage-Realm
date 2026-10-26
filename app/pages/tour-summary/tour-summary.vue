<template>
  <view class="page aurora-page">
    <view class="aurora-background" aria-hidden="true"><view class="aurora-wave aurora-wave-one"></view><view class="aurora-wave aurora-wave-two"></view><view class="aurora-shine"></view></view>
    <view class="ink-bg"><view class="ink-mt ink-mt-1"></view><view class="ink-mt ink-mt-2"></view></view>

    <view class="nav" :style="{paddingTop:statusH+'px'}">
      <view class="nav-back" @tap="goBack" role="button" :aria-label="t('返回')"><text class="nav-back-icon iconfont icon-chevron-left" aria-hidden="true"></text></view>
      <text class="nav-title">{{ t("导览记录") }}</text>
      <view class="nav-side"></view>
    </view>

    <view v-if="loading" class="state-tip"><text>{{ t("加载中...") }}</text></view>
    <view v-else-if="!sessionData" class="state-tip">
      <image class="empty-art" src="/static/empty-state.png" mode="widthFix"></image>
      <text class="state-title">{{ t("无法读取本次导览记录") }}</text>
      <view class="state-btn" @tap="goHome">{{ t("返回首页") }}</view>
    </view>

    <scroll-view scroll-y class="main" v-else>
      <view v-if="tourEnded" class="rating-card">
        <text class="rating-title">{{ t('这次导览体验怎么样？') }}</text>
        <text class="rating-hint">{{ t('点击星星，为本次导览打分') }}</text>
        <view class="rating-stars" role="group" :aria-label="t('导览评分')">
          <button v-for="star in 5" :key="star" class="rating-star" :class="{selected:star<=ratingScore}" :aria-label="t('{score}星',{score:star})" :aria-pressed="star===ratingScore" @tap="ratingScore=star"><text class="iconfont icon-star" aria-hidden="true"></text></button>
        </view>
        <text class="rating-description">{{ ratingScore ? t(ratingLabels[ratingScore-1]) : t('请选择1至5星') }}</text>
        <button class="rating-save" :disabled="!ratingScore||ratingScore===savedRating" @tap="saveRating">{{ t(savedRating ? (ratingScore===savedRating ? '评分已保存' : '更新评分') : '保存评分') }}</button>
      </view>
      <!-- 数据统计 -->
      <view class="stats-row">
        <view class="stat-card">
          <text class="stat-num">{{ spotTimeline.length }}</text>
          <text class="stat-label">{{ t("景点游览") }}</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ questionCount }}</text>
          <text class="stat-label">{{ t("提问互动") }}</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ messageCount }}</text>
          <text class="stat-label">{{ t("对话总数") }}</text>
        </view>
      </view>

      <!-- 游览时间轴 -->
      <view class="section">
        <view class="section-head route-heading"><text>{{ t("游览路线") }}</text></view>
        <view class="timeline">
          <view v-for="(s, i) in spotTimeline" :key="i" class="tl-item" :class="{last: i === spotTimeline.length - 1}">
            <view class="tl-marker">
              <view class="tl-dot" :class="{visited: i <= currentSpotIdx}">
                <text class="tl-num">{{ i + 1 }}</text>
              </view>
              <view class="tl-line" v-if="i < spotTimeline.length - 1"></view>
            </view>
            <view class="tl-body">
              <view class="tl-card">
                <image v-if="s.image_path" :src="fixImg(s.image_path)" class="tl-img" mode="aspectFill"></image>
                <view v-else class="tl-img-df"></view>
                <view class="tl-info">
                  <text class="tl-name">{{ t(s.spot_name) }}</text>
                  <text class="tl-cat" v-if="s.visit_duration">{{ t('约') }}{{ s.visit_duration }}{{ t('分钟') }}</text>
                  <text class="tl-desc" v-if="s.description">{{ t(s.description).substring(0, 50) }}...</text>
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- 知识亮点 -->
      <view class="section" v-if="highlights.length > 0">
        <view class="section-head"><view class="sh-dot"></view><text>{{ t("导览知识亮点") }}</text></view>
        <view class="highlight-list">
          <view v-for="(h, i) in highlights" :key="i" class="hl-card">
            <view class="hl-q" v-if="h.question">
              <text class="hl-q-icon">Q</text>
              <text class="hl-q-text">{{ h.question }}</text>
            </view>
            <view class="hl-a">
              <text class="hl-a-icon">A</text>
              <text class="hl-a-text">{{ h.answer }}</text>
            </view>
            <view class="hl-sentiment" v-if="h.sentiment">

              <text class="hl-mood">{{ h.sentiment }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- AI总结 -->
      <view class="section" v-if="aiSummary">
        <view class="section-head"><view class="sh-dot"></view><text>{{ t("AI 导览总结") }}</text></view>
        <view class="ai-summary-card">

          <text class="as-text">{{ aiSummary }}</text>
        </view>
      </view>

      <view style="height:140rpx"></view>
    </scroll-view>

    <!-- 加载 -->
    <view class="loading-wrap" v-if="loading">
      <view class="loading-pulse"><view class="lp-ring"></view><view class="lp-ring2"></view></view>
      <text class="loading-text">{{ t("生成游览回顾…") }}</text>
    </view>

  </view>
</template>

<script>
import { BASE_URL, assetUrl, isBeijingCity } from '../../common/config.js'

function request(options) {
  return new Promise(function(resolve, reject) {
    var url = options.url
    if (url.indexOf('http') !== 0) url = BASE_URL + url
    var token = uni.getStorageSync('token') || ''
    var header = { 'Content-Type': 'application/json' }
    if (token) header['Authorization'] = 'Bearer ' + token
    var match = options.url.match(/\/tour-session\/(?:start|end|live-info|detail|analyze|quiz|next-spot)\/(\d+)/) || options.url.match(/[?&]session_id=(\d+)/)
    var sid = options.data && options.data.sessionId || (match && match[1])
    var access = sid && uni.getStorageSync('xingyun-tour-' + sid)
    if (access) header['X-Tour-Access'] = access
    uni.request({
      url: url, method: options.method || 'GET',
      data: options.data || {}, header: header,
      timeout: options.timeout || 20000,
      success: function(res) {
        if (res.statusCode === 200) resolve({ data: res.data })
        else reject(new Error('HTTP ' + res.statusCode))
      },
      fail: reject
    })
  })
}

export default {
  data: function() {
    return {
      statusH: 20, loading: true, sid: 0,
      sessionData: null, conversation: [], spots: [],
      currentSpotIdx: 0, aiSummary: '',
      ratingScore:0,savedRating:0,ratingOwner:'',ratingLabels:['很不满意','不太满意','一般','满意','非常满意'],
    }
  },
  computed: {
    tourEnded:function(){
      var data=this.sessionData;if(!data)return false
      // live-info returns live_status at the root; retain older nested responses.
      var state=data.live_status??data.status?.live_status
      return state!=null?Number(state)===2:!!(data.end_time||data.status?.end_time)
    },
    spotTimeline: function() {
      return this.spots
    },
    questionCount: function() {
      return this.conversation.filter(function(m) { return m.role === 'user' }).length
    },
    messageCount: function() {
      return this.conversation.length
    },
    highlights: function() {
      var guideMsgs = this.conversation.filter(function(m) { return m.role === 'guide' && m.message && m.message.length > 40 })
      var paired = []
      for (var i = 0; i < guideMsgs.length && paired.length < 5; i++) {
        var msg = guideMsgs[i]
        var qIdx = -1
        for (var j = this.conversation.indexOf(msg) - 1; j >= 0; j--) {
          if (this.conversation[j].role === 'user') { qIdx = j; break }
        }
        paired.push({
          question: qIdx >= 0 ? this.conversation[qIdx].message : '',
          answer: msg.message.length > 120 ? msg.message.substring(0, 120) + '...' : msg.message,
          sentiment: msg.emotion_label || '',
        })
      }
      return paired
    },
  },
  methods: {
    ratingAccount:function(){var id=uni.getStorageSync('user_id'),name=uni.getStorageSync('username');return id?'id:'+id:name?'name:'+name:''},
    ratingKey:function(){return 'tour_rating:v1:'+encodeURIComponent(this.ratingOwner)+':'+this.sid},
    loadRating:function(){
      this.ratingScore=0;this.savedRating=0
      if(!this.ratingOwner||!this.sid)return
      try{var saved=uni.getStorageSync(this.ratingKey());if(saved&&Number.isInteger(saved.score)&&saved.score>=1&&saved.score<=5){this.ratingScore=saved.score;this.savedRating=saved.score}}catch(_){}
    },
    saveRating:function(){
      if(!this.ratingOwner||this.ratingAccount()!==this.ratingOwner){uni.showToast({title:this.t('账号已变化，请重新打开导览记录'),icon:'none'});return}
      if(!this.tourEnded||!Number.isInteger(this.ratingScore)||this.ratingScore<1||this.ratingScore>5||this.ratingScore===this.savedRating)return
      try{
        uni.setStorageSync(this.ratingKey(),{score:this.ratingScore,savedAt:Date.now()})
        this.savedRating=this.ratingScore
        uni.showToast({title:this.t('评分已保存'),icon:'success'})
      }catch(_){uni.showToast({title:this.t('评分保存失败，请重试'),icon:'none'})}
    },
    catLabel: function (c) { var m = { historical: '历史', natural: '自然', cultural: '文化' }; return this.t(m[c] || c) },
    fixImg: function(u) { if (!u) return ''; return assetUrl(u) },
    goHome: function() {
      uni.reLaunch({ url: '/pages/tabs/tabs?tab=tour' })
    },
    goBack:function(){
      const pages=getCurrentPages(),previous=pages[pages.length-2]
      if(previous&&previous.route==='pages/mine/history'){uni.navigateBack();return}
      this.goHome()
    },
    loadData: function() {
      var self = this
      self.loading = true
      request({ url: '/tour-session/live-info/' + self.sid }).then(function(res) {
        var d = res.data && res.data.data
        if (!d) { self.loading = false; return }
        self.sessionData = d
        self.conversation = d.conversation || []
        var prefs = {}
        try { prefs = JSON.parse(d.visitor_preferences || '{}') } catch(e) {}
        var spotIds = prefs.spot_ids || []
        var st = d.status || {}
        self.currentSpotIdx = st.current_spot_index || 0
        if (spotIds.length) {
          request({ url: '/tour-session/spots' }).then(function(sr) {
            var allSpots = (sr.data && sr.data.data && sr.data.data.spot_list ? sr.data.data.spot_list : []).filter(function(sp){return isBeijingCity(sp.city)})
            self.spots = spotIds.map(function(id) { return allSpots.find(function(s) { return s.spot_id === id }) }).filter(Boolean)
            self.loading = false
            self.tryAISummary()
          }).catch(function() { self.loading = false })
        } else {
          self.loading = false
        }
      }).catch(function() {
        self.loading = false
        uni.showToast({ title: '加载失败', icon: 'none' })
      })
    },
    tryAISummary: function() {
      var self = this
      if (self.conversation.length < 2) return
      request({ url: '/tour-session/analyze/' + self.sid, method: 'POST', timeout: 30000 }).then(function(res) {
        var d = res.data && res.data.data
        if (d && d.summary) self.aiSummary = d.summary
      }).catch(function() {})
    },
  },
  onLoad: function(opts) {
    var s = uni.getSystemInfoSync()
    this.statusH = (s.statusBarHeight || 20) + 6
    this.sid = Number(opts.sessionId || 0)
    this.ratingOwner=this.ratingAccount();this.loadRating()
    if (!this.sid) { this.loading = false; uni.showToast({ title: '参数无效', icon: 'none' }); return }
    this.loadData()
  },
}
</script>

<style scoped>
.rating-card{margin:12rpx 16rpx 20rpx;padding:30rpx 24rpx;border:1rpx solid var(--ng-border);border-radius:24rpx;background:var(--ng-surface);display:flex;flex-direction:column;align-items:center;gap:14rpx}
.rating-title{font-size:32rpx;font-weight:700;color:var(--ng-text)}
.rating-hint{font-size:24rpx;line-height:1.5;color:var(--ng-secondary);text-align:center}
.rating-stars{display:flex;gap:8rpx;justify-content:center;width:100%}
.rating-star{margin:0;padding:0;width:92rpx;height:92rpx;line-height:92rpx;font-size:64rpx;color:var(--ng-secondary);background:transparent;flex-shrink:0}.rating-star::after,.rating-save::after{border:0}
.rating-star.selected{color:#b77916}
.rating-description{min-height:38rpx;font-size:26rpx;color:var(--ng-text)}
.rating-save{margin:4rpx 0;padding:0 40rpx;line-height:2.6;font-size:28rpx;border-radius:18rpx;color:#fff;background:#5545b7}.rating-save[disabled]{color:var(--ng-secondary);background:var(--ng-raised,#f0edf8)}
.page{height:100vh;display:flex;flex-direction:column;background:var(--ng-surface);position:relative;overflow:hidden}
.page.aurora-page{padding-bottom:0!important;background:transparent!important}
.ink-bg{position:absolute;inset:0;pointer-events:none;z-index:0}
.ink-mt{position:absolute;left:0;right:0;background:var(--ng-night);border-radius:55% 75% 0 0}
.ink-mt-1{bottom:18%;height:200rpx;opacity:.04;transform:scaleX(1.3)}
.ink-mt-2{bottom:22%;height:140rpx;opacity:.025;transform:scaleX(1.5) translateX(-8%)}

.nav{position:relative;z-index:1;display:flex;align-items:center;padding:4rpx 20rpx;gap:12rpx}
.nav-title{flex:1;font-size:36rpx;font-weight:600;color:var(--ng-text);text-align:center}
.nav-back{width:132rpx;height:96rpx;display:flex;align-items:center;justify-content:flex-start;padding-left:10rpx;box-sizing:border-box;flex-shrink:0;background:transparent}
.nav-back-icon{font-size:56rpx;line-height:1;color:var(--ng-secondary)}
.nav-side{width:132rpx;height:96rpx;flex-shrink:0}

.main{position:relative;z-index:1;flex:1;min-height:0}

/* 统计 */
.stats-row{display:flex;gap:12rpx;padding:8rpx 16rpx}
.stat-card{flex:1;display:flex;flex-direction:column;align-items:center;padding:16rpx 0;background:var(--ng-surface);border:1rpx solid var(--ng-border);border-radius:14rpx}
.stat-num{font-size:44rpx;font-weight:700;color:var(--ng-text)}
.stat-label{font-size:22rpx;color:var(--ng-secondary);margin-top:4rpx}

/* 通用 section */
.section{padding:16rpx 16rpx 0}
.section-head{display:flex;align-items:center;gap:10rpx;margin-bottom:12rpx}
.route-heading{justify-content:center;text-align:center}
.sh-dot{width:8rpx;height:8rpx;border-radius:50%;background:rgba(99,102,241,0.25)}
.section-head text{font-size:30rpx;font-weight:600;color:var(--ng-text)}

/* 时间轴 */
.timeline{padding-left:4rpx}
.tl-item{display:flex;gap:16rpx;padding-bottom:8rpx}
.tl-marker{display:flex;flex-direction:column;align-items:center;flex-shrink:0}
.tl-dot{width:36rpx;height:36rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--ng-surface);border:2rpx solid var(--ng-border);z-index:1}
.tl-dot.visited{border-color:rgba(99,102,241,0.25);background:rgba(99,102,241,0.15)}
.tl-check{font-size:20rpx;color:var(--ng-secondary);font-weight:700}
.tl-num{font-size:20rpx;color:var(--ng-secondary)}
.tl-line{width:2rpx;flex:1;background:var(--ng-border);margin-top:4rpx;min-height:40rpx}
.tl-body{flex:1;padding-bottom:16rpx}
.tl-card{display:flex;align-items:center;gap:12rpx;padding:12rpx;background:var(--ng-surface);border:1rpx solid var(--ng-border);border-radius:14rpx}
.tl-img{width:88rpx;height:88rpx;border-radius:10rpx;flex-shrink:0}
.tl-img-df{width:88rpx;height:88rpx;border-radius:10rpx;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.08);font-size:40rpx;flex-shrink:0}
.tl-info{flex:1;min-width:0}
.tl-name{font-size:28rpx;font-weight:600;color:var(--ng-text);display:block}
.tl-cat{font-size:20rpx;color:var(--ng-secondary);display:block;margin-top:4rpx}
.tl-desc{font-size:22rpx;color:var(--ng-secondary);display:block;margin-top:6rpx;line-height:1.5}

/* 知识亮点 */
.highlight-list{display:flex;flex-direction:column;gap:12rpx}
.hl-card{padding:16rpx;background:var(--ng-surface);border:1rpx solid var(--ng-border);border-radius:14rpx}
.hl-q{display:flex;align-items:flex-start;gap:10rpx;margin-bottom:10rpx}
.hl-q-icon{width:32rpx;height:32rpx;border-radius:8rpx;background:rgba(99,102,241,0.15);display:flex;align-items:center;justify-content:center;font-size:20rpx;color:var(--ng-text);flex-shrink:0}
.hl-q-text{font-size:24rpx;color:var(--ng-text);line-height:1.5;flex:1}
.hl-a{display:flex;align-items:flex-start;gap:10rpx}
.hl-a-icon{width:32rpx;height:32rpx;border-radius:8rpx;background:rgba(59,91,255,.12);display:flex;align-items:center;justify-content:center;font-size:20rpx;color:var(--ng-secondary);flex-shrink:0}
.hl-a-text{font-size:24rpx;color:var(--ng-secondary);line-height:1.7;flex:1}
.hl-sentiment{display:flex;align-items:center;gap:6rpx;margin-top:8rpx}
.hl-emoji{font-size:24rpx}
.hl-mood{font-size:20rpx;color:var(--ng-secondary)}

/* AI总结 */
.ai-summary-card{display:flex;gap:12rpx;padding:16rpx;background:rgba(99,102,241,0.06);border:1rpx solid rgba(99,102,241,0.2);border-radius:14rpx}
.as-icon{font-size:32rpx;flex-shrink:0}
.as-text{font-size:26rpx;color:var(--ng-text);line-height:1.7;flex:1}


/* 加载 */
.loading-wrap{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center}
.loading-pulse{position:relative;width:80rpx;height:80rpx;margin-bottom:20rpx}
.lp-ring{position:absolute;inset:0;border-radius:50%;border:4rpx solid rgba(99,102,241,0.15);border-top-color:rgba(99,102,241,0.25);animation:spin 1s linear infinite}
.lp-ring2{position:absolute;inset:12rpx;border-radius:50%;border:3rpx solid rgba(59,91,255,.1);border-top-color:rgba(59,91,255,.4);animation:spin 1.5s linear infinite reverse}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-text{font-size:26rpx;color:var(--ng-secondary)}

/* 底部操作 */
.state-tip{padding:120rpx 40rpx;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:var(--ng-secondary);font-size:28rpx}
.state-tip .empty-art{width:320rpx;margin-bottom:24rpx}
.state-title{font-size:28rpx;color:var(--ng-text);margin-bottom:28rpx}
.state-btn{padding:18rpx 48rpx;border-radius:40rpx;background:#4f46e5;color:#fff;font-size:28rpx}
</style>
