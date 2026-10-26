<template>
  <view class="page aurora-page" :class="tabEnterClass">
    <!-- #ifdef APP-PLUS -->
    <view class="app-status-bar-shield" aria-hidden="true"></view>
    <!-- #endif -->
    <view class="aurora-background" aria-hidden="true"><view class="aurora-wave aurora-wave-one"></view><view class="aurora-wave aurora-wave-two"></view><view class="aurora-shine"></view></view>

    <view class="ink-bg">
      <view class="ink-mountain ink-mt-1"></view>
      <view class="ink-mountain ink-mt-2"></view>
    </view>

    <!-- 自定义导航栏（毛体标题） -->
    <view class="nav" :style="{paddingTop:statusH+'px'}">
      <!-- 扫码领取：扫描电脑网页上的路线二维码，直接领取网页上选好的路线 -->
      <view class="nav-scan" hover-class="nav-scan-press" :hover-stay-time="70" role="button" :aria-label="t('扫码')" @tap="scanRoute">
        <text class="scan-icon iconfont icon-scan" aria-hidden="true"></text>
        <text class="nav-scan-label">{{ t('扫码') }}</text>
      </view>
    </view>

    <!-- 头像卡片 -->
    <view class="profile-card">
      <view class="pc-avatar-wrap">
        <image v-if="avatarUrl" :src="avatarUrl" class="pc-avatar" mode="aspectFill" @error="avatarUrl=''"></image>
        <view v-else class="pc-avatar-df">
          <text class="pca-txt">{{ avatarText }}</text>
        </view>
      </view>
      <view class="pc-name-row">
        <text class="pc-name">{{ username || t('游客') }}</text>
      </view>
      <text class="pc-id">ID: {{ userId }}</text>
    </view>

    <!-- 菜单 -->
    <view class="menu-section">
      <view class="menu-group">
        <view class="menu-item" @tap="goHistory">
          <view class="mi-left"><text class="mi-icon iconfont icon-liulanjilu"></text><text class="mi-label">{{ t('游览记录') }}</text></view>
          <text class="mi-arrow iconfont icon-chevron-right" aria-hidden="true"></text>
        </view>

      </view>
      <view class="menu-group">
        <view class="menu-item language-menu-item">
          <view class="mi-left"><text class="mi-icon iconfont icon-pianhao"></text><text class="mi-label">{{ t('界面语言') }}</text></view>
          <view class="lang-switch" :class="{ en: tourLanguage === 'en' }" role="group" :aria-label="t('界面语言')">
            <view class="lang-thumb" aria-hidden="true"></view>
            <button class="lang-btn" :class="{active:tourLanguage==='zh'}" :aria-pressed="tourLanguage==='zh'" hover-class="lang-press" :hover-stay-time="70" @tap="setTourLanguage('zh')">中文</button>
            <button class="lang-btn" :class="{active:tourLanguage==='en'}" :aria-pressed="tourLanguage==='en'" hover-class="lang-press" :hover-stay-time="70" @tap="setTourLanguage('en')">English</button>
          </view>
        </view>
        <view class="menu-item" @tap="showAbout=true">
          <view class="mi-left"><text class="mi-icon iconfont icon-guanyuwomen"></text><text class="mi-label">{{ t('关于我们') }}</text></view>
          <text class="mi-arrow iconfont icon-chevron-right" aria-hidden="true"></text>
        </view>
      </view>
      <view class="menu-group">
        <view class="menu-item logout-item" @tap="handleLogout">
          <view class="mi-left"><text class="mi-icon iconfont icon-tuichu" style="color:var(--ng-secondary);"></text><text class="mi-label" style="color:var(--ng-secondary);">{{ t('退出登录') }}</text></view>
          <text class="mi-arrow iconfont icon-chevron-right" style="color:var(--ng-secondary);" aria-hidden="true"></text>
        </view>
      </view>
    </view>

    <!-- 关于我们：页面居中小弹窗（原先的底部抽屉会被底部标签栏挡住） -->
    <view class="about-overlay" v-if="showAbout" @touchstart.stop="" @touchmove.stop.prevent="" @touchend.stop="" @touchcancel.stop="" @tap="showAbout=false">
      <view class="about-dialog" @tap.stop="">
        <view class="about-close" hover-class="about-close-press" :hover-stay-time="70" @tap="showAbout=false"><text class="about-close-txt iconfont icon-close" aria-hidden="true"></text></view>
        <text class="about-title">{{ t('关于我们') }}</text>
        <text class="about-intro">{{ t('景区数字人导览与路线规划。') }}</text>
      </view>
    </view>

    <NocturneConfirm v-if="showLogout" plain :title="t('退出登录')" :content="t('确定要退出登录吗？')" :cancel-label="t('取消')" :confirm-label="t('确定')" @cancel="showLogout=false" @confirm="confirmLogout" />

    <!-- 退出登录：登录页从「退出登录」这一行弹性展开，再切到真实登录页，避免生硬换页 -->
    <view v-if="loginRevealOpen" class="login-reveal" :style="revealStyle" aria-hidden="true"><AuthPage /></view>
  </view>
