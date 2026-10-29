<template>
  <view class="page">

    <view class="tour-gradient" aria-hidden="true"></view>

    <NocturneConfirm v-if="showEndConfirm" plain :title="t('结束导览')" :content="t('确定要结束本次导览吗？')" :cancel-label="t('取消')" :confirm-label="t('确定')" @cancel="showEndConfirm=false" @confirm="endTour" />
    <!-- 导航栏 -->
    <view class="nav" :style="{paddingTop:statusH+'px'}">
      <view class="nav-back" @tap="goBack" role="button" :aria-label="t('返回')"><text class="iconfont icon-chevron-left" aria-hidden="true"></text></view>
    <!-- 游览进度时间轴 -->
    <view class="tour-progress nav-progress" v-if="spotCards.length">
      <scroll-view scroll-x enable-flex scroll-with-animation class="tp-track" :class="{'fade-left':fadeLeft,'fade-right':fadeRight}" :scroll-left="progressScrollLeft" :show-scrollbar="false" @scroll="onProgressScroll" @touchend="onProgressRelease">
        <view class="tp-nodes" :class="{'tp-centered': spotCards.length <= 3}">
          <view v-for="(s, idx) in spotCards" :key="s.spot_id" :id="'tpn-'+idx" class="tp-node" :class="{done:idx<spotIdx, active:idx===progressActive}" @tap="selectProgressSpot(idx)">
            <view class="tp-dot"></view>
            <text class="tp-label">{{ t(s.spot_name) }}</text>
          </view>
        </view>
      </scroll-view>
    </view>
      <view v-if="spotCards.length > 3" class="tp-more-slot" aria-hidden="true"><text v-if="fadeRight" class="tp-more">···</text></view>
      <view class="nav-end" @tap="confirmEnd" role="button" :aria-label="t('结束导览')"><text class="iconfont icon-close" aria-hidden="true"></text></view>
    </view>

    <view v-if="showRouteInfo" class="tour-route-mask" @tap="showRouteInfo=false"><view class="tour-route-sheet" @tap.stop><view class="tour-route-heading"><text>{{ t('剩余游览路线') }}</text><button @tap="showRouteInfo=false" :aria-label="t('关闭')"><text class="iconfont icon-close" aria-hidden="true"></text></button></view><scroll-view scroll-y class="tour-route-body"><RouteOverview v-if="routeOverview" :overview="routeOverview" :current-id="liveCurrentId" /><text v-else>{{ t('路线详情暂时无法加载') }}</text></scroll-view></view></view>
    <TourRouteRepair v-if="repairOpen" ref="routeRepair" :sid="sid" :current-name="spotCards.find(s=>s.spot_id===liveCurrentId)?.spot_name||spotName" :remaining-spots="repairRemainingSpots" :initial="repairInitial" :prompt="repairPrompt" @close="repairOpen=false" @applied="routeRepaired" @refresh="refresh(true)" />
    <!-- 数字导游 -->
    <view class="guide-stage" :style="!tourVisible || leavingTour || repairOpen || showRouteInfo ? 'visibility:hidden' : ''">
      <view v-if="spotCards.length" class="tp-stats stage-progress">
        <text class="tp-stat" v-if="routeOverview&&remainingDuration==null">{{ t('路线用时待确认') }}</text>
        <text class="tp-stat" v-else-if="remainingDuration > 0">{{ t('预计剩余约 {minutes} 分钟', {minutes:remainingDuration}) }}</text>
        <text class="tp-stat done" v-else>{{ t('路线游览完毕') }}</text>
      </view>
      <text v-if="guideDisplayName" class="stage-guide-name">{{ guideDisplayName }}</text>
      <!-- #ifdef APP-PLUS -->
      <tour-xingyun v-if="guideProvider==='xingyun'" :payload="xingyunPayload" @state="onXingyunState" />
      <!-- #endif -->
      <!-- 知识卡片弹出 -->
      <view class="know-card" v-if="knowCard.visible" @tap="dismissKnowCard">
        <view class="kc-inner">
          <text class="kc-tag">{{ t('景点知识') }}</text>
          <text class="kc-text">{{ knowCard.text }}</text>
          <image v-if="knowCard.image" :src="knowCard.image" class="kc-img" mode="aspectFill"></image>
        </view>
      </view>
      <template v-if="tourVisible && !leavingTour && !(appXingyun && guideProvider==='xingyun' && (xingyunConnected || xingyunActive))">
      <video v-if="videoUrl" key="speech-video" id="guide-speech-video" :muted="false" :loop="false" :src="videoUrl" class="avatar-video" object-fit="contain" :controls="true" :autoplay="true" @play="speaking=true;speechPaused=false;revealAnswer()" @pause="speaking=false" @ended="speaking=false" @error="videoError"></video>
      <view v-else class="guide-img-df"><text class="guide-df-name">{{ guideName || t('数字导游') }}</text><text v-if="guideProvider!=='xingyun'" class="avatar-notice">{{ t('形象未配置') }}</text></view>
      </template>
      <view v-if="avatarConnecting" class="stage-status" :class="{on:speaking}">
        <view class="avatar-loading" role="status" :aria-label="t('连接中…')"><view v-for="dot in 3" :key="dot" class="avatar-loading-dot"></view></view>
      </view>
    </view>

    <!-- #ifdef APP-PLUS -->
    <view v-if="guideProvider==='xingyun' && xingyunFailed && avatarMessage" class="stage-footer"><text class="avatar-runtime-status">{{ t(avatarMessage) }}</text></view>
    <view v-if="guideProvider==='xingyun'&&xingyunFailed" class="xingyun-retry" role="button" @tap="connectXingyun"><text>{{ t('重新连接数字人') }}</text></view>
    <!-- #endif -->
    <!-- #ifndef APP-PLUS -->
    <button v-if="guideProvider==='xingyun'" class="xingyun-open" @tap="openXingyun">{{ t('打开数字人导览') }}</button>
    <!-- #endif -->
    <!-- 景点切换卡片 -->
    <view class="spot-switch" v-if="spotCards.length">
      <view class="ss-arrow" @tap="prevSpot" role="button" :aria-label="t('上一个景点')"><text class="iconfont icon-chevron-left" aria-hidden="true"></text></view>
      <view class="ss-card">
        <image v-if="currentSpot.image_path||currentSpot.route_cover_image" :src="fixImg(currentSpot.image_path||currentSpot.route_cover_image)" class="ss-img" mode="aspectFill"></image>
        <view v-else class="ss-img-df"></view>
        <view class="ss-info">
          <view class="ss-top">
            <text class="ss-cat">{{ spotIdx+1 }}/{{ spotCards.length }}</text><text class="ss-name">{{ t(currentSpot.spot_name) }}</text>
            <text class="ss-cat" v-if="!currentSpot.image_path && currentSpot.route_cover_image">{{ t('路线示意图') }}</text>
          </view>
        </view>
      </view>
      <view class="ss-arrow" @tap="nextSpot" role="button" :aria-label="t('下一个景点')"><text class="iconfont icon-chevron-right" aria-hidden="true"></text></view>
    </view>

    <!-- 对话区 -->
    <scroll-view :scroll-y="!voicePressing" class="chat-area" :scroll-into-view="lastMsgId">
      <view class="chat-content">
      <view v-if="!msgs.length && !loading" class="chat-empty"></view>
      <view v-if="chatTranslationFailed" class="chat-translation" @tap="localizeChat()">{{ tourLanguage==='en'?'Translation unavailable. Tap to retry.':'翻译失败，点击重试' }}</view>
      <view v-for="(m,i) in msgs" :key="i" :id="'msg-'+i" class="msg-row" :class="m.role==='guide'?'msg-l':'msg-r'">
        <view class="msg-bubble" :class="m.role">
          <text class="msg-text">{{ m.message }}</text>
          <view v-if="m.role==='guide'" class="msg-voice-btn" :class="{muted:!isMessagePlaying(i)}" :aria-label="t(isMessagePlaying(i) ? '暂停语音播报' : '继续播放')" @tap.stop="toggleVoiceMute(m,i)">
            <text v-if="!isMessagePlaying(i)" class="playback-glyph iconfont icon-play" aria-hidden="true"></text>
            <text v-else class="playback-glyph iconfont icon-pause" aria-hidden="true"></text>
          </view>
          <text class="msg-time">{{ fmtTime(m.send_time) }}</text>
        </view>
      </view>
      <view v-if="loading" class="loading-tip" role="status" :aria-label="t('AI导游思考中...')">
        <view v-for="dot in 3" :key="dot" class="avatar-loading-dot" aria-hidden="true"></view>
      </view>
      <view id="bottom" style="height:20rpx;"></view>
      </view>
    </scroll-view>

    <!-- 底部输入区 -->
    <view class="bottom-bar" :class="{'keyboard-open':keyboardHeight>0}" :style="keyboardHeight>0?{paddingBottom:keyboardHeight+'px'}:{}">
      <view class="input-row">
        <view class="voice-btn" :class="{rec:voiceMode}" @tap="toggleVoiceMode">
          <text class="iconfont" :class="voiceMode ? 'icon-liaotian' : 'icon-yuyin'"></text>
        </view>
        <textarea v-if="!voiceMode" v-model="text" class="msg-input" :focus="textareaFocus" :placeholder="t('输入你想了解的问题...')" :adjust-position="false" @touchstart.prevent="onInputTouchStart" @input="onInputValue" @focus="onInputFocus" @keyboardheightchange="onKeyboardHeight" @linechange="onInputLineChange" @blur="onInputBlur" :cursor-spacing="0" confirm-type="send" @confirm="onConfirm" :show-confirm-bar="false" :style="inputHeight?{height:inputHeight+'px'}:{}" :maxlength="2000" :disabled="loading||transcribing"></textarea>
        <view v-else class="voice-hold-btn" :class="{pressing:voicePressing}" @touchstart.stop.prevent="startRecord" @touchmove.stop.prevent="blockTouch" @touchend.stop.prevent="stopRecord" @touchcancel.stop="cancelRecord" @contextmenu.prevent="">
          <text>{{ t(transcribing ? '正在识别…' : loading ? '正在回答…' : voicePressing ? '松开发送' : '按住说话') }}</text>
        </view>
        <view v-if="!voiceMode" class="send-btn" @tap="onSend" :class="{disabled:!text||loading||transcribing}">{{ t('发送') }}</view>
      </view>
    </view>
  </view>
