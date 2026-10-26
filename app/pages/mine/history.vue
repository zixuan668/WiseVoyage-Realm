<template>
  <view class="page aurora-page history-page">
    <!-- #ifdef APP-PLUS -->
    <view class="app-status-bar-shield" aria-hidden="true"></view>
    <!-- #endif -->
    <view class="aurora-background" aria-hidden="true"></view>
    <view class="nav" :style="{paddingTop:headerTop+'px'}"><text class="nav-back iconfont icon-chevron-left" @tap="goBack" :aria-label="t('返回')" role="button"></text><text class="nav-title">{{ t(selected?'对话记录':'游览记录') }}</text></view>
    <scroll-view v-show="!selected" scroll-y class="main history-list">
      <view v-if="loading" class="empty">{{ t("加载中…") }}</view>
      <view v-else-if="error" class="empty" @tap="loadData">{{ t(error) }}{{ t("，点击重试") }}</view>
      <view v-else-if="list.length===0 && !browseList.length && !browseError" class="empty"><image class="empty-art" src="/static/empty-state.png" mode="widthFix"></image><text>{{ t("暂无游览记录，浏览景点或开始导览后会自动记录") }}</text></view>
      <text v-if="list.length" class="history-section-title">{{ t("导览行程") }}</text>
      <view v-for="s in list" :key="s.session_id" class="card" @tap="openSession(s)">
        <view class="c-info">
          <text class="c-name">{{ t(s.city) ? t(s.city)+' · ' : '' }}{{ t(s.name) }}</text>
          <text class="c-desc">{{ (s.spot_names || []).map(function(n){ return t(n) }).join(' → ') }}</text>
          <text class="c-desc">{{ s.live_status===2 ? t('已结束') : s.live_status===1 ? t('进行中') : t('未开始') }}</text>
          <view v-if="s.live_status===2" class="history-rating-row">
            <view v-if="ratings[s.session_id]" class="history-rating" :aria-label="t('我的评分：{score}分',{score:ratings[s.session_id]})">
              <text>{{ t('我的评分') }}</text>
              <text class="history-rating-stars">{{ '★'.repeat(ratings[s.session_id]) }}{{ '☆'.repeat(5-ratings[s.session_id]) }}</text>
              <text>{{ ratings[s.session_id] }}/5</text>
            </view>
            <text v-else class="history-unrated">{{ t('未评分') }}</text>
            <button class="history-rating-link" @tap.stop="openRating(s)">{{ t(ratings[s.session_id] ? '查看评分' : '去评分') }}</button>
          </view>
          <text class="c-time">{{ t('开始：') }}{{ s.start_time }}</text><text v-if="s.end_time" class="c-time">{{ t('结束：') }}{{ s.end_time }}</text>
        </view>
      </view>
      <text v-if="browseList.length || browseError" class="history-section-title">{{ t("浏览过的景点") }}</text>
      <view v-if="browseError" class="empty" @tap="loadData">{{ t(browseError) }}{{ t("，点击重试") }}</view>
      <view v-for="spot in browseList" :key="'view-'+spot.spot_id" class="card">
        <image v-if="spot.image_path" class="c-img" :src="fixImg(spot.image_path)" mode="aspectFill" />
        <view class="c-info"><text class="c-name">{{ t(spot.city) ? t(spot.city)+' · ' : '' }}{{ t(spot.spot_name) }}</text><text class="c-desc">{{ t(spot.location) }}</text><text class="c-time">{{ t('浏览时间：') }}{{ formatViewTime(spot.viewTime) }}</text></view>
      </view>
    </scroll-view>
    <scroll-view v-if="selected" scroll-y class="main history-detail-scroll">
      <view class="history-detail">
        <text class="c-name">{{ t(selected.name) }}</text>
        <view v-if="messagesLoading" class="empty">{{ t("对话加载中…") }}</view>
        <view v-else-if="messagesError" class="empty" @tap="openSession(selected)">{{ t(messagesError) }}{{ t('，点击重试') }}</view>
        <view v-else-if="!messages.length" class="empty">{{ t("这次导览暂无对话记录") }}</view>
        <view v-for="(m,i) in messages" :key="i" class="history-message"><text class="c-desc">{{ m.role==='user' ? t('我') : t('导游') }} · {{ m.send_time }}</text><text class="message-text">{{ m.message }}</text></view>
      </view>
    </scroll-view>
  </view>
