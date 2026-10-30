<template>
  <view class="page aurora-page no-tabbar chat-ref-page" :class="{'app-english':tourLanguage==='en','chat-keyboard':keyboardVisible}">
    <!-- #ifdef APP-PLUS -->
    <view class="app-status-bar-shield" aria-hidden="true"></view>
    <!-- #endif -->
    <view class="aurora-background chat-scenery" aria-hidden="true"><view class="chat-wave chat-wave-blue"></view><view class="chat-wave chat-wave-lilac"></view></view>

    <!-- 水墨背景 -->
    <view class="ink-bg">
      <view class="ink-mountain ink-mt-1"></view>
      <view class="ink-mountain ink-mt-2"></view>
      <view class="ink-circle ink-c-1"></view>
    </view>

    <!-- 标题 -->
    <view class="nav" :style="{paddingTop:statusH+'px'}">
      <view class="nav-back" @tap="goBack" :aria-label="$t('返回')"><text class="iconfont icon-chevron-left" aria-hidden="true"></text></view>
      <view class="nav-spacer"></view>
      <text class="nav-clear" v-if="msgs.length" @tap="clearHistory">{{ $t("清空") }}</text>
      <button v-if="chatMode==='guide'" class="qh-spot" :disabled="loading||recognizing" @tap="pickSpot" :aria-label="$t('选择问答景点')">
        <view class="context-pin"><text class="iconfont icon-zuobiao"></text></view>
        <text class="context-name">{{ guideSpotName ? $t(guideSpotName) : $t('选择景点') }}</text>
      </button>
      <view class="nav-history" @tap="openHistory" :aria-label="$t('问答历史')">
        <text class="hist-clock iconfont icon-clock" aria-hidden="true"></text>
      </view>
    </view>

    <!-- 快捷提示 -->
    <view class="quick-hints" v-if="msgs.length === 0 && chatMode==='route'">
      <view class="qh-chip" @tap="quickSend('我想带孩子玩2小时，喜欢自然风光')">{{ $t("亲子2小时自然游") }}</view>
      <view class="qh-chip" @tap="quickSend('推荐颐和园的历史文化景点，半天时间')">{{ $t("颐和园历史文化半天") }}</view>
      <view class="qh-chip" @tap="quickSend('帮我规划一个适合拍照的一日游路线')">{{ $t("拍照打卡一日游") }}</view>
      <view class="qh-chip" @tap="quickSend('周末带朋友玩半天，喜欢美食和拍照')">{{ $t("周末美食拍照") }}</view>
    </view>

    <!-- 对话区 -->
    <view class="conversation-stage">
    <scroll-view :scroll-y="!voicePressing" class="chat-area" :class="{'welcome-active':msgs.length===0&&!loading&&chatMode==='guide'}" :scroll-top="chatScrollTop" :scroll-with-animation="scrollAnim" @scroll="onChatScroll">
      <view v-if="msgs.length===0&&!loading&&chatMode==='guide'" class="guide-welcome">
        <view v-if="qaCatalogLoading" class="welcome-loading" aria-live="polite">{{ $t('正在加载景点…') }}</view>
        <view v-else-if="catalogError" class="welcome-unavailable">
          <text>{{ $t(catalogError) }}</text>
          <button @tap="loadWelcomeCatalog">{{ $t('重试') }}</button>
        </view>
        <view class="welcome-art" aria-hidden="true">
          <view class="welcome-art-shadow"></view>
          <view class="welcome-balloon"><view class="welcome-dots"><view></view><view></view><view></view></view></view>
          <text class="welcome-sparkle welcome-sparkle-large iconfont icon-sparkles" aria-hidden="true"></text><text class="welcome-sparkle welcome-sparkle-small iconfont icon-sparkles" aria-hidden="true"></text>
        </view>
        <text class="welcome-title">{{ $t('想了解哪个景点？') }}</text>
        <text class="welcome-description">{{ $t('可以选择下方的快捷提问，或直接向我提问~') }}</text>
        <view class="welcome-topics">
          <button class="welcome-topic welcome-topic-intro" :disabled="qaCatalogLoading" @tap="askGuide('intro')"><view class="topic-icon-wrap"><text class="topic-icon iconfont icon-daolan"></text></view><text class="topic-title">{{ $t('介绍这个景点') }}</text></button>
          <button class="welcome-topic welcome-topic-story" :disabled="qaCatalogLoading" @tap="askGuide('story')"><view class="topic-icon-wrap"><text class="topic-icon iconfont icon-lishiwenhua"></text></view><text class="topic-title">{{ $t('这里有什么历史故事？') }}</text></button>
          <view class="welcome-photo-row"><button class="welcome-topic welcome-topic-photo" :disabled="qaCatalogLoading" @tap="askGuide('photo')"><view class="topic-icon-wrap"><text class="topic-icon iconfont icon-cam-3"></text></view><text class="topic-title">{{ $t('这里有什么拍照建议？') }}</text></button></view>
        </view>
      </view>
      <view v-else-if="msgs.length===0&&!loading" class="chat-empty">
        <text class="ce-title">{{ $t('想去哪里？') }}</text>
      </view>
      <view v-if="historyTranslationFailed" class="chat-translation" @tap="localizeHistory">{{ tourLanguage==='en'?'Translation unavailable — showing the original text. Tap to retry.':'翻译暂不可用，已显示原文。点击重试' }}</view>
      <view v-for="(m, i) in msgs" :key="i" :id="'m-'+i" class="msg-row" :class="m.role==='ai'?'msg-l':'msg-r'">
        <view class="msg-bubble" :class="m.role">
          <image v-if="m.image" :src="m.image" class="chat-photo" mode="widthFix" @load="scrollChat" @tap="previewChatPhoto(m.image)" />
          <block v-if="m.segments">
            <text v-for="(seg, si) in m.segments" :key="si" class="msg-text msg-seg">{{ seg.t }}</text>
            <text v-if="m.cursor" class="msg-caret">▍</text>
          </block>
          <text v-else-if="m.content" class="msg-text">{{ m.content }}</text>
          <button v-if="m.recognitionEvidence" class="photo-evidence-toggle" @tap="toggleEvidence(m)">{{ $t(m.showEvidence?'收起识别依据':'查看识别依据（原文）') }}</button>
          <text v-if="m.showEvidence&&m.recognitionEvidence" class="photo-evidence">{{ m.recognitionEvidence }}</text>
          <view v-if="m.role==='ai' && m.content && !m.cursor" class="msg-speaker" :class="{on:isReplyPlaying(i)}" :aria-label="$t(isReplyPlaying(i) ? '暂停语音播报' : '继续播放')" @tap="replayTTS(m.content,i)">
            <text v-if="!isReplyPlaying(i)" class="playback-glyph iconfont icon-play" aria-hidden="true"></text>
            <text v-else class="playback-glyph iconfont icon-pause" aria-hidden="true"></text>
          </view>
        </view>
      </view>
      <view v-if="loading" class="msg-row msg-l">
        <view class="msg-bubble ai typing">
          <view class="typing-dots" :aria-label="$t('AI思考中...')"><view class="td"></view><view class="td"></view><view class="td"></view></view>
        </view>
      </view>
      <view id="bottom"></view>
    </scroll-view>
    </view>

    <!-- 路线预览时间轴 -->
    <view class="route-preview" v-if="chatMode==='route' && lastSpotIds.length > 0 && !loading">
      <view class="rp-head">
        <text class="rp-title"> {{ $t("路线预览") }}</text>
        <text class="rp-count">{{ $t('{count}个景点',{count:recommendSpots.length || lastSpotIds.length}) }}</text>
      </view>
      <view v-if="recommendLoading" class="rp-loading"><text>{{ $t("路线加载中...") }}</text></view>
      <view v-else-if="recommendSpots.length" class="rp-timeline">
        <view v-for="(s, i) in recommendSpots" :key="s.spot_id" class="rp-item">
          <view class="rp-rail">
            <view class="rp-dot" :class="{ start: i === 0, end: i === recommendSpots.length - 1 }">{{ $t(i + 1) }}</view>
            <view class="rp-line" v-if="i < recommendSpots.length - 1"></view>
          </view>
          <view class="rp-card">
            <image v-if="s.image_path" :src="fixImg(s.image_path)" class="rp-img" mode="aspectFill"></image>
            <view v-else class="rp-img rp-img-df"></view>
            <view class="rp-info">
              <text class="rp-name">{{ $t(s.spot_name) }}</text>
              <text class="rp-cat">{{ $t(s.category || $t("景点")) }} {{ $t("· 预计") }} {{ $t(s.visit_duration ||10) }}{{ $t("分钟") }}</text>
              <text v-if="i < recommendSpots.length - 1" class="rp-walk">{{ $t('步行至下一站：') }}{{ walkText(s, recommendSpots[i + 1]) }}</text>
            </view>
          </view>
        </view>
        <view class="rp-total">
          <text class="rp-total-label">{{ $t("预计总时长") }}</text>
          <text class="rp-total-value">{{ totalDuration==null ? $t('时长待配置') : $t('{minutes}分钟',{minutes:totalDuration}) }}</text>
        </view>
      </view>
    </view>

    <!-- 推荐结果 -->
    <view class="result-bar" v-if="chatMode==='route' && lastSpotIds.length > 0 && !loading">
      <text>{{ $t('已推荐{count}个景点',{count:lastSpotIds.length}) }}</text>
      <view class="rb-btn" @tap="applyRecommend">{{ $t("使用路线") }}</view>
    </view>

    <view v-if="voiceError && !transcribing" class="voice-status">{{ $t(voiceError) }}</view>
    <view v-if="showPhotoChoices" class="photo-popover-mask" :class="{closing:photoClosing}" @tap="closePhotoChoices"></view>
    <!-- 底部固定区：输入框 + Tab，flex竖向排列 -->
    <view class="bottom-fixed" :class="{'keyboard-open':keyboardVisible, 'photo-open':showPhotoChoices}" :style="keyboardHeight>0?{paddingBottom:keyboardHeight+'px'}:{}">
      <!-- 录音波形以输入栏为定位基准，显示在输入栏上方的空白处。 -->
      <view class="recording-hint" v-if="recording" aria-hidden="true">
        <view class="rh-wave">
          <view v-for="i in 5" :key="i" class="rh-bar" :style="{animationDelay:(i*0.12)+'s'}"></view>
        </view>
      </view>
      <view v-if="pendingPhoto || recognitionError" class="photo-draft">
        <view v-if="pendingPhoto" class="draft-thumbnail"><image :src="pendingPhoto" mode="aspectFill" @tap="previewChatPhoto(pendingPhoto)" /><button class="draft-remove" @tap="pendingPhoto=''" :aria-label="t('关闭')"><text class="iconfont icon-close" aria-hidden="true"></text></button></view>
        <text v-if="pendingPhoto" class="draft-note">{{ $t("已选择图片，点击发送后识别") }}</text>
        <text v-if="recognitionError" class="photo-error">{{ $t(recognitionError) }}</text>
      </view>
      <!-- 输入栏 -->
    <view class="input-bar">
      <view class="photo-entry-wrap">
        <button class="photo-add" :disabled="recognizing" :aria-label="$t(&quot;拍照或相册识景&quot;)" :aria-expanded="showPhotoChoices" @tap="chooseScenicPhoto"><text class="iconfont icon-plus" aria-hidden="true"></text></button>
        <view v-if="showPhotoChoices" class="photo-popover" :class="{closing:photoClosing}" role="menu">
          <button class="photo-choice" @tap.stop="selectScenicSource(0)">{{ $t('拍照识景') }}</button>
          <button class="photo-choice" @tap.stop="selectScenicSource(1)">{{ $t('从相册选择') }}</button>
        </view>
      </view>
      <view class="voice-btn" :class="{ active: voiceMode }" @tap="toggleVoiceMode">
        <text class="iconfont" :class="voiceMode ? 'icon-liaotian' : 'icon-yuyin'"></text>
      </view>
      <textarea v-if="!voiceMode" v-model="text" class="msg-input" :focus="textareaFocus" :placeholder="$t(chatMode==='guide'?'用中文或英文提问...':'描述你的游览需求...')" :maxlength="2000" confirm-type="send" :style="inputHeight?{height:inputHeight+'px'}:{}" @touchstart.prevent="onInputTouchStart" @input="onInputValue" @focus="onInputFocus" @blur="onInputBlur" @linechange="onInputLineChange" @keyboardheightchange="onInputKeyboardHeight" @confirm="sendText" :adjust-position="false" :cursor-spacing="0" :show-confirm-bar="false" :disabled="loading"></textarea>
      <view v-else class="voice-hold-btn" :class="{ pressing: voicePressing }" @touchstart.stop.prevent="startRecord" @touchmove.stop.prevent="blockTouch" @touchend.stop.prevent="stopRecord" @touchcancel.stop="cancelRecord" @contextmenu.prevent="">
        <text>{{ $t(transcribing ? $t("正在识别…") : voicePressing ? $t("正在录音，松开发送") : $t("按住说话")) }}</text>
      </view>
      <view v-if="!voiceMode" class="send-btn" :class="{ disabled: (!text.trim() && !pendingPhoto) || loading || recognizing }" @tap="sendText">
        <text>{{ $t("发送") }}</text>
      </view>
    </view>

    </view>

    <NocturneSelect v-if="showQASpots" ref="spotPicker" :title="$t('选择问答景点')" :options="qaOptions" :selected-index="qaSpots.findIndex(spot=>spot.spot_id===qaSpotId)" :anchor="spotAnchor" @change="selectQuestionSpot" @close="closeSpotPicker" />

    <view v-if="undoVisible" class="undo-notice" role="status" :style="keyboardHeight?{bottom:(keyboardHeight+84)+'px'}:null">
      <text>{{ $t(undoKind==='history'?'已清除历史记录':'已清空当前对话') }}</text>
      <button @tap="undoClear">{{ $t('撤销') }}</button>
    </view>
    <!-- 问答历史记录 -->
    <view v-if="showHistory" class="history-mask" @tap="closeHistory">
      <view class="history-panel" @tap.stop>
        <view class="hp-head">
          <text class="hp-title">{{ $t('问答历史') }}</text>
          <view class="hp-actions">
            <text class="hp-clear" @tap.stop="clearHistoryFromPanel">{{ $t('清除历史记录') }}</text>
            <view class="hp-close" @tap="closeHistory" :aria-label="$t('关闭')"><text class="iconfont icon-close" aria-hidden="true"></text></view>
          </view>
        </view>
        <view v-if="historyTranslationFailed && !historyTranslating" class="hp-translating" @tap="localizeHistory">{{ tourLanguage==='en' ? 'Translation unavailable — showing the original text. Tap to retry.' : '翻译暂不可用，已显示原文。点击重试' }}</view>
        <view class="hp-body">
          <view v-if="!historyPairs.length" class="hp-empty">{{ $t('还没有问答记录') }}</view>
          <view v-for="(pair, i) in historyPairs" :key="i" class="hp-item">
            <view class="hp-q"><text class="hp-tag">Q</text><text class="hp-qtext">{{ pair.q }}</text></view>
            <view v-if="pair.a" class="hp-a"><text class="hp-tag a">A</text><text class="hp-atext">{{ pair.a }}</text></view>
          </view>
        </view>
      </view>
    </view>
    <!-- #ifdef APP-PLUS -->
    <view v-if="nativeChatVoice" class="chat-voice-runtime" aria-hidden="true"><tour-xingyun :payload="chatVoicePayload" @state="onChatVoiceState" /></view>
    <!-- #endif -->
  </view>