</template>

<script>
import NocturneConfirm from '../../components/NocturneConfirm.vue'
import RouteOverview from '../../components/RouteOverview.vue'
import TourRouteRepair from '../../components/TourRouteRepair.vue'
import { isRouteChange, repairDefaults } from '../../common/route-planning.js'
import TourXingyun from '../../components/tour-xingyun.vue'
import { prepareNativeGuideAudio } from '../../common/avatar-audio.js'
import { BASE_URL, assetUrl, isBeijingCity } from '../../common/config.js'
import { appendTourChatMessage } from '../../common/tour-chat-log.js'
import { localizeChatMessages, warmChatTranslations, getChatTranslationCache } from '../../common/chat-language.js'
import { LANGUAGE_STORAGE_KEY, translateTour } from '../../common/tour-language.js'
import { wgs84ToGcj02, gcj02ToWgs84 } from '../../../shared/coordinates.js'

function request(options) {
  var task;var promise=new Promise(function(resolve, reject) {
    var url = options.url
    if (url.indexOf('http') !== 0) url = BASE_URL + url
    var token = uni.getStorageSync('token') || ''
    var header = { 'Content-Type': 'application/json' }
    if (token) header['Authorization'] = 'Bearer ' + token
    var match = options.url.match(/\/tour-session\/(?:start|end|live-info|detail|analyze|quiz|next-spot)\/(\d+)/) || options.url.match(/[?&]session_id=(\d+)/)
    var sid = options.data && options.data.sessionId || (match && match[1])
    var access = sid && uni.getStorageSync('xingyun-tour-' + sid)
    if (access) header['X-Tour-Access'] = access
    task=uni.request({
      url: url, method: options.method || 'GET',
      data: options.data || {}, header: header,
      timeout: options.timeout || 20000,
      success: function(res) {
        if (res.statusCode === 200) resolve({ data: res.data })
        else if (res.statusCode === 401) { uni.reLaunch({url:'/pages/auth/auth'});reject(new Error('登录已过期，请重新进入导览')) }
        else reject(new Error(res.data && (res.data.detail || res.data.message) || '服务请求失败（HTTP ' + res.statusCode + '）'))
      },
      fail: reject
    })
  });promise.abort=function(){if(task)task.abort()};return promise
}
var api = {
  getLiveInfo: function(sid) { return request({ url: '/tour-session/live-info/' + sid }) },
  sendMessage: function(sid, message, avatarMode, currentSpotId, nextSpotId, language) { return request({ url: '/tour-session/chat', method: 'PUT', timeout: 90000, data: { sessionId: sid, message: message, avatarMode: avatarMode, currentSpotId: currentSpotId, nextSpotId: nextSpotId, language: language === 'en' ? 'en' : 'zh' } }) },
  aiChatRecommend: function(msg) { return request({ url: '/tour-session/ai-chat-recommend?message=' + encodeURIComponent(msg||''), method: 'POST' }) },
  endSession: function(sid) { return request({ url: '/tour-session/end/' + sid, method: 'PUT' }) },
  checkNearby: function(lat, lng, sid, target) { return request({ url: '/tour-session/check-nearby?latitude='+lat+'&longitude='+lng+'&session_id='+sid+'&target_spot_id='+target, method: 'POST', timeout: 8000 }) },
}