</template>

<script>
import NocturneConfirm from '../../components/NocturneConfirm.vue'
import AuthPage from '../auth/auth.vue'
import { BASE_URL, assetUrl, isLocalStationOrigin } from '../../common/config.js'
import { CLAIM_ROUTE, clearPendingClaim, saveClaim } from '../../common/station-claim.js'
import { localizeChatMessages, warmChatTranslations, getChatTranslationCache } from '../../common/chat-language.js'
import { LANGUAGE_STORAGE_KEY, translateTour } from '../../common/tour-language.js'
export default {
  components:{NocturneConfirm,AuthPage},
  data: function () {
    return {
      // 与 pages/tour/tour.vue 共用同一个 storage key，切换后全 App 一致。

      username: '', userId: '', avatarUrl: '', statusH: 20,
      scanning: false,
      showAbout: false, showLogout: false, loginRevealOpen: false, revealOriginX: 206, revealOriginY: 640,
    }
  },
  computed: {
    revealStyle: function () { return { transformOrigin: this.revealOriginX + 'px ' + this.revealOriginY + 'px' } },
    avatarText: function () { var name = (this.username || '').trim(); return name ? name.charAt(0).toUpperCase() : '游' },
  },
  methods: {
    // 与网页端 LanguageSwitch 行为一致：切换界面语言并持久化，用户自填内容保持原样。
    setTourLanguage: function (language) {
      var next = language === 'en' ? 'en' : 'zh'
      var previous = this.tourLanguage
      this.tourLanguage = next
      uni.setStorageSync(LANGUAGE_STORAGE_KEY, next)
      if (previous !== next) this.translateAiChatHistory(next)
    },
    // 切换语言时，把本地保存的 AI 小导游问答一起转换成新语言。
    translateAiChatHistory:async function(target,background=false){
      const version=this._historyTranslationVersion=(this._historyTranslationVersion||0)+1
      const ownerId=uni.getStorageSync('user_id'),ownerName=uni.getStorageSync('username')
      const owner=ownerId?'id:'+ownerId:ownerName?'name:'+ownerName:'guest'
      const key='ai_chat_state:'+encodeURIComponent(owner),raw=uni.getStorageSync(key)
      if(!raw)return
      let state;try{state=typeof raw==='string'?JSON.parse(raw):raw}catch(_){return}
      if(!Array.isArray(state.messages))return
      const current=()=>{const id=uni.getStorageSync('user_id'),name=uni.getStorageSync('username');return (background||version===this._historyTranslationVersion)&&(id?'id:'+id:name?'name:'+name:'guest')===owner&&(background||this.tourLanguage===target)}
      const options={lists:[state.messages],field:'content',target,cache:getChatTranslationCache(owner),isCurrent:current,
        translate:(texts,language=target)=>new Promise((resolve,reject)=>uni.request({url:BASE_URL+'/tour-session/translate-texts',method:'POST',timeout:45000,
          header:{'Content-Type':'application/json',Authorization:'Bearer '+(uni.getStorageSync('token')||'')},data:{texts,target:language},
          success:res=>res.statusCode===200?resolve(res.data?.data?.translations):reject(new Error('Translation failed')),fail:reject}))}
      try{if(background)await warmChatTranslations(options);else await localizeChatMessages(options)
        if(current()&&uni.getStorageSync(key)===raw)uni.setStorageSync(key,JSON.stringify(state))
      }catch(_){}
    },
    // 只翻译界面文案；用户昵称等用户自填内容保持原样。
    t: function (value, params) {
      return translateTour(value, this.tourLanguage, params || {})
    },
    goTab:function(p){uni.reLaunch({url:p})},
    goHistory:function(){uni.navigateTo({url:'/pages/mine/history'})},
    // 扫码只打开路线确认页，由游客选择数字人后再创建导览。
    scanRoute: function () {
      if(this.scanning)return
      this.scanning=true
      uni.scanCode({onlyFromCamera:false,scanType:['qrCode'],
        success:result=>{
          let claim
          try{claim=saveClaim(result&&result.result)}
          catch(_){uni.showToast({title:this.t('请扫描网页上的路线领取码'),icon:'none'});return}
          if(claim.origin&&!isLocalStationOrigin(claim.origin)){uni.showToast({title:this.t('只允许连接局域网电脑的18000端口'),icon:'none'});return}
          const query='claim='+encodeURIComponent(claim.token||'')+'&server='+encodeURIComponent(claim.origin||'')
          uni.navigateTo({url:CLAIM_ROUTE+'?'+query,fail:()=>uni.showToast({title:this.t('打开领取页失败，请重试'),icon:'none'})})
        },
        fail:err=>{if(!String(err&&err.errMsg||'').includes('cancel'))uni.showToast({title:this.t('扫码失败，请检查相机权限'),icon:'none'})},
        complete:()=>{this.scanning=false}
      })
    },
    handleLogout: function () { this.showLogout=true },
    // 退出登录：清完会话后让登录页从「退出登录」这一行弹性展开，动画结束再切真实登录页，避免生硬换页。
    confirmLogout: function () {
      this.showLogout=false
      if (this.loginRevealOpen) return
      this.clearSession()
      var started=false
      var start=()=>{
        if (started) return
        started=true
        this.loginRevealOpen=true
        this._revealTimer=setTimeout(function(){uni.reLaunch({url:'/pages/auth/auth'})},1050)
      }
      try {
        uni.createSelectorQuery().in(this).select('.logout-item').boundingClientRect(function(rect){
          if(rect&&rect.width){ this.revealOriginX=rect.left+rect.width/2; this.revealOriginY=rect.top+rect.height/2 }
          start()
        }.bind(this)).exec()
      } catch (e) {}
      this._revealFallback=setTimeout(start,140)
    },
    clearSession: function () {
      uni.setStorageSync('login_auto_disabled',true)
      uni.removeStorageSync('token')
      uni.removeStorageSync('avatar')
      uni.removeStorageSync('login_provider')
      uni.removeStorageSync('user_id')
      uni.removeStorageSync('username')
      uni.removeStorageSync('wx_nickName')
      uni.removeStorageSync('wx_avatarUrl')
      uni.removeStorageSync('login_time')
    },
  },
  mounted:function(){
    this.statusH=(uni.getSystemInfoSync().statusBarHeight||20)+6
  },
  onHide:function(){this.showAbout=false;this.showLogout=false},
  onUnload:function(){clearTimeout(this._revealTimer);clearTimeout(this._revealFallback)},
  onShow: function () {
    this.showAbout=false;this.translateAiChatHistory(this.tourLanguage,true)
    var token = uni.getStorageSync('token')
    if (!token) { uni.reLaunch({ url: '/pages/auth/auth' }); return }
    uni.request({url:BASE_URL+'/user/me',header:{Authorization:'Bearer '+token},
      success:r=>{
        const d=r.data||{}
        if(r.statusCode===401){uni.removeStorageSync('token');uni.reLaunch({url:'/pages/auth/auth'});return}
        if(r.statusCode!==200||!d.success||!d.data){uni.showToast({title:this.t('个人资料加载失败'),icon:'none'});return}
        this.username=d.data.username||''
        this.userId=d.data.user_no||d.data.user_id||''
        this.avatarUrl=assetUrl(d.data.avatar||'')
        uni.setStorageSync('username',this.username)
        uni.setStorageSync('avatar',d.data.avatar||'')
      },fail:()=>{uni.showToast({title:this.t('个人资料加载失败，请检查网络'),icon:'none'})}})
  },
}
</script>