</template>

<script>
import { localizeChatMessages, warmChatTranslations, getChatTranslationCache } from '../../common/chat-language.js'
import { BASE_URL, assetUrl, isBeijingCity } from '../../common/config.js'
import NocturneSelect from '../../components/NocturneSelect.vue'
import TourXingyun from '../../components/tour-xingyun.vue'
import { planningMessage, recommendationText, questionLanguage, findQuestionSpot, photoIdentificationText } from '../../common/planning-language.js'
import { translateTour, LANGUAGE_STORAGE_KEY } from '../../common/tour-language.js'



function uiToast(options){uni.showToast({...options,title:translateTour(options.title,uni.getStorageSync(LANGUAGE_STORAGE_KEY)==='en'?'en':'zh')})}

function request(options) {
  return new Promise(function (resolve, reject) {
    var url = options.url
    if (url.indexOf('http') !== 0) url = BASE_URL + url
    const token=uni.getStorageSync('token')
    const header={'Content-Type':'application/json'}
    if(token)header.Authorization='Bearer '+token
    var match = options.url.match(/\/tour-session\/(?:start|end|live-info|detail|analyze|quiz|next-spot)\/(\d+)/) || options.url.match(/[?&]session_id=(\d+)/)
    var sid = options.data && options.data.sessionId || (match && match[1])
    var access = sid && uni.getStorageSync('xingyun-tour-' + sid)
    if (access) header['X-Tour-Access'] = access
    uni.request({
      url: url, method: options.method || 'GET',
      data: options.data || {}, header,
      timeout: options.timeout || 20000,
      success: function (res) {
        if(res.statusCode===401){if(uni.getStorageSync('token')===token){uni.removeStorageSync('token');uni.reLaunch({url:'/pages/auth/auth'})}reject(new Error('登录已过期，请重新输入账号密码'));return}
        if(res.statusCode===200)resolve({data:res.data})
        else reject(new Error(res.data&&(res.data.detail||res.data.message)||'服务请求失败（HTTP '+res.statusCode+'）'))
      },
      fail: function (err) { reject(err) },
    })
  })
}