export default {
  components: {NocturneConfirm,TourXingyun,RouteOverview,TourRouteRepair,
  },
  data: function() {
    return {

      keyboardHeight:0,inputHeight:0,textareaFocus:false,showEndConfirm: false,tourVisible:true,leavingTour:false,endingTour:false,appXingyun:false,xingyunPayload:{},xingyunConnected:false,xingyunFailed:false,xingyunActive:false,
      chatTranslating:false,chatTranslationFailed:false,
      showRouteInfo:false,repairOpen:false,repairOpening:false,repairPrompt:'',repairInitial:{},routeOverview:null,liveCurrentId:0,
      sid: 0, msgs: [], spotCards: [], spotIdx: 0, progressActive: -1, progressScrollLeft: 0, fadeLeft: false, fadeRight: false, progressTrackW: 0, progressContentW: 0, progressNodeW: 100,
      guideName: '', guideNameEn: '', guideSourceVideo:'', guideProvider:'', statusH: 20,
      speaking: false, loading: false, text: '', recording: false, voicePressing: false, transcribing: false, voiceMode: false,
      voiceMuted: false, speechPaused: false, activeSpeechIndex: -1, speechStarting: false,
      avatarMode:'audio',avatarMessage:'语音导览',videoUrl:'',avatarCapability:null,guideId:0,
      lastMsgId: 'bottom', _voiceManager: null,
      quick: ['这里有什么历史故事？','最佳拍照点在哪里？','附近有哪些服务设施？','请介绍景点特色','下一站推荐去哪里？'],
      mediaExpanded: false,
      gpsTracking: false, mapExpanded: false, userLat: 0, userLng: 0,
      distanceStatus: '正在获取当前位置…',
      nearestDistance: 0, nearestSpotName: '', nearestSpotIdx: -1, gpsTimer: null,
      knowCard: { visible: false, text: '', image: '' }, _knowTimer: null,
    }
  },
  watch: {
    tourLanguage:function(){this.stopPlayback();this.localizeChat()},
    spotIdx: function() { if(this.gpsTracking) { this.distanceStatus='正在更新目标景点距离…'; this.checkNearby() } this.progressActive=this.spotIdx },
    'spotCards.length': function() { this._progressPos=0; this.progressScrollLeft=0; this.fadeLeft=false; this.fadeRight=false; this.progressContentW=0; this.progressActive=this.spotIdx; this.measureProgress() },
  },
  computed: {
    avatarConnecting: function() { return this.guideProvider==='xingyun' && !this.xingyunConnected && !this.xingyunFailed && this.tourVisible && !this.leavingTour },
    languageBusy: function() { return this.loading || this.recording || this.voicePressing || this.transcribing },
    guideDisplayName: function() { if (this.tourLanguage === 'en' && this.guideNameEn) return this.guideNameEn; return this.guideName.replace(/^默认星云(?:数字人)?导游(?:数字人)?\s*/, '').trim() || this.guideName },
    spotName: function() {
      var c = this.spotCards[this.spotIdx]
      return c ? c.spot_name : '景区导览中'
    },
    currentSpot: function() {
      return this.spotCards[this.spotIdx] || {}
    },
    visitedDuration: function() {
      var total = 0
      for (var i = 0; i < this.spotIdx && i < this.spotCards.length; i++) {
        total += this.spotCards[i].visit_duration ||10
      }
      return total
    },
    repairRemainingSpots:function(){var i=this.spotCards.findIndex(s=>s.spot_id===this.liveCurrentId);return this.spotCards.slice(i<0?this.spotIdx+1:i+1)},
    remainingDuration: function() {
      if(this.routeOverview)return this.routeOverview.total_minutes
      var total = 0
      for (var i = this.spotIdx + 1; i < this.spotCards.length; i++) {
        total += this.spotCards[i].visit_duration ||10
      }
      return total
    },
    hasSpotCoords: function() {
      return this.spotCards.some(function(s) { return s.latitude && s.longitude && s.latitude != 0 })
    },
    spotCenterLat: function() {
      var spots = this.spotCards.filter(function(s) { return s.latitude && s.latitude != 0 })
      if (!spots.length) return 39.999
      return spots.reduce(function(a, s) { return a + wgs84ToGcj02(Number(s.latitude), Number(s.longitude))[0] }, 0) / spots.length
    },
    spotCenterLng: function() {
      var spots = this.spotCards.filter(function(s) { return s.longitude && s.longitude != 0 })
      if (!spots.length) return 116.397
      return spots.reduce(function(a, s) { return a + wgs84ToGcj02(Number(s.latitude), Number(s.longitude))[1] }, 0) / spots.length
    },
    mapMarkers: function() {
      var markers = []
      for (var i = 0; i < this.spotCards.length; i++) {
        var s = this.spotCards[i]
        if (!s.latitude || !s.longitude || s.latitude == 0) continue
        var isActive = i === this.spotIdx
        var point = wgs84ToGcj02(Number(s.latitude), Number(s.longitude))
        markers.push({
          id: s.spot_id || i,
          latitude: point[0], longitude: point[1],
          width: isActive ? 24 : 16, height: isActive ? 24 : 16,
          callout: {
            content: s.spot_name,
            color: isActive ? '#4f46e5' : '#999',
            fontSize: 12, borderRadius: 8,
            padding: 6, display: 'ALWAYS',
            bgColor: isActive ? 'rgba(99,102,241,0.15)' : 'rgba(0,0,0,0.5)',
          },
        })
      }
      return markers
    },
  },
  methods: {
    chatTranslationOwner:function(){const id=uni.getStorageSync('user_id'),name=uni.getStorageSync('username');return id?'id:'+id:name?'name:'+name:'guest'},
    warmChat:function(){
      const owner=this.chatTranslationOwner(),cache=getChatTranslationCache(owner)
      if(!this.msgs.length)return Promise.resolve()
      return warmChatTranslations({lists:[this.msgs],field:'message',cache,isCurrent:()=>this.chatTranslationOwner()===owner&&!this.leavingTour,
        translate:async(texts,target)=>{const res=await request({url:'/tour-session/translate-texts',method:'POST',timeout:45000,data:{texts,target}});return res.data?.data?.translations}}).catch(()=>{})
    },
    localizeChat:async function(){
      const version=this._translationVersion=(this._translationVersion||0)+1
      const target=this.tourLanguage==='en'?'en':'zh',list=this.msgs,owner=uni.getStorageSync('token')
      const current=()=>this._translationVersion===version&&this.tourLanguage===target&&this.msgs===list&&uni.getStorageSync('token')===owner&&!this.leavingTour
      this.chatTranslating=true;this.chatTranslationFailed=false
      this._messageTranslations=getChatTranslationCache(this.chatTranslationOwner())
      try{await localizeChatMessages({lists:[list],field:'message',target,cache:this._messageTranslations,isCurrent:current,
        translate:async texts=>{const res=await request({url:'/tour-session/translate-texts',method:'POST',timeout:45000,data:{texts,target}});return res.data?.data?.translations}})}
      catch(_){if(current())this.chatTranslationFailed=true}
      finally{if(this._translationVersion===version)this.chatTranslating=false}
    },
    // 键盘高度只改底部间距（margin），不做 transform / pageScrollTo：
    // 输入框在布局上位于键盘上方，顶部标题和整页不会被系统往上推；
    // 中间消息区 flex:1 + 自身滚动，页面整体保持 100vh 不滚动。
    // 系统可能在 keyboardheightchange 之前就决定上移页面，所以聚焦时先按上次键盘高度
    // （首次按屏高估算）预留空间，拿到真实高度后再校正。
    kbEstimate:function(){
      var h=0
      try{h=Number(uni.getStorageSync('app-keyboard-height'))||0}catch(e){h=0}
      if(!h){var s=uni.getSystemInfoSync();h=Math.round((s.windowHeight||s.screenHeight||700)*0.42)}
      return h
    },
    onInputTouchStart:function(){
      // 显式置焦点保证一次点击就弹键盘；内边距把输入行抬到预估键盘高度（防整页平移），
      // 输入栏背景填满下方区域，键盘升起时盖住它，不会露出页面底部。
      // 键盘被系统关掉后 focus 可能仍为 true，要先复位再置位才能再次弹出。
      if(this.textareaFocus){var self=this;this.textareaFocus=false;this.$nextTick(function(){self.textareaFocus=true})}
      else this.textareaFocus=true
      if(this.keyboardHeight>0)return
      this._kbSeen=false
      this.keyboardHeight=this.kbEstimate()
      var self=this;clearTimeout(this._kbFocusTimer)
      this._kbFocusTimer=setTimeout(function(){if(!self._kbSeen)self.keyboardHeight=0},1600)
    },
    onInputFocus:function(){
      if(this.keyboardHeight>0)return
      this.keyboardHeight=this.kbEstimate()
    },
    onKeyboardHeight(e){
      var h=Math.max(0,Number(e.detail?.height)||0)
      if(h>0){this._kbSeen=true;clearTimeout(this._kbFocusTimer);try{uni.setStorageSync('app-keyboard-height',h)}catch(_){}}
      else this.textareaFocus=false
      this.keyboardHeight=h
    },
    onInputBlur:function(){
      var self=this;this.textareaFocus=false
      clearTimeout(this._kbFocusTimer)
      setTimeout(function(){self.keyboardHeight=0},150)
    },
    // 清空内容时立即还原单行高度，避免输入框一直停在多行高度。
    onInputValue:function(event){
      var value=event&&event.detail&&event.detail.value
      if((value===undefined||value===null||String(value).length===0)&&this.inputHeight)this.inputHeight=0
    },
    // textarea 自动增高：1 行为基础高度，超过 4 行后固定 4 行高并在框内滚动。
    onInputLineChange:function(event){
      var lines=Math.max(1,Math.min(4,Number(event&&event.detail&&event.detail.lineCount)||1))
      var rpx=lines>1?(lines*39+40):0
      this.inputHeight=rpx?(uni.upx2px?uni.upx2px(rpx):Math.round(rpx/2)):0
    },
    connectXingyun:async function(){
      if(this._xingyunClosePromise)await this._xingyunClosePromise
      if(!this.tourVisible||this.leavingTour||this.endingTour)return
      // #ifdef APP-PLUS
      if(this.xingyunActive||!this.guideId||!this.sid)return
      this.xingyunActive=true;this.xingyunFailed=false;this.avatarMessage='正在连接数字人…'
      var self=this,version=this._xingyunVersion=(this._xingyunVersion||0)+1
      request({url:'/xingyun/config/'+this.guideId}).then(function(res){
        if(version!==self._xingyunVersion)return
        if(!res.data.configured)throw new Error('所选星云数字人未启用或未绑定')
        self._xingyunGateway=BASE_URL+'/xingyun/session/'+self.guideId+'?tour_id='+self.sid+'&language='+(self.tourLanguage||'zh')
        self.xingyunPayload={id:Date.now(),command:'connect',text:'',gateway:self._xingyunGateway,sdkUrl:res.data.sdkUrl,accessToken:uni.getStorageSync('xingyun-tour-'+self.sid),token:uni.getStorageSync('token')}
      }).catch(function(error){if(version!==self._xingyunVersion)return;self.xingyunActive=false;self.xingyunFailed=true;self.avatarMessage=error.message||'星云连接失败，请重试'})
      // #endif
    },
    onXingyunState:function(event){
      if(event.state==='closed'){if(this._xingyunClosed&&event.id===this._xingyunCloseId){this._xingyunClosed();this._xingyunClosed=null}return}
      if(event.gateway!==this._xingyunGateway)return
      if(event.state==='connected'){
        this.xingyunConnected=true;this.xingyunFailed=false;this.avatarMessage='';this.xingyunActive=true
        var pending=this._xingyunPending;if(pending&&this._xingyunGateway){this._xingyunPending='';this.xingyunPayload=Object.assign({},this.xingyunPayload,{id:Date.now(),gateway:this._xingyunGateway,command:'speak',text:pending})}
      }
      else if(event.state==='playing'){if(this.speechPaused||this.voiceMuted)return;this.speechStarting=false;if(!this._xingyunStartedAt)this._xingyunStartedAt=Date.now();this.speaking=true;this.speechPaused=false;this.avatarMessage='星云数字人正在讲解';this.revealAnswer()}
      else if(event.state==='ended'){this.speechStarting=false;this.speaking=false;this._xingyunStartedAt=0;this.avatarMessage=''}
      else if(event.state==='error'){this.speechStarting=false;this.speaking=false;this.xingyunConnected=false;this.xingyunActive=false;this.xingyunFailed=true;this.avatarMessage=event.message||'星云连接失败，请重试'}
      else if(event.message)this.avatarMessage=event.message
    },
    isMessagePlaying:function(index){return this.activeSpeechIndex===index&&!this.voiceMuted&&!this.speechPaused&&(this.speaking||this.speechStarting)},
    toggleVoiceMute:function(m,index){
      var text=(m&&m.message)||this._lastSpoken||''
      if(index!==this.activeSpeechIndex){this.stopPlayback();this.speakAnswer(text,index);return}
      if(this.voiceMuted||this.speechPaused){this.resumeSpeech(text);return}
      if(this.speaking){this.pauseSpeech(text);return}
      if(text)this.speakAnswer(text)
    },
    pauseSpeech:function(text){
      if(text)this._lastSpoken=text
      this.voiceMuted=true;this.speechPaused=true;this.speaking=false
      if(this.xingyunActive&&this._xingyunStartedAt){
        this._xingyunOffset=Math.min((this._xingyunFullText||'').length,(this._xingyunOffset||0)+Math.max(0,(Date.now()-this._xingyunStartedAt)/1000*4))
        this._xingyunStartedAt=0
      }
      if(this._audio){try{if(this._audio.pause)this._audio.pause()}catch(e){}}
      else if(this.videoUrl){try{uni.createVideoContext('guide-speech-video',this).pause()}catch(e){}}
      if(this.xingyunActive&&!this._audio){this.xingyunPayload=Object.assign({},this.xingyunPayload,{command:'stop',text:'',id:Date.now()})}
    },
    resumeSpeech:function(text){
      var pending=text||this._lastSpoken||''
      this.voiceMuted=false;this.speechPaused=false
      if(this._audio){try{this._audio.play();this.speaking=true;return}catch(e){}}
      if(this.videoUrl){try{uni.createVideoContext('guide-speech-video',this).play();this.speaking=true;return}catch(e){}}
      if(this._xingyunFullText){
        var remaining=this._xingyunFullText.slice(Math.floor(this._xingyunOffset||0))
        if(remaining)this.speakXingyun(remaining,true)
        else{this.speaking=false;this.avatarMessage='';this._xingyunPending=''}
        return
      }
      if(pending)this.speakAnswer(pending)
    },
    revealAnswer:function(){
      if(!this._answerPending)return
      this._answerPending=false
      if(this._revealTimer){clearTimeout(this._revealTimer);this._revealTimer=null}
      this.loading=false;this.lastMsgId='bottom'
      this.refresh()
    },
    speakAnswer:function(text,index){if(!text)return;this.activeSpeechIndex=typeof index==='number'?index:this.msgs.length;this.voiceMuted=false;this.speechPaused=false;this.speechStarting=true;this._lastSpoken=text;this.speakXingyun(text)},
    speakXingyun:function(text,resume){if(this.voiceMuted)return;if(!text)return;if(!resume){this._lastSpoken=text;this._xingyunFullText=text;this._xingyunOffset=0}this._xingyunStartedAt=0;if(!this._xingyunGateway||!this.xingyunActive){this._xingyunPending=text;if(this._xingyunGateway)this.connectXingyun();return}this.xingyunPayload=Object.assign({},this.xingyunPayload,{id:Date.now(),gateway:this._xingyunGateway,command:'speak',text:text})},
    closeXingyun:function(){
      this._xingyunVersion=(this._xingyunVersion||0)+1;this._xingyunGateway='';this._xingyunPending=''
      if(this._xingyunClosePromise)return this._xingyunClosePromise
      var self=this,id=this._xingyunCloseId=(this._xingyunCloseId||0)+1
      this.xingyunActive=false;this.xingyunConnected=false
      var closed=this.appXingyun&&this.guideProvider==='xingyun'?new Promise(function(resolve){self._xingyunClosed=resolve}):Promise.resolve()
      this._xingyunClosePromise=closed.then(function(){self._xingyunClosePromise=null})
      this.xingyunPayload={command:'close',id:id}
      return this._xingyunClosePromise
    },
    stopPlayback:function(){if(this.xingyunActive)this.xingyunPayload=Object.assign({},this.xingyunPayload,{command:'stop',text:'',id:Date.now()});this._xingyunPending='';if(this._audio){this._audio.destroy();this._audio=null}if(this._avatarTimer){clearTimeout(this._avatarTimer);this._avatarTimer=null}this._playbackVersion=(this._playbackVersion||0)+1;this.activeSpeechIndex=-1;this.speechStarting=false;this.voiceMuted=false;this.speaking=false;this.speechPaused=false;this.videoUrl='';this._xingyunStartedAt=0;this._xingyunOffset=0;this._xingyunFullText=''},
    updateAvatarMessage:function(){if(this.avatarMode==='audio'){this.avatarMessage='语音导览';return}var capability=this.avatarCapability&&this.avatarCapability[this.avatarMode];this.avatarMessage=capability?capability.message:'正在查询数字人服务状态'},
    videoError:function(){this.speaking=false;this.videoUrl='';this.avatarMessage='视频播放失败，请检查视频地址与网络';this.revealAnswer()},
    playAudio:function(value){
      prepareNativeGuideAudio(typeof plus==='undefined'?null:plus)
      if(this._audio)this._audio.destroy()
      var self=this,a=this._audio=uni.createInnerAudioContext()
      a.sessionCategory='playback'
      a.onPlay(function(){if(self._audio!==a)return;if(self.voiceMuted||self.speechPaused){a.pause();return}self._xingyunStartedAt=Date.now();self.speaking=true;self.revealAnswer()})
      function finish(){if(self._audio!==a)return;self.speaking=false;a.destroy();self._audio=null}
      a.onEnded(finish)
      a.onError(function(error){if(self._audio!==a)return;console.warn('[guide-audio] player failed',error.errCode,error.errMsg);finish();self.revealAnswer();uni.showToast({title:'语音播放失败',icon:'none'})})
      a.src=assetUrl(value)
      if(!self.voiceMuted&&!self.speechPaused)a.play()
    },
    startSpeechVideo:function(value){var self=this;if(self._audio){self._audio.destroy();self._audio=null}self.videoUrl=assetUrl(value);self.$nextTick(function(){if(self.videoUrl)uni.createVideoContext('guide-speech-video',self).play()})},
    pollAvatar:function(job,version){var self=this;if(version!==self._playbackVersion)return;request({url:'/avatar/jobs/'+job.job_id+'?token='+encodeURIComponent(job.access_token)}).then(function(r){if(version!==self._playbackVersion)return;var d=r.data&&r.data.data;if(!d)throw new Error('任务状态缺失');if(d.status==='completed'){self.startSpeechVideo(d.video_url);self.avatarMessage='讲解视频已生成，若未自动播放请点播放';return}if(d.status==='failed'){self.avatarMessage=d.message||'视频生成失败';self.revealAnswer();return}self.avatarMessage=d.status==='processing'?'正在生成口型视频…':'视频生成排队中';self._avatarTimer=setTimeout(function(){self.pollAvatar(job,version)},1500)}).catch(function(){if(version===self._playbackVersion)self.avatarMessage='获取视频状态失败，请重新提问'})},
    fixImg:function(u){if(!u)return'';return assetUrl(u)},
    fmtTime: function(t) {
      if (!t) return ''
      const date = new Date(typeof t === 'string' ? t.replace(/^(\d{4}-\d{2}-\d{2}) /, '$1T') : t)
      if (isNaN(date.getTime())) return ''
      return String(date.getHours()).padStart(2, '0') + ':' + String(date.getMinutes()).padStart(2, '0')
    },
    prevSpot: function(){ if(this.spotCards.length>1){ this.spotIdx=(this.spotIdx-1+this.spotCards.length)%this.spotCards.length; this.mediaExpanded=false }},
    nextSpot: function(){ if(this.spotCards.length>1){ this.spotIdx=(this.spotIdx+1)%this.spotCards.length; this.mediaExpanded=false }},
    jumpSpot: function(i){ if(i===this.spotIdx||this.loading) return; this.spotIdx=i; this.mediaExpanded=false },
    selectProgressSpot:function(i){
      if(uni.vibrateShort)uni.vibrateShort({type:'light'})
      if(i===this.progressActive){this.progressActive=-1;return}
      this.progressActive=i
      if(i!==this.spotIdx){this.spotIdx=i;this.mediaExpanded=false}
      this.$nextTick(this.snapToActive)
    },
    measureProgress:function(){
      var info=uni.getSystemInfoSync()
      var screenW=info.windowWidth||375
      var rpx=screenW/750
      // 3 个以内等分居中不滚动；超过 3 个时一屏三列，另留 40rpx 放“···”提示
      var few=this.spotCards.length<=3
      this.progressNodeW=few?Math.max(1,(screenW-176*rpx)/Math.max(1,this.spotCards.length)):174*rpx
      this.progressTrackW=Math.max(0,screenW-(few?176:228)*rpx)
      this.progressContentW=few?this.progressTrackW:this.spotCards.length*this.progressNodeW
      this.updateProgressFade()
    },
    updateProgressFade:function(){
      var max=Math.max(0,this.progressContentW-this.progressTrackW)
      var scrollable=max>4
      var pos=this._progressPos||0
      var left=scrollable&&pos>4
      var right=scrollable&&pos<max-4
      if(left!==this.fadeLeft)this.fadeLeft=left
      if(right!==this.fadeRight)this.fadeRight=right
    },
    onProgressScroll:function(e){
      this._progressPos=e.detail.scrollLeft||0
      if(this.progressScrollLeft!==this._progressPos)this.progressScrollLeft=this._progressPos
      if(!this.progressContentW||!this.progressTrackW)this.measureProgress()
      this.updateProgressFade()
    },
    blockTouch:function(){},
    onProgressRelease:function(){
      this._progressReleaseTimer&&clearTimeout(this._progressReleaseTimer)
      this._progressReleaseTimer=setTimeout(this.snapToActive,220)
    },
    snapToActive:function(){
      var max=Math.max(0,this.progressContentW-this.progressTrackW)
      var per=Math.max(1,this.progressNodeW)
      var target=this.spotIdx*per-(this.progressTrackW-per)/2
      this.progressScrollLeft=Math.max(0,Math.min(max,target))
      var self=this
      setTimeout(function(){self.updateProgressFade()},380)
    },
    send: function(msg) {
      var self = this; var t = (msg||'').trim()
      if (!t || self.loading||self.repairOpen||self.repairOpening) return
      if(isRouteChange(t)){self.text='';self.openRepair(t);return}
      if(!self.guideId){uni.showToast({title:'导游信息加载中，请稍后再试',icon:'none'});return}
      self.stopPlayback();self.text = ''; self.inputHeight = 0; self.loading = true
      self._answerPending=false;if(self._revealTimer){clearTimeout(self._revealTimer);self._revealTimer=null}
      var playbackVersion=self._playbackVersion,turn=self._turnVersion=(self._turnVersion||0)+1
      var currentSpot = self.spotCards[self.spotIdx]
      var nextSpot = self.spotCards[self.spotIdx+1]
      self.msgs.push({ role:'user', message:t, send_time: new Date().toISOString() })
      appendTourChatMessage('user', t)
      self.lastMsgId = 'bottom'
      // AI推荐
      api.aiChatRecommend(t).then(function(r) {
        var d = r.data
        if (d && d.success && d.data && d.data.spot_ids && d.data.spot_ids.length) {
          uni.setStorageSync('ai_spot_ids', JSON.stringify(d.data.spot_ids))
        }
      }).catch(function() {})
      // 发送消息（附带景点上下文）
      Promise.resolve(self._capabilityPromise).then(function(){if(turn!==self._turnVersion)return null;return self._chatTask=api.sendMessage(self.sid, t, self.avatarMode, currentSpot&&currentSpot.spot_id, nextSpot?nextSpot.spot_id:null,self.tourLanguage)}).then(function(res) {
        if(turn!==self._turnVersion||!res)return
        var d = res.data
        if (d && d.success) {
          appendTourChatMessage('ai', d.data && d.data.message)
          // 先出声音、再出文字：文字在语音真正开始播放时一起出现，避免“先看到字、等语音”
          self._answerPending=true
          if(self._revealTimer)clearTimeout(self._revealTimer)
          self._revealTimer=setTimeout(function(){self.revealAnswer()},3500)
          // TTS自动播报
          if(playbackVersion===self._playbackVersion){
            // #ifdef APP-PLUS
            if(self.guideProvider==='xingyun')self.speakAnswer(d.data&&d.data.message,d.data&&d.data.ttsAudioUrl)
            // #endif
            self.activeSpeechIndex=self.msgs.length;self.voiceMuted=false;self.speechPaused=false
            var job=d.data&&d.data.avatarJob
            if(job&&job.job_id){self.pollAvatar(job,playbackVersion)}
            else{if(job)self.avatarMessage=job.message;if(d.data&&d.data.ttsAudioUrl)self.playAudio(d.data.ttsAudioUrl)}
            if(self.voiceMuted||self.speechPaused)setTimeout(function(){self.revealAnswer()},300)
            else if(!job&&!(d.data&&d.data.ttsAudioUrl)&&self.guideProvider!=='xingyun')setTimeout(function(){self.revealAnswer()},1500)
          } else self.revealAnswer()
        } else { uni.showToast({title:(d&&d.message)||'回复失败',icon:'none'}) }
      }).catch(function(e) {
        if(turn!==self._turnVersion)return
        uni.showToast({title:e.message || (/timeout/i.test(e.errMsg||'')?'回答等待超时，请重试':'无法连接服务器，请检查网络'),icon:'none'})
      })
        .finally(function() { if(turn===self._turnVersion){if(!self._answerPending)self.loading = false; self.lastMsgId = 'bottom'} })
    },
    onConfirm: function(e) { this.send(e.detail ? e.detail.value : '') },
    onSend: function() { this.send(this.text) },
    openRepair:async function(message){
      if(this.repairOpening||this.repairOpen||this.leavingTour||this.endingTour)return
      this.repairOpening=true;this._turnVersion=(this._turnVersion||0)+1;this._chatTask?.abort();this.loading=false;this.cancelRecord();this.stopPlayback()
      const current=this._turnVersion
      try{const ready=await this.refresh(true);if(current!==this._turnVersion||!this.tourVisible||this.leavingTour)return;if(!ready){uni.showToast({title:this.t('导览信息加载失败，请重试'),icon:'none'});return}this.repairPrompt=message||'';this.showRouteInfo=false;this.repairOpen=true}
      finally{this.repairOpening=false}
    },
    routeRepaired:async function(){this.repairOpen=false;this._turnVersion=(this._turnVersion||0)+1;this.stopPlayback();if(await this.refresh(true))uni.showToast({title:this.t('路线已更新'),icon:'none'});else uni.showToast({title:this.t('路线已保存，请重新进入导览查看'),icon:'none'})},
    refresh: function(preferServerCurrent) {
      var self = this,version=self._liveVersion=(self._liveVersion||0)+1
      return api.getLiveInfo(self.sid).then(function(res) {
        if(version!==self._liveVersion||self.leavingTour)return false
        var d = res.data
        if (d && d.success) {
          var data = d.data
          if(data.live_status===2){self.repairOpen=false;self.routeOverview=null;return false}
          self.routeOverview=data.remaining_route_overview||data.route_overview||null;self.repairInitial=repairDefaults(data);self.liveCurrentId=data.current_spot_info?.spot_id||0
          self.msgs = data.conversation || []
          self.localizeChat();self.warmChat()
          if (data.guide_info) {
            self.guideProvider = data.guide_info.render_mode || ''
            self.guideName = data.guide_info.name || ''
            self.guideNameEn = data.guide_info.name_en || ''
            var gid=data.guide_info.guide_id
              self.guideSourceVideo=assetUrl(data.guide_info.base_mp4_path||'')
            if(self.guideProvider==='xingyun'){self.guideId=gid;self.avatarMode='audio';
              // #ifdef APP-PLUS
              self.avatarMode='xingyun';self.connectXingyun()
              // #endif
              // #ifndef APP-PLUS
              self.avatarMessage='星云未连接 · 可使用语音导览'
              // #endif
            }else if(gid&&gid!==self.guideId){self.guideId=gid;self._capabilityPromise=request({url:'/avatar/capabilities/'+gid}).then(function(r){self.avatarCapability=r.data.data;self.avatarMode=self.avatarCapability.realistic.ready?'realistic':'audio';self.updateAvatarMessage()}).catch(function(){self.avatarMessage='数字人服务状态查询失败'})}
          }
          var selectedIds=[];try{selectedIds=JSON.parse(data.visitor_preferences||'{}').spot_ids||[]}catch(e){}
          if(!selectedIds.length&&data.route_info)selectedIds=data.route_info.spot_ids||[]
          const update=function(spots){
            if(version!==self._liveVersion||self.leavingTour)return false
            var viewed=self.spotCards[self.spotIdx]
            self.spotCards=selectedIds.map(id=>spots.find(spot=>spot.spot_id===id)).filter(Boolean)
            var activeId=preferServerCurrent?self.liveCurrentId:(viewed?.spot_id||self.liveCurrentId)
            var index=self.spotCards.findIndex(spot=>spot.spot_id===activeId);self.spotIdx=index>=0?index:0
            return true
          }
          if(data.route_spots?.length)return update(data.route_spots)
          if(selectedIds.length)return request({url:'/tour-session/spots'}).then(r=>update(r.data?.data?.spot_list||[]))
          self.spotCards=[];return true
        }
        return false
      }).catch(function(){return false})
    },
    goBack: function() { this.leaveTour() },
    // 重建首页并移除导览页；返回不能依赖渲染层回调或云端响应。
    leaveTour: function(url) {
      if(this.leavingTour)return
      this.leavingTour=true;this.repairOpen=false;this.showRouteInfo=false;this._turnVersion=(this._turnVersion||0)+1;this._liveVersion=(this._liveVersion||0)+1;this._chatTask?.abort()
      this.showEndConfirm=false
      this.cancelRecord();this.stopPlayback();this.stopGps()
      this.closeXingyun()
      var self=this
      uni.reLaunch({url:url||'/pages/tabs/tabs?tab=tour',fail:function(){
        self.leavingTour=false
        uni.showToast({title:'返回首页失败，请重试',icon:'none'})
      }})
    },
    confirmEnd: function() { if(!this.endingTour&&!this.leavingTour)this.showEndConfirm=true },
    endTour: function() {
      if(this.endingTour||this.leavingTour)return
      this.endingTour=true
      this.showEndConfirm=false
      var self=this
      return api.endSession(this.sid).then(function(result){
        if(!result.data||!result.data.success)throw new Error(result.data&&result.data.message||'结束记录保存失败')
        self.leaveTour('/pages/tour-summary/tour-summary?sessionId='+self.sid)
      }).catch(function(){self.endingTour=false;uni.showToast({title:self.t('结束导览保存失败，请重试'),icon:'none'})})
    },
    toggleGps: function() {
      if (this.gpsTracking) { this.stopGps() }
      else { this.startGps() }
    },
    startGps: function() {
      var self = this
      this.stopGps()
      this.gpsTracking = true
      this.distanceStatus = '正在获取当前位置…'
      uni.getLocation({
        type: 'gcj02', isHighAccuracy: true,
        success: function(res) { self.userLat = res.latitude; self.userLng = res.longitude; self.checkNearby() },
        fail: function() { self.distanceStatus='定位失败，请开启手机定位并允许位置权限'; uni.showToast({ title: '定位失败，请检查权限', icon: 'none' }) }
      })
      this.gpsTimer = setInterval(function() {
        uni.getLocation({
          type: 'gcj02',
          success: function(res) { self.userLat = res.latitude; self.userLng = res.longitude; self.checkNearby() },
          fail: function() { self.distanceStatus='定位暂时失败，正在重试…' }
        })
      }, 5000)
    },
    stopGps: function() {
      this.gpsTracking = false
      this.mapExpanded = false
      if (this.gpsTimer) { clearInterval(this.gpsTimer); this.gpsTimer = null }
    },
    checkNearby: function() {
      if(this.repairOpen||this.repairOpening||this.showRouteInfo)return
      if (!this.userLat || !this.userLng || !this.sid) return
      var self = this
      var gps = gcj02ToWgs84(this.userLat, this.userLng)
      var target = this.currentSpot.spot_id || 0
      api.checkNearby(gps[0], gps[1], this.sid, target).then(function(res) {
        if (!self.gpsTracking || self.repairOpen || self.repairOpening || target !== (self.currentSpot.spot_id || 0)) return
        var d = res.data && res.data.data
        if (!d) return
        self.distanceStatus = d.target_spot ? '距'+d.target_spot.spot_name+'约 '+(d.target_spot.distance >= 1000 ? (d.target_spot.distance/1000).toFixed(2)+' 公里' : Math.round(d.target_spot.distance)+' 米')+'（直线距离）' : '当前景点暂无坐标，无法测距'
        if (d.closest_spot) {
          self.nearestSpotName = d.closest_spot.spot_name || ''
          self.nearestDistance = Math.round(d.closest_spot.distance || 0)
        }
        if (d.auto_switched) {
          var newIdx = self.spotCards.findIndex(function(s) { return s.spot_name === self.nearestSpotName })
          if (newIdx >= 0 && newIdx !== self.spotIdx) {
            self.spotIdx = newIdx
            self.mediaExpanded = false
            uni.showToast({ title: '到达「' + self.nearestSpotName + '」', icon: 'none', duration: 2000 })
            self.send('请介绍「' + self.spotName + '」')
          }
        }
      }).catch(function() { if(self.gpsTracking) self.distanceStatus='距离更新失败，请检查导览服务器连接' })
    },
    showKnowCard: function() {
      var s = this.currentSpot
      var fact = ''
      if (s.history_detail && s.history_detail.length > 20) {
        fact = s.history_detail.substring(0, 80)
        if (s.history_detail.length > 80) fact += '...'
      } else if (s.description && s.description.length > 20) {
        fact = s.description.substring(0, 80)
        if (s.description.length > 80) fact += '...'
      } else if (s.photo_tips) {
        fact = '最佳拍摄：' + s.photo_tips.substring(0, 60)
      }
      if (!fact) return
      var img = s.image_path ? this.fixImg(s.image_path) : ''
      this.knowCard = { visible: true, text: fact, image: img }
      var self = this
      if (this._knowTimer) clearTimeout(this._knowTimer)
      this._knowTimer = setTimeout(function() { self.knowCard.visible = false }, 6000)
    },
    dismissKnowCard: function() {
      this.knowCard.visible = false
      if (this._knowTimer) { clearTimeout(this._knowTimer); this._knowTimer = null }
    },
    toggleVoiceMode:function(){if(this.recording||this.transcribing)return;this.voiceMode=!this.voiceMode;this.textareaFocus=false;if(this.voiceMode)uni.hideKeyboard()},
    initRecorder: function() {
      if(this._voiceManager)return this._voiceManager
      var self=this,rm=uni.getRecorderManager();self._voiceManager=rm
      rm.onStart(function(){self._recordStartedAt=Date.now();if(!self.voicePressing)rm.stop()})
      rm.onStop(function(res){
        self.recording=false;self.voicePressing=false
        if(self._recordCancelled)return
        var duration=Number(res.duration)||(self._recordStartedAt?Date.now()-self._recordStartedAt:0)
        if(!res.tempFilePath||duration<500){uni.showToast({title:'请按住说话至少半秒',icon:'none'});return}
        self.transcribing=true
        uni.uploadFile({url:BASE_URL+'/tour-session/asr-upload',filePath:res.tempFilePath,name:'file',timeout:120000,
          header:{Authorization:'Bearer '+uni.getStorageSync('token')},
          success:function(r){
            try{var d=JSON.parse(r.data)
              if(r.statusCode===200&&d.success&&d.data){self.text=d.data;self.send(d.data);return}
              uni.showToast({title:typeof d.detail==='string'?d.detail:d.message||'语音识别服务返回错误',icon:'none',duration:4000})
            }catch(e){uni.showToast({title:'语音识别返回格式异常',icon:'none'})}
          },
          fail:function(){uni.showToast({title:'语音上传失败，请检查网络连接',icon:'none'})},
          complete:function(){self.transcribing=false}
        })
      })
      rm.onError(function(){self.recording=false;self.voicePressing=false;uni.showToast({title:'录音失败，请检查麦克风权限',icon:'none'})})
      return rm
    },
    startRecord: function() {
      if(this.recording||this.transcribing||this.loading)return
      this._recordStartedAt=0;this._recordCancelled=false;this.voicePressing=true;this.recording=true
      try{this.initRecorder().start({duration:60000,sampleRate:16000,numberOfChannels:1,format:'mp3'})}
      catch(e){this.recording=false;this.voicePressing=false;uni.showToast({title:'无法启动录音，请检查麦克风权限',icon:'none'})}
    },
    stopRecord: function() {this.voicePressing=false;if(this._voiceManager&&this._recordStartedAt)this._voiceManager.stop()},
    cancelRecord: function(){this._recordCancelled=true;this.voicePressing=false;this.recording=false;if(this._voiceManager&&this._recordStartedAt)this._voiceManager.stop()},
  },
  onBackPress:function(){if(this.repairOpen){if(!this.$refs.routeRepair?.applying)this.repairOpen=false;return true}if(this.showRouteInfo){this.showRouteInfo=false;return true}},
  onUnload:function(){this._translationVersion=(this._translationVersion||0)+1;this._turnVersion=(this._turnVersion||0)+1;this._liveVersion=(this._liveVersion||0)+1;this._chatTask?.abort();this.repairOpen=false;this.tourVisible=false;this.cancelRecord();this.stopPlayback();this.closeXingyun();this.stopGps();if(uni.offKeyboardHeightChange&&this._kbListener)uni.offKeyboardHeightChange(this._kbListener)},
  onHide:function(){this.keyboardHeight=0;this._turnVersion=(this._turnVersion||0)+1;this._chatTask?.abort();this.loading=false;this.repairOpen=false;this.showRouteInfo=false;this.tourVisible=false;this.cancelRecord();this.stopPlayback();this.closeXingyun();
  },
  onShow:async function(){this.tourVisible=true;if(this._xingyunClosePromise)await this._xingyunClosePromise;if(this.guideProvider==='xingyun')this.connectXingyun()},
  onLoad: function(opts) {
    // #ifdef APP-PLUS
    this.appXingyun=true
    // #endif
    this.sid = Number(opts.sessionId || 0)
    if (!this.sid) { uni.showToast({title:'会话ID无效',icon:'none'}); return }
    var s = uni.getSystemInfoSync()
    this.statusH = (s.statusBarHeight || 20) + 6
    this.refresh()
    var self=this
    // 兜底监听键盘高度：部分机型输入框不派发 keyboardheightchange
    if(uni.onKeyboardHeightChange){this._kbListener=function(res){self.onKeyboardHeight({detail:{height:res.height}})};uni.onKeyboardHeightChange(this._kbListener)}
    setTimeout(function(){self.measureProgress()},700)
    setTimeout(function(){self.measureProgress()},2200)
  },
}
</script>