</template>
<script>
import { BASE_URL, assetUrl, isBeijingCity } from '../../common/config.js'
export default {
  data:function(){return{headerTop:48,list:[],ratings:{},ratingOwner:'',browseList:[],browseError:'',loading:false,error:'',selected:null,messages:[],messagesLoading:false,messagesError:''}},
  onLoad:function(){var info=uni.getSystemInfoSync();this.headerTop=Math.max(info.statusBarHeight||0,info.safeArea&&info.safeArea.top||0)+16},
  methods:{
    ratingAccount:function(){var id=uni.getStorageSync('user_id'),name=uni.getStorageSync('username');return id?'id:'+id:name?'name:'+name:''},
    refreshRatings:function(){
      const owner=this.ratingAccount(),ratings={};this.ratingOwner=owner
      if(owner)this.list.forEach(s=>{
        if(s.live_status!==2)return
        try{const saved=uni.getStorageSync('tour_rating:v1:'+encodeURIComponent(owner)+':'+s.session_id);if(saved&&Number.isInteger(saved.score)&&saved.score>=1&&saved.score<=5)ratings[s.session_id]=saved.score}catch(_){}
      })
      this.ratings=ratings
    },
    openRating:function(s){
      if(this.ratingAccount()!==this.ratingOwner){this.loadData();return}
      if(s.live_status===2)uni.navigateTo({url:'/pages/tour-summary/tour-summary?sessionId='+s.session_id})
    },
    fixImg:function(value){return assetUrl(value)},
    formatViewTime:function(value){var date=new Date(value);return isNaN(date.getTime())?value:date.toLocaleString()},
    closeSession:function(){this._messageVersion=(this._messageVersion||0)+1;this._messageRequest?.abort();this.selected=null},
    goBack:function(){if(this.selected){this.closeSession();return}uni.navigateBack()},
    openSession:function(s){
      this._messageRequest?.abort();const version=this._messageVersion=(this._messageVersion||0)+1
      const token=uni.getStorageSync('token'),owner=this.ratingAccount()
      const current=()=>this._messageVersion===version&&this.selected?.session_id===s.session_id&&uni.getStorageSync('token')===token&&this.ratingAccount()===owner
      this.selected=s;this.messages=[];this.messagesLoading=true;this.messagesError=''
      this._messageRequest=uni.request({url:BASE_URL+'/tour-session/my-history/'+s.session_id+'/messages',timeout:15000,header:{Authorization:'Bearer '+token},
        success:r=>{if(!current())return;if(r.statusCode===200&&r.data.success)this.messages=r.data.data.messages||[];else this.messagesError=r.statusCode===401?'请重新登录':'对话加载失败'},
        fail:()=>{if(current())this.messagesError='对话加载失败'},complete:()=>{if(current())this.messagesLoading=false}})
    },
    loadData:function(){
      this.closeSession();this.loading=true;this.error='';this.browseError='';this.list=[];this.ratings={};this.ratingOwner=this.ratingAccount();this.browseList=[]
      const token=uni.getStorageSync('token'),owner=uni.getStorageSync('user_id')
      const read=url=>new Promise((resolve,reject)=>uni.request({url:BASE_URL+url,header:{Authorization:'Bearer '+token},success:r=>{if(r.statusCode===200&&r.data.success)resolve(r.data.data);else reject(new Error(r.statusCode===401?'请重新登录':'记录加载失败'))},fail:()=>reject(new Error('记录加载失败'))}))
      const isCurrent=()=>uni.getStorageSync('token')===token&&uni.getStorageSync('user_id')===owner
      const tours=read('/tour-session/my-history').then(data=>{if(isCurrent()){this.list=(data.session_list||[]).filter(function(x){return isBeijingCity(x.city)});this.refreshRatings()}}).catch(error=>{if(isCurrent())this.error=error.message})
      const views=read('/spot-favorites/history').then(data=>{if(isCurrent())this.browseList=(data.spot_list||[]).filter(function(sp){return isBeijingCity(sp.city)})}).catch(error=>{if(isCurrent())this.browseError=error.message})
      return Promise.all([tours,views]).finally(()=>{if(isCurrent())this.loading=false})
    },
  },
  onShow:function(){this.loadData()},
  onBackPress:function(){if(this.selected){this.closeSession();return true}},
  onUnload:function(){this.closeSession()},
}
</script>
<style scoped>
.history-rating-row{display:flex;align-items:center;justify-content:space-between;gap:12rpx;flex-wrap:wrap;margin-top:12rpx}
.history-rating{display:flex;align-items:center;gap:12rpx;flex-wrap:wrap;font-size:24rpx;color:var(--ng-text)}
.history-rating-stars{color:#a66b0c;font-size:30rpx;letter-spacing:2rpx;line-height:1.4}
.history-unrated{font-size:24rpx;color:var(--ng-secondary)}
.history-rating-link{margin:0;padding:4rpx 16rpx;font-size:24rpx;line-height:1.8;border-radius:12rpx;background:var(--ng-raised,#f0edf8);color:var(--ng-accent-text,#5141ad)}.history-rating-link::after{border:0}
.page{height:100vh;display:flex;flex-direction:column;background-color:var(--ng-surface);position:relative;overflow:hidden}
.ink-bg{position:absolute;inset:0;pointer-events:none;z-index:0}.ink-mt{position:absolute;left:0;right:0;background:var(--ng-night);border-radius:55% 75% 0 0}.ink-mt-1{bottom:20%;height:220rpx;opacity:.04;transform:scaleX(1.3)}.ink-mt-2{bottom:25%;height:160rpx;opacity:.025;transform:scaleX(1.5) translateX(-8%)}
.page-bg{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0}
.nav{position:relative;z-index:1;display:flex;flex-shrink:0;align-items:center;padding:50rpx 24rpx 16rpx}
.nav-back{font-size:56rpx;color:var(--ng-text);padding-right:20rpx;line-height:1}
.nav-title{flex:1;font-size:34rpx;font-weight:600;color:var(--ng-text);letter-spacing:0;font-family:var(--app-font-family);text-align:center}
.main{position:relative;z-index:1;padding:0 24rpx;height:0;min-height:0;flex:1;box-sizing:border-box;width:100%}
.empty{text-align:center;padding:100rpx;color:var(--ng-secondary);font-size:28rpx}
.card{display:flex;align-items:center;gap:14rpx;padding:16rpx 18rpx;margin-bottom:14rpx;background:var(--ng-surface);border:1rpx solid var(--ng-border);border-radius:18rpx}
.c-img{width:88rpx;height:88rpx;border-radius:14rpx;flex-shrink:0}.c-img-df{width:88rpx;height:88rpx;border-radius:14rpx;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.1);font-size:36rpx;flex-shrink:0}
.c-info{flex:1;min-width:0}.c-name{font-size:28rpx;font-weight:600;color:var(--ng-text);display:block}.c-desc{font-size:22rpx;color:var(--ng-secondary);display:block;margin-top:4rpx}.c-time{font-size:20rpx;color:var(--ng-secondary);margin-top:4rpx;display:block}
.history-detail{padding:24rpx;background:var(--ng-surface);border-radius:18rpx;margin-bottom:30rpx}.history-close{padding:18rpx 0;color:var(--ng-secondary)}.history-message{padding:20rpx 0;border-bottom:1rpx solid var(--ng-border)}.message-text{display:block;font-size:28rpx;line-height:1.7;margin-top:8rpx}
.empty-art{width:280rpx;margin:0 auto 16rpx;opacity:.95}.history-section-title{display:block;padding:24rpx 0 16rpx;font-size:30rpx;font-weight:600;color:var(--ng-text)}
.page.history-page{padding-bottom:env(safe-area-inset-bottom)!important;background:transparent}
</style>