export default {
  components:{NocturneSelect,TourXingyun},
  data: function () {
    return {
      chatMode:'guide',qaSpots:[],qaGuides:[],qaSpotId:null,spotAnchor:null,qaSession:null,qaCatalogLoading:false,catalogError:'',showQASpots:false,requestEpoch:0,historyOwner:null,applyingRoute:false,
      keyboardVisible:false,keyboardHeight:0,recognizing:false,pendingPhoto:'',recognitionError:'',showPhotoChoices:false,photoClosing:false,scrollAnim:false,
      undoVisible:false,undoKind:'',showHistory:false, historyTranslating:false, historyTranslationFailed:false, text: '', msgs: [], historyMsgs: [], loading: false, chatScrollTop:0, followBottom:true, chatViewH:0, tabLeaving:false, lastSpotIds: [], recommendSpots: [], recommendLoading: false,recommendedPlan:null,
      nativeChatVoice:false,chatVoicePayload:{},
      voiceError:'',transcribing:false,voiceMode: false, recording: false, voicePressing: false, speaking: false, speakingIndex:-1,ttsLoading:false,ttsPaused:false,
      recordingText: '正在聆听...', _voiceManager: null, _voiceTimer: null, _ws: null, statusH:20, inputHeight:0, textareaFocus:false,
    }
  },
  mounted:function(){this.statusH=(uni.getSystemInfoSync().statusBarHeight||20)+6;this.$nextTick(()=>{uni.createSelectorQuery().in(this).select('.chat-area').boundingClientRect(rect=>{if(rect&&rect.height)this.chatViewH=rect.height}).exec()});setTimeout(()=>{this.tabLeaving=true},160)},
  onReady:function(){this._welcomeReady=true;if(this.historyOwner!==this.storageOwner())this.loadHistory();this.warmHistory();if(this.chatMode==='guide')this.loadWelcomeCatalog()},
  watch:{
    tourLanguage:function(){this.stopTTS();this.stopReveal();this.msgs.forEach(m=>{if(m.segments){m.segments=undefined;m.cursor=false}});this.localizeHistory()},
    'msgs.length':function(){this.localizeHistory();this.warmHistory()},
    pendingPhoto:function(){this.scrollChat()},
    recognitionError:function(){this.scrollChat()},
    loading:function(){this.scrollChat();this.warmHistory()},
  },
  onLoad:function(){
    // #ifdef APP-PLUS
    this.nativeChatVoice=true
    // #endif
    this._keyboardListener=event=>this.updateKeyboardHeight(event.height)
    if(uni.onKeyboardHeightChange)uni.onKeyboardHeightChange(this._keyboardListener)
  },
  onUnload:function(){
    this.dismissUndo()
    this._translationDisposed=true;this.requestEpoch++;this._translationVersion=(this._translationVersion||0)+1
    if(uni.offKeyboardHeightChange&&this._keyboardListener)uni.offKeyboardHeightChange(this._keyboardListener)
    this.cancelRecord()
    this.stopTTS()
    this.stopReveal()
  },
  computed: {
    historyPairs:function(){
      var self=this,out=[],cur=null
      this.historyMsgs.forEach(function(m){
        var text=m.content||''
        if(m.image&&!text)text=self.$t('照片')
        if(!text)return
        if(m.role==='user'){cur={q:text,a:''};out.push(cur)}
        else if(m.role==='ai'){if(cur&&!cur.a){cur.a=text}else{out.push({q:'',a:text})}}
      })
      return out.slice().reverse()
    },
    qaOptions:function(){return this.qaSpots.map(spot=>this.$t(spot.spot_name))},
    guideSpotName:function(){const spot=this.qaSpots.find(item=>item.spot_id===this.qaSpotId);return spot?spot.spot_name:''},
    totalDuration: function () {
      if(!this.recommendedPlan)return null
      const minutes=this.recommendedPlan.estimated_time_minutes ?? this.recommendedPlan.total_duration
      return minutes!=null&&Number.isFinite(Number(minutes))&&Number(minutes)>=0?Number(minutes):null
    },
  },
  methods: {
    loadWelcomeCatalog:async function(){
      const epoch=this.requestEpoch,owner=this.storageOwner();this.catalogError=''
      try{await this.loadQACatalog()}catch(_){if(this.isCurrentRequest(epoch,owner))this.catalogError='景点加载失败，请检查网络后重试'}
    },

    goBack:function(){
      const stack=(typeof getCurrentPages==='function')?getCurrentPages():[]
      if(stack&&stack.length>1){uni.navigateBack({delta:1});return}
      uni.$emit('tabs:select','tour')
    },
    openHistory:function(){this.showHistory=true;this.localizeHistory()},
    closeHistory:function(){this.showHistory=false},
    dismissUndo:function(){clearTimeout(this._undoTimer);this._undoSnapshot=null;this.undoVisible=false},
    rememberClear:function(kind,retained){
      this.dismissUndo()
      this._undoSnapshot={owner:this.storageOwner(),expiresAt:Date.now()+8000,kind,retained:retained||[],
        history:this.historyMsgs.slice(),msgs:this.msgs.slice(),text:this.text,qaSession:this.qaSession,qaSpotId:this.qaSpotId,chatMode:this.chatMode,
        recommendedPlan:this.recommendedPlan,lastSpotIds:this.lastSpotIds.slice(),recommendSpots:this.recommendSpots.slice(),
        routeIds:uni.getStorageSync('ai_spot_ids'),routePlan:uni.getStorageSync('ai_route_plan')}
      this.undoKind=kind;this.undoVisible=true;this._undoTimer=setTimeout(()=>this.dismissUndo(),8000)
      this._undoTimer?.unref?.()
    },
    undoClear:function(){
      const saved=this._undoSnapshot
      if(!saved||saved.owner!==this.storageOwner()||Date.now()>saved.expiresAt){this.dismissUndo();return}
      // Only the question explicitly retained during deletion is de-duplicated. Repeated new questions remain separate.
      const retained=saved.retained.map(m=>JSON.stringify([m.role,m.content,m.image]))
      const appended=this.historyMsgs.filter(m=>{const i=retained.indexOf(JSON.stringify([m.role,m.content,m.image]));if(i<0)return true;retained.splice(i,1);return false})
      this.historyMsgs=saved.history.concat(appended)
      if(saved.kind==='chat'&&!this.msgs.length&&!this.text.trim()&&!this.pendingPhoto&&!this.loading&&!this.recognizing&&!this.transcribing){
        this.msgs=saved.msgs;this.text=saved.text;this.qaSession=saved.qaSession;this.qaSpotId=saved.qaSpotId;this.chatMode=saved.chatMode
        this.recommendedPlan=saved.recommendedPlan;this.lastSpotIds=saved.lastSpotIds;this.recommendSpots=saved.recommendSpots
        for(const [key,value] of [['ai_spot_ids',saved.routeIds],['ai_route_plan',saved.routePlan]]){if(value)uni.setStorageSync(key,value);else uni.removeStorageSync(key)}
      }
      this.dismissUndo();this.saveHistory();this.localizeHistory();this.scrollChat()
    },
    clearHistoryFromPanel:function(){
      // 历史清理不重置当前聊天、请求版本、语音或数字人会话。
      const pending=this.loading?this.msgs.slice().reverse().find(m=>m.role==='user'):null
      this.rememberClear('history',pending?[pending]:[])
      this.historyMsgs=pending?[{...pending}]:[]
      this.historyTranslationFailed=false
      this.saveHistory()
      this.showHistory=false
    },
    pushMsg:function(msg){this.msgs.push(msg);this.historyMsgs.push(msg);this.saveHistory()},
    splitReveal:function(text){
      const out=[];let buf=''
      const flush=()=>{if(buf){out.push(buf);buf=''}}
      const chars=Array.from(String(text||''))
      const cjk=/[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]/
      let cjkCount=0
      for(let i=0;i<chars.length;i++){
        const c=chars[i]
        if(c==='\n'){buf+=c;flush();cjkCount=0;continue}
        if(cjk.test(c)){buf+=c;cjkCount++;if(cjkCount>=3){flush();cjkCount=0}continue}
        cjkCount=0
        if(c===' '){buf+=c;flush();continue}
        buf+=c
        if(/[.,!?;:，。！？；：、）)]/.test(c))flush()
      }
      flush()
      return out
    },
    stopReveal:function(){this._revealEpoch=(this._revealEpoch||0)+1;clearTimeout(this._revealTimer);this._revealTimer=null},
    pushAIReply:function(content,extra){
      if(!content)return null
      const index=this.msgs.length
      const reply={role:'ai',content:content,segments:[],cursor:true}
      if(extra)Object.assign(reply,extra)
      this.msgs.push(reply)
      this.historyMsgs.push({role:'ai',content:content,image:extra&&extra.image||undefined})
      this.saveHistory()
      this.startReveal(reply,index,!(extra&&extra.silent))
      return reply
    },
    startReveal:function(msg,index,speak){
      this.stopReveal()
      if(speak&&msg.content)this.prefetchTTS(msg.content,index)
      const chunks=this.splitReveal(msg.content)
      const epoch=this._revealEpoch
      let i=0
      const step=()=>{
        if(epoch!==this._revealEpoch)return
        if(i>=chunks.length){
          msg.cursor=false;this._revealTimer=null
          if(speak&&msg.content)this.playTTS(msg.content,index)
          this.jumpBottom()
          return
        }
        msg.segments.push({t:chunks.slice(i,i+4).join('')})
        i+=4
        this._revealTimer=setTimeout(step,16)
        this.jumpBottomThrottled()
      }
      step()
    },
    jumpBottomThrottled:function(){
      if(!this.followBottom)return
      const now=Date.now()
      if(now-(this._softScrollAt||0)<140)return
      this._softScrollAt=now
      this.scrollAnim=false
      this.chatScrollTop+=100000
    },
    jumpBottom:function(){
      this.followBottom=true
      this.scrollAnim=true
      this.chatScrollTop+=100000
      clearTimeout(this._jumpTimer)
      this._jumpTimer=setTimeout(()=>{this.scrollAnim=false},320)
    },
    onChatScroll:function(event){
      const d=(event&&event.detail)||{}
      if(typeof d.scrollHeight!=='number')return
      const viewH=this.chatViewH||uni.getSystemInfoSync().windowHeight*0.6
      const gap=d.scrollHeight-d.scrollTop-viewH
      if(gap>160){this.followBottom=false}
      else if(gap<80){this.followBottom=true}
    },
    storageOwner:function(){const id=uni.getStorageSync('user_id');return id?'id:'+id:uni.getStorageSync('username')?'name:'+uni.getStorageSync('username'):'guest'},
    historyKey:function(){return 'ai_chat_state:'+encodeURIComponent(this.storageOwner())},
    // 历史问答按当前界面语言自动转换；接口失败时保留原文。
    guessHistoryLanguage:function(text){
      const value=String(text||'')
      const cjk=(value.match(/[\u4e00-\u9fff]/g)||[]).length
      const latin=(value.match(/[A-Za-z]/g)||[]).length
      if(latin>=5&&latin>=cjk*2)return 'en'
      if(cjk>0)return 'zh'
      return latin>0?'en':''
    },
    localizeHistory:async function(){
      const version=this._translationVersion=(this._translationVersion||0)+1
      const owner=this.storageOwner(),target=this.tourLanguage==='en'?'en':'zh'
      const active=this.msgs,history=this.historyMsgs
      const current=()=>this._translationVersion===version&&this.storageOwner()===owner&&this.tourLanguage===target&&this.msgs===active&&this.historyMsgs===history
      this.historyTranslating=true;this.historyTranslationFailed=false
      this._messageTranslations=getChatTranslationCache(owner)
      try{
        await localizeChatMessages({lists:[active,history],field:'content',target,cache:this._messageTranslations,isCurrent:current,
          translate:async texts=>{const res=await request({url:'/tour-session/translate-texts',method:'POST',timeout:45000,data:{texts,target}});return res.data?.data?.translations}})
        if(current())this.saveHistory()
      }catch(_){if(current())this.historyTranslationFailed=true}
      finally{if(this._translationVersion===version)this.historyTranslating=false}
    },
    warmHistory:function(){
      const owner=this.storageOwner(),cache=getChatTranslationCache(owner)
      if(!this.msgs.length&&!this.historyMsgs.length)return Promise.resolve()
      return warmChatTranslations({lists:[this.msgs,this.historyMsgs],field:'content',cache,
        isCurrent:()=>this.storageOwner()===owner&&!this._translationDisposed,
        translate:async(texts,target)=>{const res=await request({url:'/tour-session/translate-texts',method:'POST',timeout:45000,data:{texts,target}});return res.data?.data?.translations}
      }).then(()=>{if(this.storageOwner()===owner&&!this._translationDisposed)this.saveHistory()}).catch(()=>{})
    },
    isCurrentRequest:function(epoch,owner){return this.requestEpoch===epoch&&this.storageOwner()===owner},
    loadQACatalog:async function(){
      if(this.qaSpots.length&&this.qaGuides.length)return
      const epoch=this.requestEpoch,owner=this.storageOwner()
      if(this._catalogRequest&&this._catalogEpoch===epoch&&this._catalogOwner===owner)return this._catalogRequest
      this.qaCatalogLoading=true;this._catalogEpoch=epoch;this._catalogOwner=owner
      const pending=Promise.all([request({url:'/tour-session/spots'}),request({url:'/tour-session/guides'})]).then(([spots,guides])=>{
        if(!this.isCurrentRequest(epoch,owner))return
        this.qaSpots=spots.data?.data?.spot_list||[]
        this.qaGuides=guides.data?.data?.guide_list||[]
      }).finally(()=>{if(this.isCurrentRequest(epoch,owner))this.qaCatalogLoading=false;if(this._catalogRequest===pending)this._catalogRequest=null})
      this._catalogRequest=pending;return pending
    },
    selectQuestionSpot:function(event){
      this.qaSpotId=this.qaSpots[Number(event.detail.value)]?.spot_id||null
      this.saveHistory()
      this._pendingGuideKind=''
      if(this.$refs.spotPicker)this.$refs.spotPicker.requestClose()
      else this.showQASpots=false
    },
    pickSpot:function(){
      this.loadWelcomeCatalog()
      const self=this
      const open=function(){self.showQASpots=true}
      try{
        uni.createSelectorQuery().in(this).select('.qh-spot').boundingClientRect(function(r){
          if(r)self.spotAnchor={x:r.left+r.width/2,y:r.top+r.height/2}
          open()
        }).exec()
      }catch(e){open()}
    },
    closeSpotPicker:function(){this.showQASpots=false;this._pendingGuideKind=''},
    askGuide:function(kind){
      this._pendingGuideKind=kind
      if(this.qaSpotId&&this.guideSpotName){this.sendGuideKind(kind);return}
      this.pickSpot()
    },
    sendGuideKind:function(kind){
      const name=this.guideSpotName
      if(!name)return
      const spot=this.$t(name)
      const msg=kind==='story'?this.$t('「{spot}」有什么历史故事？',{spot}):kind==='photo'?this.$t('「{spot}」有什么拍照建议？',{spot}):this.$t('介绍「{spot}」',{spot})
      this.text=msg
      this.sendText()
    },
    sendGuideQuestion:async function(message,language,epoch,owner,contextSpotId){
      await this.loadQACatalog()
      if(!this.isCurrentRequest(epoch,owner))return null
      const spot=contextSpotId!=null?this.qaSpots.find(item=>item.spot_id===contextSpotId):findQuestionSpot(message,this.qaSpots,this.qaSpotId)
      if(!spot){
        if(contextSpotId!=null)throw new Error('识别到的景点已不可用，请重新选择')
        this.msgs.pop();this.text=message;this.showQASpots=!!this.qaSpots.length
        uiToast({title:this.qaSpots.length?'请先选择问答景点':'暂无可用景点',icon:'none'});return null
      }
      this.qaSpotId=spot.spot_id
      const guide=this.qaGuides.find(item=>item.guide_id>0&&item.is_enabled!==false)
      if(!guide)throw new Error('暂无可用数字导游，请稍后重试')
      const create=async()=>{
        const res=await request({url:'/tour-session/visitor-create?name='+encodeURIComponent(this.$t('景点问答'))+'&guide_id='+guide.guide_id+'&spot_ids='+encodeURIComponent(JSON.stringify([spot.spot_id])),method:'POST'})
        if(!res.data?.success||!res.data?.data?.session_id)throw new Error(res.data?.message||'问答会话创建失败')
        if(!this.isCurrentRequest(epoch,owner))return null
        if(res.data.data.avatar_access_token)uni.setStorageSync('xingyun-tour-'+res.data.data.session_id,res.data.data.avatar_access_token)
        this.qaSession={session_id:res.data.data.session_id,guide_id:guide.guide_id};this.saveHistory();return this.qaSession
      }
      let session=this.qaSession
      if(!session||session.guide_id!==guide.guide_id)session=await create()
      if(!session||!this.isCurrentRequest(epoch,owner))return null
      const ask=()=>request({url:'/tour-session/chat',method:'PUT',timeout:120000,data:{sessionId:session.session_id,message,currentSpotId:spot.spot_id,nextSpotId:null,language,text_only:true}})
      let result=await ask()
      if(!this.isCurrentRequest(epoch,owner))return null
      if(!result.data?.success&&/会话不存在|导览已结束/.test(result.data?.message||'')){
        session=await create();if(!session)return null;result=await ask()
      }
      if(!this.isCurrentRequest(epoch,owner))return null
      if(!result.data?.success||!result.data?.data?.message)throw new Error(result.data?.message||'问答服务暂不可用，请稍后重试')
      return result.data.data.message
    },
    // 键盘高度只改布局底部间距（margin），不做 transform / pageScrollTo：
    // 这样输入框在布局上就位于键盘上方，系统不会再为了露出焦点把整页往上推。
    // 系统可能在 keyboardheightchange 之前就决定上移页面，所以聚焦时先按上次的键盘高度
    // （首次使用按屏高估算）预留空间，再用真实高度校正。
    kbEstimate:function(){
      var h=0
      try{h=Number(uni.getStorageSync('app-keyboard-height'))||0}catch(e){h=0}
      if(!h){var s=uni.getSystemInfoSync();h=Math.round((s.windowHeight||s.screenHeight||700)*0.42)}
      return h
    },
    updateKeyboardHeight:function(height){
      var h=Math.max(0,Number(height)||0)
      if(h>0){this._kbSeen=true;clearTimeout(this._kbFocusTimer);try{uni.setStorageSync('app-keyboard-height',h)}catch(e){}}
      else this.textareaFocus=false
      this.keyboardHeight=h;this.keyboardVisible=h>0;this.scrollChat()
    },
    // 触摸按下就先预留键盘空间（早于 focus 和键盘弹出），避免系统抢先把页面往上推。
    onInputTouchStart:function(){
      // 置焦点保证一次点击就弹键盘；同时用内边距把输入行抬到预估键盘高度（防系统平移整页）。
      // 输入栏背景会填满下方区域，键盘升起时把它盖住，不会露出页面底部。
      // 键盘被系统关掉时 focus 可能仍为 true，需要先复位再置位，否则 focus 值没变化、键盘不会弹出。
      if(this.textareaFocus){var self=this;this.textareaFocus=false;this.$nextTick(function(){self.textareaFocus=true})}
      else this.textareaFocus=true
      if(this.keyboardHeight>0)return
      this._kbSeen=false
      this.keyboardHeight=this.kbEstimate()
      var self=this;clearTimeout(this._kbFocusTimer)
      this._kbFocusTimer=setTimeout(function(){if(!self._kbSeen)self.keyboardHeight=0},1600)
    },
    onInputFocus:function(){
      this.scrollChat();this.keyboardVisible=true
      if(this.keyboardHeight>0)return
      this.keyboardHeight=this.kbEstimate()
    },
    onInputBlur:function(){
      var self=this;this.textareaFocus=false
      clearTimeout(this._kbFocusTimer)
      setTimeout(function(){self.keyboardHeight=0;self.keyboardVisible=false;self.scrollChat()},150)
    },
    // 清空内容时立即还原单行高度，避免输入框一直停在多行高度。
    onInputValue:function(event){
      var value=event&&event.detail&&event.detail.value
      if((value===undefined||value===null||String(value).length===0)&&this.inputHeight)this.inputHeight=0
    },
    // textarea 自动增高：1 行基础高度，超过 4 行后固定为 4 行高度并在框内滚动。
    onInputLineChange:function(event){
      var lines=Math.max(1,Math.min(4,Number(event&&event.detail&&event.detail.lineCount)||1))
      var rpx=lines>1?(lines*39+40):0
      this.inputHeight=rpx?(uni.upx2px?uni.upx2px(rpx):Math.round(rpx/2)):0
    },
    onInputKeyboardHeight:function(event){this.updateKeyboardHeight(event.detail.height)},
    chooseScenicPhoto:function(){
      if(this.recognizing)return
      uni.hideKeyboard()
      this.recognitionError=''
      if(this.showPhotoChoices){this.closePhotoChoices();return}
      this.photoClosing=false
      this.showPhotoChoices=true
    },
    closePhotoChoices:function(){
      if(!this.showPhotoChoices||this.photoClosing)return
      this.photoClosing=true
      clearTimeout(this._photoCloseTimer)
      this._photoCloseTimer=setTimeout(()=>{this.showPhotoChoices=false;this.photoClosing=false},190)
    },
    selectScenicSource:function(index){
      const source=Number(index)===0?'camera':'album'
      this.closePhotoChoices()
      setTimeout(()=>{this.openScenicSource(source)},200)
    },
    openScenicSource:function(source){
      const epoch=this.requestEpoch,owner=this.storageOwner()
      // #ifdef APP-PLUS
      if(plus.os.name==='Android'){
        try{
          const Version=plus.android.importClass('android.os.Build$VERSION')
          const activity=plus.android.runtimeMainActivity()
          const appInfo=activity.getApplicationInfo()
          plus.android.importClass(appInfo)
          const mediaPermission=Number(Version.SDK_INT)>=33&&Number(appInfo.targetSdkVersion)>=33?'android.permission.READ_MEDIA_IMAGES':'android.permission.READ_EXTERNAL_STORAGE'
          const permission=source==='camera'?'android.permission.CAMERA':mediaPermission
          plus.android.requestPermissions([permission],result=>{
            if(result.deniedAlways&&result.deniedAlways.length){this.recognitionError='权限已被关闭，请到手机设置 → 应用设置 → HBuilder（或智游知境）→ 权限管理，允许'+(source==='camera'?'相机':'照片与视频／存储')+'权限';return}
            if(result.deniedPresent&&result.deniedPresent.length){this.recognitionError='需要允许'+(source==='camera'?'相机':'相册读取')+'权限才能选择照片';return}
            this.pickScenicImage(source,epoch,owner)
          },e=>{this.recognitionError='申请权限失败，请到手机应用权限设置中开启';console.error('Photo permission failed',e)})
        }catch(e){this.recognitionError='无法检查图片权限，请到手机应用权限设置中开启';console.error('Photo permission check failed',e)}
        return
      }
      // #endif
      this.pickScenicImage(source,epoch,owner)
    },
    pickScenicImage:function(source,epoch=this.requestEpoch,owner=this.storageOwner()){
      uni.chooseImage({count:1,sizeType:['compressed'],sourceType:[source],
        success:res=>{if(this.isCurrentRequest(epoch,owner)&&res.tempFilePaths&&res.tempFilePaths[0]){this.pendingPhoto=res.tempFilePaths[0];this.recognitionError='';this.voiceMode=false}},
        fail:e=>{if(!this.isCurrentRequest(epoch,owner))return;console.error('Choose scenic photo failed',e);if(!/cancel/i.test(e.errMsg||''))this.recognitionError=(source==='camera'?'相机':'相册')+'打开失败：'+(e.errMsg||'请检查手机权限')}})
    },
    previewChatPhoto:function(path){uni.previewImage({urls:[path],current:path})},
    sendPhoto:async function(){
      if(this.loading||this.recognizing||!this.pendingPhoto)return
      const path=this.pendingPhoto,caption=this.text.trim()
      if(Array.from(caption).length>1000){uiToast({title:'照片附言请控制在1000字以内',icon:'none'});return}
      const language=questionLanguage(caption,this.tourLanguage)
      this.pendingPhoto='';this.text='';this.recognitionError=''
      this.qaSpotId=null;this.chatMode='guide'
      this.pushMsg({role:'user',image:path,content:caption})
      const epoch=++this.requestEpoch,owner=this.storageOwner()
      this.recognizing=true;this.loading=true;this.scrollChat();this.saveHistory()
      try{
        const r=await new Promise((resolve,reject)=>uni.uploadFile({url:BASE_URL+'/tour-session/recognize-spot',filePath:path,name:'file',timeout:90000,
          formData:{question:caption,language},header:{Authorization:'Bearer '+uni.getStorageSync('token')},success:resolve,fail:()=>reject(new Error('照片上传失败，请检查网络连接'))}))
        if(!this.isCurrentRequest(epoch,owner))return
        let d;try{d=JSON.parse(r.data)}catch(error){throw new Error('识景服务返回格式异常')}
        if(r.statusCode===401){uni.removeStorageSync('token');uni.reLaunch({url:'/pages/auth/auth'});return}
        if(r.statusCode!==200||!d.success||!d.data)throw new Error(typeof d.detail==='string'?d.detail:d.message||'识景失败，请稍后重试')
        const result=d.data,prefix=photoIdentificationText(result,language)
        let reply=prefix
        if(result.status==='candidate'&&Number.isInteger(result.spot_id)&&result.spot_id>0){
          try{
            const question=translateTour('介绍「{spot}」的历史、典故和看点。',language,{spot:result.spot_name||''})
            const answer=await this.sendGuideQuestion(question,language,epoch,owner,result.spot_id)
            if(answer)reply+='\n\n'+answer
          }catch(error){
            if(!this.isCurrentRequest(epoch,owner))return
            reply+='\n\n'+translateTour('已得到候选景点，但问答服务暂不可用。请稍后重试提问。',language)
            this.text=caption
          }
        }
        if(!this.isCurrentRequest(epoch,owner))return
        this.loading=false;this.pushAIReply(reply,{recognition_id:result.recognition_id,recognitionEvidence:result.evidence||'',silent:true})
      }catch(error){
        if(!this.isCurrentRequest(epoch,owner))return
        const translated=translateTour(error.message||'照片上传失败，请检查网络连接',language)
        this.pushMsg({role:'ai',content:language==='en'&&/[\u3400-\u9fff]/.test(translated)?translateTour('照片识别失败，请稍后重试或联系管理员。',language):translated})
        this.pendingPhoto=path;this.text=caption
      }finally{
        if(this.isCurrentRequest(epoch,owner)){this.recognizing=false;this.loading=false;this.scrollChat();this.saveHistory()}
      }
    },
    toggleEvidence:function(m){m.showEvidence=!m.showEvidence;this.scrollChat()},
    scrollChat:function(){
      const self=this
      self.scrollAnim=false
      self.$nextTick(()=>{self.chatScrollTop=self.msgs.length||self.loading?self.chatScrollTop+100000:0})
      clearTimeout(self._scrollAnimTimer)
      self._scrollAnimTimer=setTimeout(()=>{self.scrollAnim=true},260)
    },
    saveHistory:function(){
      try{uni.setStorageSync(this.historyKey(),JSON.stringify({messages:this.historyMsgs.slice(-200),mode:this.chatMode,session:this.qaSession,spotId:this.qaSpotId,plan:this.recommendedPlan}))}catch(e){}
    },
    loadHistory:function(){
      this.dismissUndo()
      this.requestEpoch++;this.historyOwner=this.storageOwner();this.loading=false;this.recognizing=false;this.qaCatalogLoading=false
      this.msgs=[];this.chatMode='guide';this.qaSession=null;this.qaSpotId=null;this.recommendedPlan=null;this.lastSpotIds=[];this.recommendSpots=[]
      uni.removeStorageSync('ai_chat_msgs') // Old shared history has no reliable account owner.
      try{
        const raw=uni.getStorageSync(this.historyKey()),state=raw?JSON.parse(raw):{}
        // 重新进入账号时页面清空，上一轮的问答只保留在右上角的问答历史里。
        this.historyMsgs=Array.isArray(state.messages)?state.messages.filter(item=>item&&['ai','user'].includes(item.role)&&typeof item.content==='string').slice(-200):[]
      }catch(e){this.historyMsgs=[];this.msgs=[]}
    },
    clearRoutePreview:function(){this.lastSpotIds=[];this.recommendSpots=[];this.recommendedPlan=null;this.recommendLoading=false;uni.removeStorageSync('ai_spot_ids');uni.removeStorageSync('ai_route_plan')},
    clearHistory:function(){
      this.rememberClear('chat')
      this.requestEpoch++;this.stopTTS();this.cancelRecord();this.loading=false;this.recognizing=false;this.transcribing=false;this.qaCatalogLoading=false
      this.msgs=[];this.historyMsgs=[];this.qaSession=null;this.text='';this.voiceError='';this.showPhotoChoices=false;this.showQASpots=false;this.pendingPhoto='';this.recognitionError='';this.applyingRoute=false;this.clearRoutePreview();this.saveHistory()
      this.chatScrollTop=0;this.followBottom=true
      uni.removeStorageSync('ai_chat_msgs')
    },
    fixImg: function (u) { if (!u) return ''; return assetUrl(u) },
    walkText: function (a, b) {
      const details=this.recommendedPlan&&this.recommendedPlan.score_details||[]
      const index=details.findIndex(item=>item.spot_id===b.spot_id)
      const leg=index>0&&details[index-1].spot_id===a.spot_id?details[index]:null
      if(!leg||leg.walk_from_previous_meters==null||leg.walk_from_previous_minutes==null)return this.$t('暂无步行数据')
      const meters=Number(leg.walk_from_previous_meters),minutes=Number(leg.walk_from_previous_minutes)
      if(!Number.isFinite(meters)||!Number.isFinite(minutes))return this.$t('暂无步行数据')
      return meters<1000?this.$t('{meters}米 / {minutes}分钟',{meters:Math.round(meters),minutes}):this.$t('{km}公里 / {minutes}分钟',{km:(meters/1000).toFixed(2),minutes})
    },
    fetchRecommendSpots: function (ids) {
      var self = this
      const epoch=this.requestEpoch,owner=this.storageOwner()
      self.recommendSpots = []
      self.recommendLoading = true
      request({ url: '/tour-session/spots' }).then(function (res) {
        if(!self.isCurrentRequest(epoch,owner))return
        var d = res.data
        var list = (d && d.data && d.data.spot_list) ? d.data.spot_list : (d && d.spot_list ? d.spot_list : [])
        list = list.filter(function(sp){ return isBeijingCity(sp.city) })
        var map = {}
        list.forEach(function (sp) { map[sp.spot_id] = sp })
        self.recommendSpots = ids.map(function (id) { return map[id] }).filter(Boolean)
      }).catch(function () { if(self.isCurrentRequest(epoch,owner))self.recommendSpots=[] }).finally(function () { if(self.isCurrentRequest(epoch,owner))self.recommendLoading=false })
    },
    goTab:function(p){uni.reLaunch({url:p})},
    quickSend: function (msg) { this.text = this.$t(msg); this.sendText() },
    sendText: async function () {
      if(this.pendingPhoto){this.sendPhoto();return}
      var self = this
      var msg = (self.text || '').trim()
      if (!msg || self.loading) return
      if(Array.from(msg).length>2000){uiToast({title:'请输入2000字以内的问题',icon:'none'});return}
      const epoch=++this.requestEpoch,owner=this.storageOwner()
      self.pushMsg({ role: 'user', content: msg })
      self.text = ''; self.inputHeight = 0; self.loading = true; self.scrollChat()
      self.saveHistory()
      var requestLanguage = questionLanguage(msg,self.tourLanguage)
      try{
      if(self.chatMode==='guide'){
        const reply=await self.sendGuideQuestion(msg,requestLanguage,epoch,owner)
        if(reply&&self.isCurrentRequest(epoch,owner)){self.loading=false;self.pushAIReply(reply)}
        return
      }
      self.clearRoutePreview()
      const res=await request({
        url: '/tour-session/ai-chat-recommend?message=' + encodeURIComponent(planningMessage(msg)) + '&language=' + requestLanguage,
        method: 'POST', data: {},
      })
        if(!self.isCurrentRequest(epoch,owner))return
        var d = res.data
        if (d && d.success && d.data) {
          var dd = d.data
          var reply = recommendationText(dd,requestLanguage)
          self.loading=false
          self.pushAIReply(reply)
          if (dd.spot_ids && dd.spot_ids.length) {
            self.recommendedPlan=dd
            self.lastSpotIds = dd.spot_ids
            self.fetchRecommendSpots(dd.spot_ids)
          }
        } else { self.pushMsg({ role: 'ai', content: self.$t(d && d.message || '没有找到匹配路线，请调整需求。') }) }
      }catch(error){
        if(self.isCurrentRequest(epoch,owner))self.pushMsg({role:'ai',content:self.$t(error.message||error.errMsg||'无法连接推荐服务，请检查网络。')})
      }finally{if(self.isCurrentRequest(epoch,owner)){self.loading=false;self.scrollChat();self.saveHistory()}}
    },
    applyRecommend: function () {
      if(!this.lastSpotIds.length||this.loading||this.applyingRoute)return
      this.applyingRoute=true
      const epoch=this.requestEpoch,owner=this.storageOwner(),self=this
      uni.setStorageSync('ai_spot_ids', JSON.stringify(this.lastSpotIds))
      if(this.recommendedPlan)uni.setStorageSync('ai_route_plan',JSON.stringify(this.recommendedPlan))
      uni.setStorageSync('ai_route_owner',this.storageOwner())
      uiToast({ title: '已选中' + this.lastSpotIds.length + '个景点', icon: 'success' })
      setTimeout(function () { if(self.isCurrentRequest(epoch,owner))uni.$emit('tabs:select','tour') }, 500)
    },
    blockTouch:function(){},
    toggleVoiceMode: function () { if(this.recording||this.transcribing)return;this.voiceMode = !this.voiceMode;this.textareaFocus=false;if(this.voiceMode)uni.hideKeyboard() },
    stopTTS:function(){
      if(this.nativeChatVoice){this.chatVoicePayload={command:'close',id:Date.now()};this._chatVoiceStarted=0;this._chatVoiceText='';this._chatVoiceOffset=0}
      this._ttsRequestId=(this._ttsRequestId||0)+1
      if(this._ttsAudio){this._ttsAudio.destroy();this._ttsAudio=null}
      this.speaking=false;this.ttsLoading=false;this.ttsPaused=false;this.speakingIndex=-1
    },
    isReplyPlaying:function(index){return this.speakingIndex===index&&!this.ttsPaused&&(this.speaking||this.ttsLoading)},
    replayTTS: function (text,index) {
      if(this.speakingIndex===index){
        if(this.ttsLoading){this.stopTTS();return}
        if(this.ttsPaused){this.resumeTTS(text,index);return}
        this.pauseTTS(text,index)
        return
      }
      this.playTTS(text,index)
    },
    // Keep the same audio object so resume preserves the actual playback position.
    pauseTTS: function () {
      if(this.nativeChatVoice){if(this._chatVoiceStarted)this._chatVoiceOffset=Math.min((this._chatVoiceText||'').length,(this._chatVoiceOffset||0)+(Date.now()-this._chatVoiceStarted)/1000*4);this._chatVoiceStarted=0;this.chatVoicePayload=Object.assign({},this.chatVoicePayload,{command:'stop',text:'',id:Date.now()})}
      this.ttsPaused=true;this.speaking=false
      try{this._ttsAudio&&this._ttsAudio.pause()}catch(e){}
    },
    resumeTTS: function () {
      this.ttsPaused=false
      if(this.nativeChatVoice){const text=(this._chatVoiceText||'').slice(Math.floor(this._chatVoiceOffset||0));if(text){this.ttsLoading=true;this.chatVoicePayload=Object.assign({},this.chatVoicePayload,{command:'speak',text,id:Date.now()})}else this.stopTTS();return}
      if(this._ttsAudio){try{this._ttsAudio.play();return}catch(e){this.stopTTS()}}
      // An in-flight request starts when ready; completed playback is never restarted here.
    },
    prefetchTTS:function(){return Promise.resolve('')},
    cleanTTS:function(text){return (text||'').replace(/\*\*/g,'').replace(/[\[\]]/g,'').replace(/[（）\(\)]/g,'，').replace(/\n+/g,'，').substring(0,2000)},
    playTTS: function (text,index) {
      if (!text) return
      this.stopTTS()
      var clean=this.cleanTTS(text)
      if(this.nativeChatVoice){this.playDigitalVoice(clean,index);return}
      this.playEdgeTTS(clean,index)
    },
    playDigitalVoice:async function(text,index){
      this.speakingIndex=index;this.ttsLoading=true
      const version=this._ttsRequestId,owner=uni.getStorageSync('token')
      try{
        const res=await request({url:'/xingyun/chat-voice'})
        if(version!==this._ttsRequestId||owner!==uni.getStorageSync('token'))return
        const config=res.data
        if(!config?.guide_id||!config.sdk_url)throw new Error('数字人语音服务未配置')
        this._chatVoiceText=text;this._chatVoiceOffset=0
        this.chatVoicePayload={command:this.ttsPaused?'connect':'speak',text:this.ttsPaused?'':text,id:Date.now(),gateway:BASE_URL+'/xingyun/session/'+config.guide_id+'?chat_speech=true&language='+questionLanguage(text,this.tourLanguage),sdkUrl:config.sdk_url,token:owner}
      }catch(error){if(version!==this._ttsRequestId)return;this.stopTTS();uiToast({title:error.message||'数字人语音连接失败',icon:'none'})}
    },
    onChatVoiceState:function(event){
      if(event.gateway&&event.gateway!==this.chatVoicePayload.gateway)return
      if(event.state==='playing'){if(this.ttsPaused)return;this._chatVoiceStarted=Date.now();this.ttsLoading=false;this.speaking=true}
      else if(event.state==='ended'){if(this.ttsPaused)return;this.stopTTS()}
      else if(event.state==='error'){this.stopTTS();uiToast({title:event.message||'数字人语音连接失败',icon:'none'})}
    },
    playEdgeTTS: function (clean,index) {
      if (!clean) return
      var self=this
      this.speakingIndex=index;this.ttsLoading=true
      var requestId=this._ttsRequestId
      request({url:'/tts/edge?text='+encodeURIComponent(clean)+'&language='+questionLanguage(clean,self.tourLanguage)}).then(function(res){
        if(!res.data||!res.data.success||!res.data.data)throw new Error('语音服务未返回音频')
        if(requestId!==self._ttsRequestId)return
        var url=res.data.data
        if (url.indexOf('http') !== 0) url = BASE_URL + url
        else url = assetUrl(url)
        var audio = uni.createInnerAudioContext()
        self._ttsAudio=audio
        audio.onPlay(function(){if(requestId!==self._ttsRequestId||self._ttsAudio!==audio)return;if(self.ttsPaused){audio.pause();return}self.ttsLoading=false;self.speaking=true})
        audio.onEnded(function(){if(requestId===self._ttsRequestId)self.stopTTS()})
        audio.onError(function(){if(requestId!==self._ttsRequestId)return;self.stopTTS();uiToast({title:'语音播放失败，请检查网络后重试',icon:'none'})})
        audio.src = url; self.ttsLoading=false; if(!self.ttsPaused)audio.play()
      }).catch(function (error) {if(requestId!==self._ttsRequestId)return;self.stopTTS();uiToast({title:error.message||'语音播报失败，请稍后重试',icon:'none'})})
    },

    // Record once per press; register callbacks only once per page instance.
    initRecorder:function(){
      if(this._voiceManager)return this._voiceManager
      var self=this,rm=uni.getRecorderManager()
      self._voiceManager=rm
      rm.onStart(function(){self._recordStartedAt=Date.now();if(!self.voicePressing)rm.stop()})
      rm.onStop(function(res){
        self.voicePressing=false;self.recording=false
        if(self._recordCancelled)return
        var duration=Number(res.duration)||((self._recordStartedAt||self._recordRequestedAt)?Date.now()-(self._recordStartedAt||self._recordRequestedAt):0)
        self._recordStartedAt=0;self._recordRequestedAt=0
        if(!res.tempFilePath||duration<500){uiToast({title:'请按住说话至少半秒',icon:'none'});return}
        self.transcribing=true
        const epoch=self.requestEpoch,owner=self.storageOwner()
        uni.uploadFile({url:BASE_URL+'/tour-session/asr-upload',filePath:res.tempFilePath,name:'file',timeout:120000,
          header:{Authorization:'Bearer '+uni.getStorageSync('token')},
          success:function(r){
            if(!self.isCurrentRequest(epoch,owner))return
            try{var d=JSON.parse(r.data)
              if(r.statusCode===200&&d.success&&d.data){self.transcribing=false;self.text=d.data;self.sendText();return}
              self.voiceError=d.message||d.detail||'语音识别服务返回错误'
            }catch(e){self.voiceError='语音识别返回格式异常'}
          },
          fail:function(){if(self.isCurrentRequest(epoch,owner))self.voiceError='语音上传失败，请检查网络连接'},
          complete:function(){if(self.isCurrentRequest(epoch,owner))self.transcribing=false}
        })
      })
      rm.onError(function(e){self.voicePressing=false;self.recording=false;self.voiceError='录音失败，请检查手机麦克风权限';uiToast({title:self.voiceError,icon:'none'});console.error('Recorder failed',e)})
      return rm
    },
    startRecord:function(){
      if(this.transcribing){uiToast({title:'正在识别上一段语音，请稍候',icon:'none'});return}
      if(this.loading){uiToast({title:'正在回答，请稍候再录音',icon:'none'});return}
      if(this.recording)return
      this.stopTTS()
      this.voiceError='';this._recordCancelled=false;this._recordStartedAt=0
      this._recordRequestedAt=Date.now()
      this.voicePressing=true;this.recording=true;this.recordingText='正在聆听...'
      try{this.initRecorder().start({duration:60000,sampleRate:16000,numberOfChannels:1,encodeBitRate:48000,format:'mp3'})}
      catch(e){this.voicePressing=false;this.recording=false;this.voiceError='无法启动录音，请检查麦克风权限'}
    },
    stopRecord:function(){this.voicePressing=false;if(this._voiceManager&&(this._recordStartedAt||this._recordRequestedAt))this._voiceManager.stop()},
    cancelRecord:function(){this._recordCancelled=true;this.voicePressing=false;this.recording=false;if(this._voiceManager&&(this._recordStartedAt||this._recordRequestedAt))this._voiceManager.stop()},
  },
  onBackPress:function(){if(this.showQASpots){this.showQASpots=false;return true}if(this.showPhotoChoices){this.showPhotoChoices=false;return true}},
  onHide:function(){this.cancelRecord();this.stopTTS();this.keyboardVisible=false;this.keyboardHeight=0;this.showPhotoChoices=false;this.showQASpots=false},
  onShow:function(){this._translationDisposed=false;if(this.historyOwner!==this.storageOwner())this.loadHistory();if(this.chatMode==='guide'&&this._welcomeReady)this.loadWelcomeCatalog();else if(this.chatMode==='guide'&&this.qaSpotId&&!this.qaSpots.length)this.loadWelcomeCatalog();this.scrollChat()},
}
</script>