<style scoped>
.chat-translation{padding:16rpx;text-align:center;font-size:24rpx;color:var(--ng-secondary)}
.route-tools{display:flex;gap:14rpx;padding:12rpx 24rpx;flex-shrink:0}.route-tools button{flex:1;min-width:0;margin:0;font-size:26rpx;line-height:2.5;border:1rpx solid var(--ng-border);border-radius:14rpx;color:#614b9a;background:#f0ecf8}.tour-route-mask{position:fixed;inset:0;z-index:1500;background:rgba(25,30,50,.35);display:flex;align-items:flex-end}.tour-route-sheet{width:100%;height:88vh;padding:28rpx 28rpx calc(28rpx + env(safe-area-inset-bottom));box-sizing:border-box;background:var(--ng-surface,#fff);border-radius:30rpx 30rpx 0 0;display:flex;flex-direction:column}.tour-route-heading{display:flex;align-items:center;justify-content:space-between;font-size:34rpx;padding-bottom:24rpx}.tour-route-heading button{margin:0;padding:0 20rpx;font-size:36rpx;line-height:1.7;background:#f5f1fa;color:#655574}.tour-route-body{flex:1;height:0;min-height:0}
.xingyun-open{margin:8rpx 24rpx;padding:8rpx 24rpx;border:1rpx solid var(--ng-border);border-radius:14rpx;color:var(--ng-secondary);background:var(--ng-surface);font-size:26rpx;flex-shrink:0}
.xingyun-retry{position:relative;z-index:1;flex-shrink:0;display:flex;align-items:center;justify-content:center;min-height:44px;margin:0 24rpx;color:#7952d5;font-size:26rpx;background:transparent;border:0;box-shadow:none}
.stage-footer{position:relative;z-index:1;display:flex;align-items:center;gap:12rpx;padding:10rpx 24rpx;flex-shrink:0}
.stage-footer .avatar-runtime-status{flex:1;min-width:0;padding:0;color:var(--ng-secondary);font-size:22rpx;line-height:1.6}
.stage-location{display:flex;align-items:center;justify-content:flex-end;gap:10rpx;max-width:70%;margin-left:auto}
.guide-stage{flex-shrink:0}
.avatar-video{width:100%;height:100%}.avatar-notice{font-size:24rpx;line-height:1.7;color:var(--ng-secondary);padding:0 28rpx;text-align:center;max-width:560rpx}
.page{height:100vh;height:100dvh;width:100%;min-width:0;box-sizing:border-box;display:flex;flex-direction:column;background-color:var(--ng-surface);position:relative;overflow:hidden}
.avatar-runtime-status,.xingyun-open,.tour-progress,.spot-media{position:relative;z-index:1}
.nav-spacer{flex:1;min-width:0}
.nav .nav-progress{position:relative;flex:1;min-width:0;padding:4rpx 0}
.nav-progress .tp-nodes{min-width:0;justify-content:flex-start}
.nav-progress .tp-stats{justify-content:center;flex-wrap:wrap;gap:4rpx 12rpx}
.nav-progress .tp-stat{font-size:18rpx}
.nav-distance{max-width:56vw;font-size:20rpx;line-height:1.4;color:var(--ng-accent-text)}
.stage-guide-name{position:absolute;left:20rpx;top:16rpx;z-index:4;padding:8rpx 18rpx;border-radius:14rpx;background:transparent;color:#000;font-size:28rpx;font-weight:600;max-width:36%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tour-gradient{position:absolute;inset:0;pointer-events:none;z-index:0;background:linear-gradient(135deg,#eee8ff 0%,#f6f2ff 28%,#fbfbff 52%,#eef8fc 76%,#eee8ff 100%);background-size:220% 220%;animation:tourGradientFlow 16s ease-in-out infinite alternate}
@keyframes tourGradientFlow{from{background-position:0% 0%}to{background-position:100% 100%}}
.page-bg{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0}

/* 导航 */
.nav{position:relative;z-index:3;display:flex;align-items:center;padding:4rpx 20rpx;gap:12rpx;align-items:flex-start;flex-shrink:0}
.nav-back{width:56rpx;height:56rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--ng-glass-blue-bg);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);font-size:40rpx;color:var(--ng-secondary);flex-shrink:0}
.nav-title{flex:1;font-size:36rpx;font-weight:600;color:var(--ng-text);letter-spacing:4rpx;font-family:var(--app-font-family);text-align:center}
.nav-end{width:56rpx;height:56rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--ng-glass-blue-bg);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);font-size:30rpx;color:var(--ng-secondary);flex-shrink:0}
.nav-gps{width:56rpx;height:56rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.06);font-size:26rpx;color:var(--ng-secondary);flex-shrink:0}
.nav-gps.on{background:rgba(99,102,241,0.25);box-shadow:0 0 0 4rpx rgba(99,102,241,0.08)}