<style scoped>
.page.aurora-page .profile-card{background:transparent;border:0;box-shadow:none}
.page { min-height:100vh; background-color:var(--ng-surface); position:relative; overflow:hidden; padding-bottom:140rpx; }
.page-bg{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0}
.ink-bg { position:absolute; inset:0; pointer-events:none; z-index:0; overflow:hidden; }
.ink-mountain { position:absolute; left:0; right:0; background:var(--ng-night); border-radius:50% 70% 0 0; }
.ink-mt-1 { bottom:20%; height:200rpx; opacity:0.03; transform:scaleX(1.4); }
.ink-mt-2 { bottom:25%; height:150rpx; opacity:0.025; transform:scaleX(1.2) translateX(10%); }
/* 毛体导航 */
.nav{position:relative;z-index:1;display:flex;align-items:center;justify-content:flex-end;padding:16rpx 24rpx;background:var(--ng-surface)}
.nav-title{font-size:44rpx;font-weight:900;color:var(--ng-text);letter-spacing:8rpx;font-family:var(--app-font-family);text-align:center}

/* 右上角扫码领取路线（扫描电脑网页上的路线二维码） */
.nav-scan{display:flex;align-items:center;gap:8rpx;padding:12rpx 22rpx 12rpx 18rpx;border-radius:999rpx;background:var(--ng-raised);border:1rpx solid var(--ng-border);box-shadow:0 6rpx 18rpx rgba(30,41,59,.06);transition:transform .18s ease,background-color .18s ease}
.nav-scan-press{transform:scale(.94);background:rgba(99,102,241,.14)}
.nav-scan-label{font-size:24rpx;font-weight:600;line-height:1;color:var(--ng-text)}
.scan-icon{font-size:22px;color:var(--ng-accent-text)}
@media (prefers-reduced-motion: reduce){.nav-scan{transition:none}}