<style scoped>
.undo-notice{position:fixed;z-index:9600;left:16px;right:16px;bottom:calc(84px + env(safe-area-inset-bottom));display:flex;align-items:center;justify-content:space-between;gap:12px;padding:6px 12px;border-radius:16px;background:var(--ng-surface);border:1px solid var(--ng-border);box-shadow:0 4px 18px rgba(30,41,59,.1);color:var(--ng-text);font-size:26rpx;line-height:1.5}.undo-notice button{margin:0;padding:0 12px;min-height:44px;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:var(--ng-accent-text);background:transparent;font-size:inherit}.undo-notice button::after{border:0}
.chat-translation{padding:16rpx;text-align:center;font-size:24rpx;color:var(--ng-secondary)}
.photo-evidence-toggle{margin:12rpx 0 0;padding:8rpx 0;background:transparent;color:#625a75;font-size:22rpx;line-height:1.5;text-align:left}.photo-evidence-toggle::after{border:0}.photo-evidence{display:block;margin-top:8rpx;font-size:23rpx;line-height:1.7;color:#625a75}
.photo-draft{display:flex;align-items:center;gap:20rpx;padding:16rpx 24rpx;flex-wrap:wrap;border-top:1rpx solid var(--ng-border)}
.draft-thumbnail{position:relative;width:112rpx;height:112rpx}.draft-thumbnail image{width:100%;height:100%;border-radius:12rpx}
.draft-remove{position:absolute;top:-10rpx;right:-10rpx;display:flex;align-items:center;justify-content:center;width:36rpx;height:36rpx;margin:0;padding:0;border-radius:50%;background:#625a75;color:#fff;font-size:28rpx;line-height:1}.draft-remove::after{border:0}
.draft-note{font-size:23rpx;color:#817994}.chat-photo{display:block;width:320rpx;max-width:100%;border-radius:14rpx;margin-bottom:10rpx}

.photo-entry{position:relative;padding:12rpx 24rpx;z-index:1}
.photo-entry-wrap{position:relative;flex-shrink:0;display:flex;align-items:center}
.photo-popover{position:absolute;left:0;bottom:calc(100% + 14rpx);width:296rpx;padding:8rpx;background:var(--ng-surface,#fff);border-radius:26rpx;box-shadow:0 20rpx 54rpx rgba(48,40,94,.2),0 2rpx 8rpx rgba(48,40,94,.08);z-index:1200;transform-origin:left bottom;animation:photoPopIn 340ms cubic-bezier(.18,1.35,.3,1) both;overflow:hidden}
.photo-choice{display:flex;align-items:center;width:100%;margin:0;padding:24rpx 26rpx;background:transparent;border-radius:18rpx;font-size:29rpx;line-height:1.4;color:#3f3a55;text-align:left;box-shadow:none}
.photo-choice::after{border:0}
.photo-choice:active{background:#f3effb}
.photo-choice + .photo-choice{border-top:1rpx solid var(--ng-border,#eee)}
.photo-popover-mask{position:fixed;inset:0;z-index:1200;background:rgba(20,24,40,.06);animation:photoMaskIn 180ms ease both}
.photo-popover-mask.closing{animation:photoMaskOut 190ms ease both}
@keyframes photoMaskOut{from{opacity:1}to{opacity:0}}
.photo-popover.closing{animation:photoPopOut 190ms cubic-bezier(.4,0,.75,.45) both;pointer-events:none}
@keyframes photoPopOut{0%{opacity:1;transform:translateY(0) scale(1)}100%{opacity:0;transform:translateY(20rpx) scale(.7)}}
@keyframes photoPopIn{0%{opacity:0;transform:translateY(26rpx) scale(.82)}55%{opacity:1;transform:translateY(-6rpx) scale(1.04)}100%{opacity:1;transform:translateY(0) scale(1)}}
@keyframes photoMaskIn{from{opacity:0}to{opacity:1}}
.photo-add{flex-shrink:0;display:flex;align-items:center;justify-content:center;width:84rpx;height:84rpx;margin:0;padding:0;line-height:1;font-family:Arial,sans-serif;font-size:52rpx;font-weight:400;color:#6840c2;background:#f1eaff;border-radius:50%}.photo-add::after{border:0}.photo-add[disabled]{opacity:.45}
.bottom-fixed.keyboard-open{padding-bottom:env(safe-area-inset-bottom,0px)}
.input-bar .msg-input{min-width:0}.input-bar .voice-btn{flex-shrink:0}
.photo-caption,.photo-error{display:block;font-size:23rpx;line-height:1.7;margin-top:10rpx;color:#817994}.photo-error{color:#9f3450}
.recognition-photo{display:block;width:100%;height:240rpx;margin-top:16rpx;border-radius:18rpx}
.recognition-result{margin-top:12rpx;padding:20rpx;background:#fff;border-radius:18rpx}.recognition-result text{display:block;margin-bottom:10rpx;font-size:26rpx;line-height:1.7}.recognition-result .recognition-title{font-size:30rpx;font-weight:600;color:#6840c2}
.voice-status{position:relative;padding:16rpx 24rpx;color:#9f3450;font-size:26rpx;line-height:1.7;background:#fff1f2}
.page.aurora-page { height:100vh; min-height:0; box-sizing:border-box; display:flex; flex-direction:column; background-color:var(--ng-surface); position:relative; overflow:hidden; padding-bottom:0!important; }
.ink-bg { position:absolute; inset:0; pointer-events:none; z-index:0; }
.page-bg{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0}
.ink-mountain { position:absolute; left:0; right:0; background:var(--ng-night); border-radius:50% 70% 0 0; opacity:0.03; }
.ink-mt-1 { bottom:30%; height:180rpx; transform:scaleX(1.3); }
.ink-mt-2 { bottom:35%; height:130rpx; opacity:0.02; transform:scaleX(1.5) translateX(-10%); }
.ink-circle { position:absolute; top:20%; right:-100rpx; width:360rpx; height:360rpx; border-radius:50%; border:1rpx solid rgba(99,102,241,0.25); }

.nav{position:relative;z-index:1;display:flex;align-items:center;justify-content:flex-end;padding:12rpx 24rpx;min-height:88rpx;box-sizing:border-box;flex-shrink:0}
.nav-actions{display:flex;align-items:center;gap:16rpx;margin-left:auto}
.nav-title { font-size:44rpx; font-weight:900; color:var(--ng-text); letter-spacing:8rpx; font-family:var(--app-font-family); }
.nav-back{display:flex;align-items:center;justify-content:center;width:108rpx;height:108rpx;margin:-22rpx 10rpx -22rpx -8rpx;border-radius:24rpx;background:transparent;border:0;box-shadow:none;color:var(--ng-text);font-size:60rpx;line-height:1;margin-right:auto}
.nav-back:active{opacity:.5}
.nav-back text{transform:translateY(-4rpx)}
.nav-back text{transform:translateY(-3rpx)}
.nav-clear{position:static;font-size:24rpx;color:var(--ng-secondary);padding:6rpx 14rpx;border-radius:8rpx;background:rgba(99,102,241,0.06)}
.nav-history{position:relative;flex-shrink:0;width:68rpx;height:68rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.82);border:1rpx solid var(--ng-border);box-shadow:0 4rpx 14rpx rgba(99,102,241,0.14)}
.hist-clock{font-size:22px;color:var(--ng-soft-blue-text)}


.history-mask{position:fixed!important;inset:0!important;z-index:9500!important;background:rgba(24,20,40,0.38);display:flex;align-items:center;justify-content:center;padding:0 24rpx}
.history-panel{width:86vw;max-width:660rpx;max-height:74vh;background:var(--ng-surface);border-radius:34rpx;box-shadow:0 30rpx 80rpx rgba(40,30,70,0.28);display:block;overflow:hidden;transform-origin:top right;animation:historyPop 180ms ease-out}
@keyframes historyPop{from{transform:translateY(8px);opacity:0}to{transform:translateY(0);opacity:1}}
.hp-head{display:flex;align-items:center;justify-content:space-between;padding:26rpx 28rpx 16rpx}
.hp-actions{display:flex;align-items:center;gap:14rpx}
.hp-clear{font-size:24rpx;color:var(--ng-secondary);padding:8rpx 18rpx;border-radius:12rpx;background:rgba(99,102,241,0.08)}
.hp-title{font-size:30rpx;font-weight:700;color:var(--ng-text)}
.hp-close{width:60rpx;height:60rpx;border-radius:16rpx;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.08);font-size:34rpx;line-height:1;color:var(--ng-secondary)}
.hp-body{max-height:calc(74vh - 110rpx);overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:auto;touch-action:pan-y;padding:0 24rpx 24rpx;box-sizing:border-box}
.hp-empty{padding:60rpx 0;text-align:center;color:var(--ng-secondary);font-size:26rpx}
.hp-translating{padding:4rpx 4rpx 14rpx;color:var(--ng-secondary);font-size:23rpx}
.hp-item{margin-top:18rpx;padding:18rpx;border-radius:20rpx;background:rgba(99,102,241,0.05);border:1rpx solid rgba(99,102,241,0.12)}
.hp-q{display:flex;gap:12rpx;align-items:flex-start}
.hp-a{display:flex;gap:12rpx;align-items:flex-start;margin-top:12rpx;padding-top:12rpx;border-top:1rpx dashed var(--ng-border)}
.hp-tag{flex-shrink:0;width:34rpx;height:34rpx;border-radius:10rpx;background:rgba(99,102,241,0.18);color:var(--ng-text);font-size:20rpx;font-weight:700;display:flex;align-items:center;justify-content:center}
.hp-tag.a{background:rgba(59,91,255,0.12);color:var(--ng-secondary)}
.hp-qtext,.hp-atext{font-size:24rpx;line-height:1.6;color:var(--ng-text);word-break:break-word}
.hp-atext{color:var(--ng-secondary)}

.quick-hints { position:relative; z-index:1; display:flex; flex-wrap:wrap; gap:10rpx; padding:2rpx 24rpx 14rpx; }
.qh-spot{display:flex;align-items:center;justify-content:space-between;width:100%;box-sizing:border-box;padding:12rpx 20rpx;margin-bottom:6rpx;border-radius:18rpx;background:rgba(255,255,255,.66);border:1rpx dashed rgba(108,76,228,.32)}
.qh-spot-label{font-size:23rpx;color:#5b527a}
.qh-spot-action{font-size:22rpx;color:#7c4dea}
.qh-chip { padding:12rpx 20rpx; border-radius:22rpx; background:rgba(99,102,241,0.12); border:1rpx solid rgba(99,102,241,0.25); font-size:22rpx; color:var(--ng-secondary); }
.qh-chip:active { background:rgba(99,102,241,0.18); }

.chat-area { position:relative; z-index:1; flex:1; height:100%; min-height:0; box-sizing:border-box; padding:16rpx 24rpx; }
.chat-empty { display:flex; flex-direction:column; align-items:center; justify-content:flex-start; min-height:0; padding-top:34rpx; }
.ce-icon { font-size:72rpx; margin-bottom:18rpx; display:inline-block; animation:bounceBall 2.4s ease-in-out infinite; }
@keyframes bounceBall { 0%,100%{transform:translateY(0)} 4%{transform:translateY(-36rpx)} 8%{transform:translateY(0)} 12%{transform:translateY(-24rpx)} 16%{transform:translateY(0)} 20%{transform:translateY(-14rpx)} 24%{transform:translateY(0)} 28%{transform:translateY(-6rpx)} 32%{transform:translateY(0)} }
.ce-title { font-size:32rpx; font-weight:800; color:var(--ng-text); margin-bottom:10rpx; }
.ce-sub { font-size:24rpx; color:var(--ng-secondary); }

.msg-row { margin-bottom:22rpx; display:flex; }
.msg-l { justify-content:flex-start; }
.msg-r { justify-content:flex-end; }
.msg-bubble { max-width:82%; padding:18rpx 24rpx; border-radius:18rpx; }
.msg-bubble.user { background:linear-gradient(135deg, rgba(99,102,241,0.18), rgba(99,102,241,0.18)); border-bottom-right-radius:6rpx; }
.msg-bubble.ai { background:var(--ng-surface); border:1rpx solid var(--ng-border); border-bottom-left-radius:6rpx; }
.msg-bubble.user .msg-text { color:var(--ng-text); }
.msg-bubble.ai .msg-text { color:var(--ng-text); }
.msg-text { font-size:28rpx; line-height:1.8; word-break:break-word; white-space:pre-wrap; }
.typing .msg-text { color:var(--ng-secondary); font-size:24rpx; }
.typing-dots{display:flex;align-items:center;gap:9rpx;height:34rpx;padding:2rpx 0}
.typing-dots .td{width:13rpx;height:13rpx;border-radius:50%;background:var(--ng-secondary,#8b84a3);opacity:.3;animation:tdBreath 1.15s ease-in-out infinite}
.typing-dots .td:nth-child(2){animation-delay:.16s}
.typing-dots .td:nth-child(3){animation-delay:.32s}
@keyframes tdBreath{0%,100%{opacity:.22;transform:scale(.85)}45%{opacity:1;transform:scale(1.15)}}
.msg-seg{animation:segIn 320ms cubic-bezier(.25,.8,.35,1) both}
@keyframes segIn{from{opacity:0;filter:blur(4px)}to{opacity:1;filter:blur(0)}}
.msg-caret{display:inline-block;width:3rpx;height:26rpx;margin-left:6rpx;border-radius:2rpx;background:var(--ng-accent-text,#6840c2);vertical-align:-4rpx;animation:caretBlink .92s steps(1,end) infinite}
@keyframes caretBlink{0%,49%{opacity:1}50%,100%{opacity:0}}
.msg-speaker{margin-top:16rpx;padding:6rpx 28rpx 6rpx 16rpx;display:flex;justify-content:flex-end;border-top:1rpx solid var(--ng-border)}
.msg-speaker .vm-pause{display:flex;align-items:center;gap:6rpx;padding:8rpx 10rpx;border-radius:20rpx;background:rgba(99,102,241,.12)}
.msg-speaker .vm-bar{width:7rpx;height:22rpx;border-radius:4rpx;background:#4f46e5;display:block}
.msg-speaker .vm-play{width:0;height:0;border-left:18rpx solid #4f46e5;border-top:11rpx solid transparent;border-bottom:11rpx solid transparent;margin-left:4rpx}
.msg-speaker.on{animation:spkPulse .6s ease-in-out infinite}
@keyframes spkPulse{0%,100%{opacity:1}50%{opacity:.4}}

.result-bar { position:relative; z-index:1; display:flex; align-items:center; justify-content:space-between; padding:14rpx 20rpx; margin:0 20rpx 8rpx; background:rgba(99,102,241,0.15); border:1rpx solid rgba(99,102,241,0.25); border-radius:14rpx; font-size:24rpx; color:var(--ng-text); font-weight:600; }
.rb-btn { padding:8rpx 20rpx; border-radius:20rpx; background:linear-gradient(135deg, rgba(99,102,241,0.18), rgba(99,102,241,0.18)); color:var(--ng-text); font-size:22rpx; font-weight:700; }

.recording-hint { position:absolute; left:0; right:0; bottom:100%; z-index:996; display:flex; align-items:flex-end; justify-content:center; padding:0 0 18rpx; background:transparent; pointer-events:none; }
.rh-wave { display:flex; gap:5rpx; align-items:flex-end; height:50rpx; }
.rh-bar { width:5rpx; min-height:10rpx; border-radius:3rpx; background:rgba(99,102,241,0.55); box-shadow:0 0 6rpx rgba(255,255,255,0.9); animation:waveAnim 0.6s ease-in-out infinite; }
@keyframes waveAnim { 0%,100% { transform:scaleY(1); } 50% { transform:scaleY(3); } }

.bottom-fixed{position:absolute;left:0;right:0;bottom:0;flex-shrink:0;z-index:998;display:flex;flex-direction:column;background:var(--ng-surface);backdrop-filter: none}
.bottom-fixed.photo-open{z-index:1300}.input-bar{display:flex;gap:12rpx;align-items:flex-end;padding:16rpx 18rpx 18rpx;background:var(--ng-surface);border-top:1rpx solid var(--ng-border);margin:0}
.voice-btn { width:84rpx; height:84rpx; border-radius:50%; display:flex; align-items:center; justify-content:center; background:rgba(99,102,241,0.15); font-size:32rpx; }
.voice-btn.active { background:var(--ng-glass-blue-bg); color:var(--ng-soft-blue-text); }
.msg-input { flex:1; height:88rpx; padding:0 24rpx; border:1rpx solid var(--ng-border); border-radius:44rpx; background:var(--ng-surface); font-size:28rpx; color:var(--ng-text); }
.voice-hold-btn { user-select:none; -webkit-user-select:none; -webkit-touch-callout:none; touch-action:none; flex:1; height:88rpx; display:flex; align-items:center; justify-content:center; border:1rpx dashed rgba(182,207,238,.9); border-radius:44rpx; background:var(--ng-glass-blue-bg); font-size:28rpx; color:var(--ng-soft-blue-text); font-weight:600; box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9); }
.voice-hold-btn.pressing { background:rgba(230,240,255,.85); color:var(--ng-soft-blue-text); border-style:solid; border-color:rgba(182,207,238,.9); }
.send-btn { height:88rpx; padding:0 32rpx; line-height:88rpx; border-radius:44rpx; background:linear-gradient(135deg, rgba(99,102,241,0.18), rgba(99,102,241,0.18)); color:var(--ng-text); font-size:28rpx; font-weight:700; }
.send-btn.disabled { opacity:0.35; }

.tb-root{background:transparent}
.tb-ink-line{height:1rpx;background:linear-gradient(90deg,transparent,rgba(99,102,241,0.12),transparent);margin:0 32rpx}
.tb-inner{display:flex;align-items:center;justify-content:space-around;padding:4rpx 8rpx}
.tb-item{display:flex;flex-direction:column;align-items:center;gap:4rpx;padding:2rpx 10rpx;position:relative;flex:1}
.tb-icon{font-size:38rpx}.tb-label{font-size:20rpx;font-weight:600;color:var(--ng-secondary)}
.tb-dot{position:absolute;bottom:-4rpx;width:24rpx;height:4rpx;border-radius:2rpx;background:rgba(99,102,241,0.18);opacity:.6}
.tb-item.on .tb-label{color:var(--ng-secondary);font-weight:600}.tb-item.on .tb-icon{transform:scale(1.1)}
.tb-hl-ring{width:68rpx;height:68rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.18);border:2rpx solid rgba(99,102,241,0.25);margin-bottom:-2rpx}
.tb-hl-ring.on{background:linear-gradient(135deg,rgba(99,102,241,0.18),rgba(99,102,241,0.18));border-color:transparent;box-shadow:0 6rpx 18rpx rgba(99,102,241,0.15);animation:tabBounce .4s ease-out}
.tb-hl-ring .tb-icon{font-size:34rpx}.tb-safe{height:env(safe-area-inset-bottom,10rpx);min-height:2rpx}
@keyframes tabBounce{0%{transform:scale(1)}30%{transform:scale(1.15)}60%{transform:scale(.95)}100%{transform:scale(1)}}

/* 路线预览时间轴 */
.route-preview { position:relative; z-index:1; flex-shrink:0; max-height:24vh; overflow-y:auto; box-sizing:border-box; margin:0 20rpx 8rpx; padding:18rpx 20rpx; background:var(--ng-surface); border:1rpx solid var(--ng-border); border-radius:16rpx; }
.rp-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:14rpx; }
.rp-title { font-size:28rpx; font-weight:800; color:var(--ng-text); letter-spacing:2rpx; }
.rp-count { font-size:22rpx; color:var(--ng-secondary); }
.rp-loading { padding:24rpx 0; text-align:center; font-size:24rpx; color:var(--ng-secondary); }
.rp-timeline { display:flex; flex-direction:column; }
.rp-item { display:flex; gap:14rpx; }
.rp-rail { display:flex; flex-direction:column; align-items:center; flex-shrink:0; }
.rp-dot { width:44rpx; height:44rpx; border-radius:50%; background:rgba(99,102,241,0.18); border:2rpx solid rgba(99,102,241,0.25); color:var(--ng-text); font-size:22rpx; font-weight:700; display:flex; align-items:center; justify-content:center; }
.rp-dot.start { background:linear-gradient(135deg, rgba(99,102,241,0.25), rgba(99,102,241,0.18)); }
.rp-dot.end { background:rgba(99,102,241,0.25); }
.rp-line { flex:1; width:2rpx; min-height:44rpx; background:linear-gradient(to bottom, rgba(99,102,241,0.25), rgba(99,102,241,0.12)); margin:6rpx 0; }
.rp-card { flex:1; display:flex; gap:14rpx; align-items:center; padding:6rpx 0 20rpx; }
.rp-img { width:88rpx; height:88rpx; border-radius:14rpx; flex-shrink:0; background:var(--ng-night); }
.rp-img-df { display:flex; align-items:center; justify-content:center; font-size:40rpx; opacity:.5; }
.rp-info { flex:1; display:flex; flex-direction:column; gap:6rpx; }
.rp-name { font-size:28rpx; font-weight:700; color:var(--ng-text); }
.rp-cat { font-size:22rpx; color:var(--ng-secondary); }
.rp-walk { font-size:20rpx; color:var(--ng-secondary); opacity:.85; }
.rp-total { display:flex; align-items:center; justify-content:space-between; margin-top:10rpx; padding-top:14rpx; border-top:1rpx dashed var(--ng-border); }
.rp-total-label { font-size:24rpx; color:var(--ng-secondary); font-weight:600; }
.rp-total-value { font-size:30rpx; font-weight:800; color:var(--ng-text); }

/* Reference layout: compact header, central welcome and soft landscape waves. */
.chat-ref-page{--app-font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;font-family:var(--app-font-family);color:#211653}
.chat-ref-page .chat-scenery{background:linear-gradient(145deg,#efedfc 0%,#f8f7ff 55%,#f2fbff 100%)!important}
.chat-scenery .chat-wave{position:absolute;opacity:1!important;pointer-events:none;animation:none!important}
.chat-wave-blue{left:-18%;bottom:140rpx;width:150%;height:560rpx;border-radius:65% 48% 0 0;transform:rotate(-15deg);background:linear-gradient(160deg,rgba(208,232,254,.1),rgba(207,235,254,.55))}
.chat-wave-lilac{left:-30%;bottom:-130rpx;width:170%;height:460rpx;border-radius:54% 60% 0 0;transform:rotate(13deg);background:linear-gradient(155deg,rgba(221,211,250,.58),rgba(223,236,255,.2))}
.chat-ref-page .nav{gap:14rpx;padding-left:26rpx;padding-right:26rpx;padding-bottom:20rpx;border-bottom:0!important}
.nav-back{width:64rpx;height:72rpx;margin:0;flex-shrink:0;font-size:64rpx;color:#302563}.nav-spacer{flex:1;min-width:0}
.nav-history{width:72rpx;min-width:72rpx;height:72rpx;border-radius:50%;border:0;background:var(--ng-glass-blue-bg);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)}
.hist-clock{font-size:22px;color:var(--ng-soft-blue-text)}
.nav .qh-spot{display:flex;align-items:center;gap:12rpx;width:auto;flex:0 1 auto;max-width:450rpx;min-width:0;margin:0;padding:12rpx 18rpx 12rpx 10rpx;min-height:72rpx;line-height:1.4;border:1rpx solid rgba(255,255,255,.76);border-radius:40rpx;background:rgba(255,255,255,.64);box-shadow:0 6rpx 24rpx rgba(115,91,185,.07);text-align:left;box-sizing:border-box}
.qh-spot::after{border:0}.context-pin{display:flex;align-items:center;justify-content:center;width:46rpx;height:46rpx;flex-shrink:0;border-radius:50%;background:var(--ng-glass-blue-bg);box-shadow:0 1rpx 2rpx rgba(70,105,170,.06),0 4rpx 8rpx -4rpx rgba(70,105,170,.12),inset 0 1rpx 0 rgba(255,255,255,.9)}.context-pin .iconfont{font-size:31rpx;color:var(--ng-soft-blue-text)}
.context-name{flex:1;min-width:0;font-size:25rpx;font-weight:500;color:#261956;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.nav-clear{flex-shrink:0;margin:0;padding:8rpx;font-size:23rpx;background:transparent}
.conversation-stage{position:relative;flex:1;min-height:0;overflow:hidden;padding-bottom:128rpx}.conversation-stage .chat-area{position:absolute;inset:0;width:100%;height:100%;padding:0 28rpx 24rpx}
.welcome-active :deep(.uni-scroll-view-content){display:flex;flex-direction:column;min-height:100%}
.guide-welcome{flex:0 0 auto;min-height:100%;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:160rpx 12rpx 120rpx;box-sizing:border-box}
.guide-welcome>view,.guide-welcome>text{flex-shrink:0}
.welcome-art{position:relative;width:240rpx;height:172rpx;flex-shrink:0;margin:0 0 34rpx;pointer-events:none}
.welcome-art-shadow{position:absolute;left:16rpx;right:8rpx;bottom:4rpx;height:28rpx;border-radius:50%;background:radial-gradient(ellipse,rgba(171,147,232,.12),rgba(194,176,245,0) 72%)}
.welcome-balloon{position:absolute;left:42rpx;top:24rpx;width:146rpx;height:96rpx;border-radius:36rpx;background:linear-gradient(135deg,#e1d8ff,#ac91ed);box-shadow:inset 4rpx 6rpx 16rpx rgba(255,255,255,.38),0 10rpx 28rpx rgba(162,130,225,.12);animation:welcomeFloat 4s ease-in-out infinite}
.welcome-balloon::after{content:'';position:absolute;left:22rpx;bottom:-20rpx;width:38rpx;height:32rpx;background:#c7b5f6;clip-path:polygon(0 0,100% 0,0 100%)}
.welcome-dots{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:13rpx}.welcome-dots>view{width:14rpx;height:14rpx;border-radius:50%;background:rgba(255,255,255,.94)}
.welcome-sparkle{position:absolute;line-height:1;color:#d3b2ed;animation:welcomeTwinkle 4s ease-in-out infinite}.welcome-sparkle-large{right:12rpx;top:0;font-size:54rpx}.welcome-sparkle-small{right:0;top:40rpx;font-size:29rpx;animation-delay:1s}
.welcome-title{display:block;text-align:center;font-size:43rpx;line-height:1.45;font-weight:700;letter-spacing:1rpx;color:#241552}
.welcome-description{display:block;max-width:100%;margin-top:14rpx;text-align:center;font-size:25rpx;line-height:1.7;color:#9a98ae}
.welcome-topics{display:flex;flex-wrap:wrap;align-items:stretch;gap:18rpx;width:100%;margin-top:48rpx}
.welcome-topic{position:relative;max-width:100%;min-width:0;min-height:88rpx;margin:0;padding:16rpx 22rpx;border:1rpx solid rgba(255,255,255,.95);border-radius:32rpx;background:rgba(255,255,255,.85);box-shadow:0 6rpx 20rpx rgba(116,85,196,.06),inset 0 2rpx 6rpx rgba(255,255,255,.85);display:flex;align-items:center;gap:14rpx;text-align:left;line-height:1.45;box-sizing:border-box}
.welcome-photo-row{width:100%;min-height:88rpx;flex-shrink:0;display:flex;justify-content:center}.welcome-topic-photo{justify-content:center;text-align:center}
.welcome-topic::after{border:0}.welcome-topic[disabled]{opacity:.55}.topic-icon-wrap{width:48rpx;height:48rpx;flex-shrink:0;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--ng-glass-blue-bg);box-shadow:0 1rpx 2rpx rgba(70,105,170,.06),0 4rpx 8rpx -4rpx rgba(70,105,170,.12),inset 0 1rpx 0 rgba(255,255,255,.9)}.topic-icon{font-size:31rpx;color:var(--ng-soft-blue-text)}.topic-title{min-width:0;font-size:26rpx;font-weight:500;color:#291b58;white-space:normal}
.welcome-loading,.welcome-unavailable{width:100%;margin-bottom:20rpx;padding:14rpx 20rpx;box-sizing:border-box;display:flex;align-items:center;justify-content:center;gap:16rpx;border-radius:20rpx;background:rgba(255,255,255,.6);color:#8b829d;font-size:23rpx;line-height:1.5;white-space:normal;text-align:center}
.welcome-unavailable button{flex-shrink:0;margin:0;padding:6rpx 18rpx;font-size:23rpx;line-height:1.7;border-radius:14rpx;color:#7961bc;background:#fff}
.chat-ref-page .bottom-fixed{border-radius:32rpx 32rpx 0 0;background:#fff;box-shadow:0 -6rpx 24rpx rgba(166,154,211,.04);padding-bottom:env(safe-area-inset-bottom,0px)}
.chat-ref-page .input-bar{gap:12rpx;padding:16rpx 18rpx 20rpx;border-top:0;border-radius:32rpx 32rpx 0 0;background:#fff}.photo-add,.voice-btn{width:82rpx;height:82rpx;flex-shrink:0;background:var(--ng-glass-blue-bg);color:var(--ng-soft-blue-text);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9)}.photo-add{font-size:47rpx}.voice-btn .iconfont{color:var(--ng-soft-blue-text)}
.input-bar .msg-input{height:82rpx;min-height:82rpx;padding:20rpx;line-height:1.5;font-family:inherit;font-size:26rpx;border:0;border-radius:22rpx;background:#f8f8fb;box-sizing:border-box;overflow-y:auto;max-height:360rpx}.chat-ref-page .input-bar .send-btn{height:82rpx;line-height:82rpx;padding:0 26rpx;font-size:27rpx;border-radius:24rpx;color:var(--ng-soft-blue-text);background:var(--ng-glass-blue-bg);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.92)}.send-btn.disabled{opacity:.7}.input-bar .voice-hold-btn{height:82rpx;border-radius:22rpx}
.app-english .welcome-title{font-size:40rpx;letter-spacing:0}.app-english .topic-title{font-size:24rpx}
/* 英文文案更长，三个快捷提问会各自换行；英文状态下整行居中，中文布局保持不变。 */
.app-english .welcome-topics{justify-content:center}
/* 英文里最短的是 "Introduce this place"，放到另外两个下面（只是排在其他两个之后，不贴页面底部）。 */
.app-english .welcome-topic-intro{order:3}
.app-english .welcome-topic-story{order:1}
.app-english .welcome-photo-row{order:2}
/* 键盘弹起时欢迎区完全保持原位：不贴顶、不隐藏气球和说明、不缩放标题、不改快捷提问间距，避免整块跳动或被导航裁切。 */
@keyframes welcomeFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-7rpx)}}
@keyframes welcomeTwinkle{0%,100%{opacity:.5;transform:scale(.9)}50%{opacity:1;transform:scale(1.06)}}
@media (prefers-reduced-motion:reduce){.welcome-balloon,.welcome-sparkle,.history-panel,.photo-popover{animation:none!important}}
@media (max-width:360px){.chat-ref-page .nav{gap:10rpx;padding-left:18rpx;padding-right:18rpx}.nav .qh-spot{max-width:370rpx;padding-right:14rpx;gap:8rpx}.context-name{font-size:24rpx}.welcome-title{font-size:40rpx}.guide-welcome{padding-left:4rpx;padding-right:4rpx;padding-bottom:80rpx}.welcome-topic{padding:14rpx 16rpx;gap:10rpx}.topic-title{font-size:25rpx}.chat-ref-page .input-bar{gap:8rpx;padding-left:14rpx;padding-right:14rpx}.photo-add,.voice-btn{width:76rpx;height:76rpx}.input-bar .msg-input,.input-bar .voice-hold-btn,.send-btn{height:76rpx;line-height:76rpx}.send-btn{padding:0 20rpx}}
</style>


<style scoped>
.chat-ref-page>.chat-voice-runtime{position:fixed!important;left:-1000px;top:0;width:240px;height:400px;pointer-events:none;opacity:0;overflow:hidden}
</style>