/* 实时小地图 */
.mini-map{position:absolute;right:12rpx;bottom:12rpx;z-index:2;width:140rpx;height:140rpx;border-radius:16rpx;overflow:hidden;border:2rpx solid rgba(99,102,241,0.25);box-shadow:0 4rpx 16rpx rgba(0,0,0,.3);transition:transform .3s,opacity .3s}
.mini-map.expanded{width:100%;height:100%;left:0;right:0;bottom:0;border-radius:0;border:none}
.mm-canvas{width:100%;height:100%}
.mm-no-coords{width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:var(--ng-surface)}
.mm-nc-text{font-size:20rpx;color:var(--ng-secondary)}
.mm-info{position:absolute;left:0;right:0;bottom:0;padding:4rpx 8rpx;background:rgba(0,0,0,.5);backdrop-filter: none}
.mm-dist{font-size:18rpx;color:#1f2937}
.mm-close{position:absolute;top:12rpx;right:12rpx;width:48rpx;height:48rpx;border-radius:50%;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;font-size:28rpx;color:#fff;z-index:3}

/* 知识卡片 */
.know-card{position:absolute;left:12rpx;top:12rpx;z-index:3;max-width:55%;animation:kcSlide .3s ease}
@keyframes kcSlide{from{opacity:0;transform:translateX(-20rpx)}to{opacity:1;transform:translateX(0)}}
.kc-inner{display:flex;flex-direction:column;gap:6rpx;padding:12rpx 14rpx;border-radius:12rpx;background:rgba(0,0,0,.65);backdrop-filter: none;border:1rpx solid rgba(99,102,241,0.2)}
.kc-tag{font-size:18rpx;color:rgba(99,102,241,0.25)}
.kc-text{font-size:20rpx;color:#1f2937;line-height:1.5}
.kc-img{width:100%;height:120rpx;border-radius:8rpx;margin-top:4rpx}

/* 数字导游区域 — 大半屏 */
.page .guide-stage{position:relative;z-index:2;width:min(calc(100% - 16rpx),calc(34vh * 16 / 9));max-width:100%;aspect-ratio:16/9;height:auto;flex-shrink:0;display:flex;align-items:center;justify-content:center;margin:0 auto;border-radius:24rpx;overflow:hidden;background:linear-gradient(180deg,var(--ng-surface) 0%,var(--ng-surface) 50%,var(--ng-surface) 100%);box-shadow:0 18rpx 44rpx -20rpx rgba(30,41,59,.24),0 4rpx 16rpx rgba(30,41,59,.06)}
@supports not (aspect-ratio:16/9){.page .guide-stage{width:calc(100% - 16rpx);height:34vh}}
.spot-nav-bar{position:absolute;top:16rpx;left:0;right:0;z-index:3;display:flex;align-items:center;justify-content:center;gap:12rpx;padding:0 20rpx}
.spot-arrow{width:52rpx;height:52rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.35);backdrop-filter: none;font-size:36rpx;color:var(--ng-text);flex-shrink:0}
.spot-label-text{padding:8rpx 16rpx;border-radius:10rpx;background:rgba(0,0,0,.45);backdrop-filter: none;color:var(--ng-text);font-size:22rpx;font-weight:700;white-space:nowrap}
.stage-status{position:absolute;bottom:12rpx;left:50%;right:auto;transform:translateX(-50%);z-index:2;padding:6rpx 14rpx;border-radius:10rpx;background:rgba(0,0,0,.35);backdrop-filter: none}
.stage-status text{color:#fff;font-size:22rpx;white-space:nowrap}
.stage-status.on{background:rgba(30,30,50,.35)}
.avatar-loading{height:28rpx;display:flex;align-items:center;justify-content:center;gap:8rpx;padding:0 6rpx}
.avatar-loading-dot{width:9rpx;height:9rpx;border-radius:50%;background:#fff;animation:avatar-loading-bounce 1.2s ease-in-out infinite}
.avatar-loading-dot:nth-child(2){animation-delay:.16s}.avatar-loading-dot:nth-child(3){animation-delay:.32s}
@keyframes avatar-loading-bounce{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-6rpx);opacity:1}}
@media(prefers-reduced-motion:reduce){.avatar-loading-dot{animation:none;opacity:.8}}
.guide-img{width:80%;height:80%;background:transparent}
.guide-img.speaking{animation:guideTalk .3s ease-in-out infinite}
@keyframes guideBreathe{0%,100%{transform:scale(1)}50%{transform:scale(1.03)}}
@keyframes guideTalk{0%,100%{transform:scale(1)}25%{transform:scale(1.01) translateY(-2rpx)}75%{transform:scale(1.01) translateY(2rpx)}}
.guide-img-df{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16rpx}
.guide-df-icon{font-size:120rpx}
.guide-df-name{font-size:36rpx;font-weight:600;color:var(--ng-secondary);font-family:var(--app-font-family)}

/* 景点切换卡片 */
.spot-switch{position:relative;z-index:1;display:flex;align-items:center;gap:8rpx;padding:8rpx 16rpx}
.ss-arrow{width:44rpx;height:44rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--ng-surface);border:1rpx solid var(--ng-border);font-size:30rpx;color:var(--ng-secondary);flex-shrink:0}
.ss-card{flex:1;display:flex;gap:12rpx;padding:10rpx 14rpx;background:var(--ng-surface);border-radius:14rpx;border:1rpx solid var(--ng-border);min-width:0}
.ss-img{width:72rpx;height:72rpx;border-radius:12rpx;flex-shrink:0}
.ss-img-df{width:72rpx;height:72rpx;border-radius:12rpx;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.1);font-size:32rpx;flex-shrink:0}
.ss-info{flex:1;min-width:0}
.ss-top{display:flex;align-items:center;gap:8rpx}
.ss-name{font-size:26rpx;font-weight:600;color:var(--ng-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ss-cat{font-size:18rpx;color:var(--ng-secondary);background:rgba(99,102,241,0.08);padding:2rpx 10rpx;border-radius:6rpx;flex-shrink:0}

/* 对话区 */
.chat-area{position:relative;z-index:1;flex:1;width:100%;height:0;min-width:0;min-height:0;box-sizing:border-box;padding:0}
.chat-content{width:100%;min-width:0;box-sizing:border-box;padding:12rpx 20rpx 24rpx}
.chat-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%}
.ce-icon{font-size:64rpx;margin-bottom:12rpx}
.ce-title{font-size:28rpx;font-weight:600;color:var(--ng-text);margin-bottom:8rpx}
.ce-sub{font-size:22rpx;color:var(--ng-secondary)}
.msg-row{width:100%;min-width:0;box-sizing:border-box;margin-bottom:18rpx;display:flex}
.msg-l{justify-content:flex-start}
.msg-r{justify-content:flex-end}
.msg-bubble{max-width:82%;min-width:0;box-sizing:border-box;padding:16rpx 22rpx;border-radius:18rpx;overflow-wrap:anywhere}
.msg-bubble.user{background:linear-gradient(135deg,rgba(99,102,241,0.18),rgba(99,102,241,0.18));border-bottom-right-radius:6rpx}
.msg-bubble.guide{background:var(--ng-surface);border:1rpx solid var(--ng-border);border-bottom-left-radius:6rpx}
.msg-bubble.user .msg-text{color:var(--ng-text)}
.msg-bubble.guide .msg-text{color:var(--ng-text)}
.msg-text{display:block;font-size:28rpx;line-height:1.8;word-break:break-word;overflow-wrap:anywhere;white-space:pre-wrap}
.msg-time{font-size:20rpx;text-align:right;display:block;margin-top:6rpx}
.msg-l .msg-time{color:var(--ng-secondary)}
.msg-r .msg-time{color:var(--ng-text)}
.loading-tip{display:flex;align-items:center;justify-content:center;gap:8rpx;min-height:34rpx;padding:16rpx}
.loading-tip .avatar-loading-dot{width:12rpx;height:12rpx;background:var(--ng-secondary)}

/* 底部输入 */
.bottom-bar{position:relative;width:100%;box-sizing:border-box;z-index:2;flex-shrink:0;border-top:1rpx solid var(--ng-border);background:var(--ng-surface);padding-bottom:env(safe-area-inset-bottom,0px)}
/* 输入区尺寸与 AI 小导游页保持一致（84/88rpx、胶囊圆角） */
.input-row{display:flex;align-items:flex-end;gap:12rpx;padding:16rpx 18rpx 18rpx}
.voice-btn{width:84rpx;height:84rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--ng-glass-blue-bg);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);flex-shrink:0}
.voice-btn .iconfont{font-size:32rpx;color:var(--ng-secondary)}
.voice-btn.rec{background:#e6f0ff}
.voice-btn.rec .iconfont{color:var(--ng-text)}
.voice-hold-btn{flex:1;height:88rpx;display:flex;align-items:center;justify-content:center;border:1rpx dashed rgba(182,207,238,.9);border-radius:44rpx;background:var(--ng-glass-blue-bg);font-size:28rpx;color:var(--ng-soft-blue-text);font-weight:600;user-select:none;box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9)}
.voice-hold-btn.pressing{background:rgba(230,240,255,.85);color:var(--ng-soft-blue-text);border-style:solid;border-color:rgba(182,207,238,.9)}
@keyframes recPulse{0%,100%{box-shadow:0 0 0 0 rgba(99,102,241,0.15)}50%{box-shadow:0 0 0 12rpx rgba(99,102,241,0.15)}}
.msg-input{flex:1;height:88rpx;min-height:88rpx;padding:20rpx 24rpx;border:1rpx solid var(--ng-border);border-radius:28rpx;background:var(--ng-surface);font-size:28rpx;line-height:1.5;color:var(--ng-text);box-sizing:border-box;overflow-y:auto;max-height:360rpx}
.input-row .send-btn{height:88rpx;padding:0 32rpx;line-height:88rpx;border-radius:44rpx;background:var(--ng-glass-blue-bg);color:var(--ng-soft-blue-text);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.92);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);font-size:28rpx;font-weight:700;flex-shrink:0}
.send-btn.disabled{opacity:.35}
.spot-switch{flex-shrink:0}.ss-card{align-items:center}.ss-img{height:80rpx;width:80rpx}