/* 头像卡片 */
.profile-card { position:relative; z-index:1; display:flex; flex-direction:column; align-items:center; padding:40rpx 32rpx 32rpx; }
.pc-avatar-wrap{position:relative;width:120rpx;height:120rpx}
.pc-avatar { width:120rpx;height:120rpx;border-radius:50%;border:3rpx solid rgba(99,102,241,0.25); }
.pc-avatar-df { width:120rpx;height:120rpx;border-radius:50%;background:linear-gradient(135deg,rgba(99,102,241,0.18),rgba(99,102,241,0.18));display:flex;align-items:center;justify-content:center; }
.pca-txt { font-size:52rpx;font-weight:600;color:var(--ng-text);font-family:var(--app-font-family); }
.pc-name-row{margin-top:20rpx}
.pc-name { font-size:36rpx; font-weight:800; color:var(--ng-text); }
.pc-id { font-size:22rpx; color:var(--ng-secondary); margin-top:8rpx; }
.menu-section { position:relative; z-index:1; padding:0 28rpx; }
.menu-group { margin-bottom:16rpx; border-radius:16rpx; overflow:hidden; background:var(--ng-surface); border:1rpx solid var(--ng-border); }
.menu-item { display:flex; align-items:center; justify-content:space-between; padding:28rpx 24rpx; border-bottom:1rpx solid var(--ng-border); }
.menu-item:last-child { border-bottom:0; }
.mi-left { display:flex; align-items:center; gap:16rpx; }
.language-menu-item { flex-wrap:wrap; gap:20rpx; }
.language-menu-item .lang-switch { flex-shrink:0; margin-left:auto; }
.mi-icon { font-size:32rpx; }
.mi-label { font-size:28rpx; font-weight:600; color:var(--ng-text); }
.mi-arrow { font-size:32rpx; color:var(--ng-secondary); }

/* 中英文切换（与「我的」菜单同排，样式沿用主题变量） */
/* 界面语言：白色滑块在两个选项间弹性滑动，按下时按钮回弹。 */
.lang-switch { position:relative; display:flex; align-items:center; padding:8rpx; border-radius:28rpx; background:var(--ng-raised); border:1rpx solid var(--ng-border); }
.lang-thumb { position:absolute; top:8rpx; bottom:8rpx; left:8rpx; width:80px; border-radius:20rpx; background:var(--ng-surface); box-shadow:0 4rpx 14rpx rgba(30,41,59,.10); transition:transform 160ms ease-out; will-change:transform; }
.lang-switch.en .lang-thumb { transform:translateX(80px); }
.lang-btn { position:relative; z-index:1; flex-shrink:0; width:80px; height:36px; display:flex; align-items:center; justify-content:center; padding:0; border:0; margin:0; background:transparent; color:var(--ng-secondary); font-size:26rpx; line-height:1.2; transition:color .26s ease, transform .24s cubic-bezier(.34,1.56,.64,1); }
.lang-btn.active { color:var(--ng-secondary); font-weight:700; }
.lang-btn.lang-press { transform:scale(.96); }
.lang-btn::after { border:0; }
@media (prefers-reduced-motion: reduce) { .lang-thumb, .lang-btn { transition:none; } }
.logout-item:active { background:rgba(228,155,168,0.04); }
.footer-tag { position:relative; z-index:1; text-align:center; padding:40rpx 0 20rpx; }
.footer-tag text { font-size:20rpx; color:var(--ng-secondary); letter-spacing:2rpx; }

.tb-root{position:fixed;bottom:0;left:0;right:0;z-index:999;background:var(--ng-surface)}
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

/* 关于我们：居中弹窗。页面在横向分页轨道里、底部标签栏层级更高，
   所以不用 fixed 抽屉（会沉到标签栏下面），改成相对页面绝对定位的居中框。 */
.about-overlay{position:fixed!important;top:0;right:0;bottom:0;left:0;z-index:1200!important;display:flex;align-items:center;justify-content:center;padding:48rpx;box-sizing:border-box;background:rgba(30,41,59,0.32);animation:aboutMaskIn .2s ease both}
.about-dialog{position:relative;width:100%;max-width:560rpx;padding:44rpx 40rpx 40rpx;box-sizing:border-box;border-radius:36rpx;background:#ffffff;border:1rpx solid #d9d3f0;box-shadow:0 18px 54px rgba(59,43,110,.22),0 3px 12px rgba(59,43,110,.1);animation:aboutDialogIn .26s cubic-bezier(.34,1.56,.64,1) both}
.about-title{display:block;text-align:center;font-size:32rpx;font-weight:700;color:#1f2937;letter-spacing:2rpx;font-family:var(--app-font-family)}
.about-intro{display:block;margin-top:20rpx;font-size:26rpx;line-height:1.75;color:#4b5563;text-align:center}
.about-close{position:absolute;top:16rpx;right:16rpx;width:56rpx;height:56rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.06)}
.about-close-txt{font-size:24rpx;line-height:1;color:#6b7280}
.about-close-press{background:rgba(99,102,241,0.14)}
@keyframes aboutMaskIn{from{opacity:0}to{opacity:1}}
@keyframes aboutDialogIn{from{opacity:0;transform:scale(.9) translateY(12rpx)}to{opacity:1;transform:scale(1) translateY(0)}}
@media (prefers-reduced-motion:reduce){.about-overlay,.about-dialog{animation:none}}

/* 退出登录：登录页弹性展开（与引导页「开始体验」同一套动效），避免生硬换页 */
.login-reveal{position:fixed!important;top:0;right:0;bottom:0;left:0;z-index:9999!important;overflow:hidden;background:linear-gradient(135deg,#eee8ff 0%,#fbfbff 52%,#eef8fc 100%);animation:loginSpring 850ms linear both;will-change:transform,opacity}
@keyframes loginSpring{0%{opacity:0;transform:scale(.1,.045);border-radius:180px}12%{opacity:1}45%{transform:scale(1.045,1.025);border-radius:32px}64%{transform:scale(.985,.99);border-radius:12px}82%{transform:scale(1.007,1.004);border-radius:4px}100%{opacity:1;transform:scale(1);border-radius:0}}
@media(prefers-reduced-motion:reduce){.login-reveal{animation:loginFade 120ms ease both}}
@keyframes loginFade{from{opacity:0}to{opacity:1}}
</style>