/* 游览进度时间轴 */
.tour-progress{flex-shrink:0;padding:6rpx 16rpx 8rpx}
.tp-track{white-space:nowrap}
.tp-nodes{display:inline-flex;align-items:center;gap:0;padding:4rpx 0}
.tp-node{display:inline-flex;flex-direction:column;align-items:center;min-width:100rpx;position:relative;padding:0 8rpx}
.tp-node::after{content:'';position:absolute;top:15rpx;left:calc(50% + 16rpx);right:calc(-50% + 16rpx);width:auto;height:2rpx;background:var(--ng-border)}
.tp-node:last-child::after{display:none}
.tp-dot{width:28rpx;height:28rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--ng-surface);border:2rpx solid var(--ng-border);z-index:1}
.tp-node.active .tp-dot{border-color:rgba(190,213,245,.7);background:var(--ng-glass-blue-bg);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9)}
.tp-node.done .tp-dot{border-color:var(--ng-border);background:var(--ng-surface)}
.tp-check{font-size:18rpx;color:var(--ng-secondary);font-weight:700}
.tp-now{font-size:14rpx;color:var(--ng-text)}
.tp-label{font-size:18rpx;color:var(--ng-secondary);margin-top:6rpx;max-width:100rpx;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;transition:color .3s ease}
.tp-node.active .tp-label{color:var(--ng-text);font-weight:600}
.tp-node.done .tp-label{color:var(--ng-secondary)}
.guide-stage .stage-progress{position:absolute;top:16rpx;right:20rpx;left:auto;z-index:5;box-sizing:border-box;max-width:58%;padding:8rpx 0;background:transparent;pointer-events:none;justify-content:flex-end;text-align:right;gap:0}
.guide-stage .stage-progress .tp-stat{font-size:22rpx;line-height:36rpx;color:var(--ng-text);text-shadow:0 1rpx 3rpx rgba(255,255,255,.9)}
.tp-stats{display:flex;justify-content:space-between;align-items:center;padding:2rpx 4rpx 0}
.tp-stat{font-size:20rpx;color:var(--ng-secondary)}
.tp-stat.done{color:rgba(99,102,241,0.25)}

/* 景点沉浸式媒体 */
.spot-media{flex-shrink:0;margin:0 16rpx 4rpx;border-radius:14rpx;border:1rpx solid var(--ng-border);overflow:hidden;background:var(--ng-surface)}
.sm-bar{display:flex;align-items:center;gap:12rpx;padding:8rpx 14rpx}
.sm-thumb{width:56rpx;height:56rpx;border-radius:10rpx;flex-shrink:0}
.sm-thumb-df{width:56rpx;height:56rpx;border-radius:10rpx;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.08);font-size:28rpx;flex-shrink:0}
.sm-bar-info{flex:1;min-width:0}
.sm-bar-title{font-size:24rpx;font-weight:600;color:var(--ng-text);display:block}
.sm-bar-sub{font-size:20rpx;color:var(--ng-secondary);display:block;margin-top:2rpx}
.sm-arrow{font-size:32rpx;color:var(--ng-secondary);flex-shrink:0;transition:transform .2s}
.sm-arrow.open{transform:rotate(90deg)}
.sm-body{padding:4rpx 14rpx 12rpx;max-height:22vh;overflow-y:auto}
.sm-section{margin-top:8rpx}
.sm-section-title{font-size:22rpx;font-weight:600;color:var(--ng-text);display:block;margin-bottom:4rpx}
.sm-section-text{font-size:22rpx;color:var(--ng-secondary);line-height:1.6}
.voice-mute-btn{position:absolute;right:24rpx;top:calc(18rpx + env(safe-area-inset-top));z-index:8;width:64rpx;height:64rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;gap:6rpx;background:rgba(255,255,255,.86);border:1rpx solid rgba(99,102,241,.22);box-shadow:0 6rpx 20rpx rgba(30,41,59,.12)}
.voice-mute-btn.muted{background:rgba(148,163,184,.28);border-color:rgba(148,163,184,.35)}
.vm-pause{display:flex;align-items:center;gap:6rpx}
.vm-bar{width:8rpx;height:26rpx;border-radius:4rpx;background:#4f46e5;display:block}
.voice-mute-btn.muted .vm-bar{background:#64748b}
.vm-play{width:0;height:0;border-left:22rpx solid #64748b;border-top:13rpx solid transparent;border-bottom:13rpx solid transparent;margin-left:6rpx}
.msg-voice-btn{display:inline-flex;align-items:center;justify-content:center;gap:5rpx;width:44rpx;height:44rpx;margin-left:10rpx;border-radius:50%;background:rgba(99,102,241,.12);vertical-align:middle}
.msg-voice-btn.muted{background:rgba(148,163,184,.22)}
.msg-voice-btn .vm-bar{width:6rpx;height:20rpx;border-radius:3rpx;background:#4f46e5;display:block}
.msg-voice-btn.muted .vm-bar{background:#64748b}
.msg-voice-btn .vm-play{width:0;height:0;border-left:16rpx solid #64748b;border-top:10rpx solid transparent;border-bottom:10rpx solid transparent;margin-left:4rpx}
.voice-mute-btn{display:none}

.page .guide-stage{background:transparent}
.nav-progress .tp-nodes{display:inline-flex;align-items:stretch;width:max-content;min-width:100%}
.nav-progress .tp-node{width:174rpx;min-width:174rpx;flex:0 0 174rpx;padding:0 4rpx;box-sizing:border-box}
.nav-progress .tp-nodes.tp-centered{justify-content:center;width:100%}
.nav-progress .tp-nodes.tp-centered .tp-node{width:auto;min-width:0;flex:1 1 0;padding:0 4rpx}
.nav-progress .tp-nodes.tp-centered .tp-label{max-width:100%;white-space:normal;word-break:break-word;overflow:visible;text-overflow:clip;line-height:1.2;font-size:17rpx}
.nav-progress .tp-label{max-width:100%;white-space:normal;word-break:break-word;overflow:visible;text-overflow:clip;line-height:1.2;font-size:17rpx}
.tp-more-slot{flex:0 0 40rpx;width:40rpx;display:flex;align-items:center;justify-content:center;align-self:center}
.tp-more{font-size:28rpx;line-height:1;letter-spacing:2rpx;color:var(--ng-secondary);opacity:.9}
.nav-progress .tp-node>.tp-dot{margin:0 auto}
.tp-track.fade-left.fade-right{-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 44rpx,#000 calc(100% - 44rpx),transparent 100%);mask-image:linear-gradient(90deg,transparent 0,#000 44rpx,#000 calc(100% - 44rpx),transparent 100%)}
.tp-track.fade-left:not(.fade-right){-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 44rpx,#000 100%);mask-image:linear-gradient(90deg,transparent 0,#000 44rpx,#000 100%)}
.tp-track.fade-right:not(.fade-left){-webkit-mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 44rpx),transparent 100%);mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 44rpx),transparent 100%)}
.tp-dot{transition:background .3s ease,border-color .3s ease,box-shadow .3s ease}
.bottom-bar.keyboard-open{z-index:10001;box-shadow:0 -8rpx 24rpx rgba(15,23,42,.08)}
</style>
