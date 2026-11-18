<script>
import { LOGIN_PROVIDER } from './common/config.js'
import { ONBOARDING_STORAGE_KEY, ONBOARDING_ROUTE } from './common/onboarding.js'
import { CLAIM_ROUTE, clearPendingClaim, saveClaim } from './common/station-claim.js'
export default {
  onLaunch: function() {
    console.log('App Launch')
    // 首页悬浮球只在本次打开 App 内有效，重启后清空。
    try { uni.removeStorageSync('home-orb-resume') } catch (_) {}
    clearPendingClaim()
    // 每次打开 App，路径规划都从空开始；只有本次手动加入的景点才算。
    try { uni.removeStorageSync('scenic-selection-touched') } catch (_) {}
    try { uni.removeStorageSync('scenic-settings-touched') } catch (_) {}
    // 每次重新打开 App 清除上次的路线，首页不显示“继续导览”悬浮球。
    try { uni.removeStorageSync('pending-tour-route') } catch (_) {}
  },
  onHide: function() {
    // 记录是从主界面切到后台的，回来时重新展示欢迎页。
    this._hiddenFromMain = true
  },
  onShow: function() {
    let incomingClaim = false
    // #ifdef APP-PLUS
    const args = typeof plus !== 'undefined' ? plus.runtime.arguments : ''
    if (args && args !== this._lastClaimArguments) {
      this._lastClaimArguments = args
      try { saveClaim(args); incomingClaim = true } catch (_) { /* Ordinary launches have no claim. */ }
    }
    // #endif
    var token = uni.getStorageSync('token')
    var pages = getCurrentPages()
    var currentPage = ''
    if (pages && pages.length) {
      currentPage = (pages[pages.length - 1] || {}).route || ''
    }
    // 冷启动先停在欢迎页，由欢迎页自己决定下一步，避免被登录/引导重定向打断。
    if (currentPage === 'pages/welcome/welcome') return
    // 打开系统相册/相机时 App 会短暂 onHide，回来不该当成重新启动而跳欢迎页。
    var pickerGuard = Number(uni.getStorageSync('picker-resume-guard') || 0)
    if (pickerGuard && Date.now() - pickerGuard < 120000) return
    if (this._hiddenFromMain) {
      this._hiddenFromMain = false
      // 从后台回到主界面时也先看「Hi 颐和园」，再决定进哪个主页面。
      if (currentPage === 'pages/tabs/tabs') { uni.reLaunch({ url: '/pages/welcome/welcome' }); return }
    }
    if (!uni.getStorageSync(ONBOARDING_STORAGE_KEY)) {
      if (currentPage && currentPage !== ONBOARDING_ROUTE) uni.reLaunch({ url: '/' + ONBOARDING_ROUTE })
      return
    }
    if (currentPage === ONBOARDING_ROUTE) return
    if (currentPage === CLAIM_ROUTE.slice(1)) return
    if (incomingClaim && currentPage.indexOf('pages/auth/auth') === -1) {
      uni.reLaunch({ url: CLAIM_ROUTE })
      return
    }
    if ((!token || uni.getStorageSync('login_provider') !== LOGIN_PROVIDER) && currentPage.indexOf('pages/auth/auth') === -1) {
      // A scanned-route page can be opening sign-in at the same time during a cold launch.
      uni.reLaunch({ url: '/pages/auth/auth', fail: err => console.warn('Sign-in navigation already in progress', err.errMsg || '') })
    }
  },
}
</script>

<style>
@import "./common/soft-ui.css";
@import url("/static/iconfont/iconfont-inline.css");
@import "./common/icons.css";
page { background:var(--ng-night); color:var(--ng-text); font-family:var(--app-font-family); }
.page { background:var(--ng-night); color:var(--ng-text); }
.page .nav { border-color:var(--ng-border); }
.page .card,.page .menu-group,.page .profile-card,.page .map-card,.page .rank-block,.page .block { background:var(--ng-surface); border-color:var(--ng-border); border-radius:24rpx; }
.page .ink-bg,.auth-page .ink-bg { display:none; }
.page .nav { background:var(--ng-surface); border-bottom:1rpx solid var(--ng-border); padding-bottom:24rpx; }
.page .nav-title { font-family:var(--app-font-family); font-size:36rpx; font-weight:700; letter-spacing:0; }
.page .tb-root { background:var(--ng-surface); border-top:1rpx solid var(--ng-border); box-shadow:0 -8rpx 30rpx rgba(30,41,59,.06); }
/* 三页容器：标签栏在 AI 页收起时，页面底部留白同步释放，避免出现空档 */
.tabs-shell.dock-down .panel-slot .page.aurora-page{padding-bottom:calc(env(safe-area-inset-bottom))!important}
.page .tb-ink-line { display:none; }
.page .tb-hl-ring { background:transparent; border:none; box-shadow:none; }
.page .tb-hl-ring.on { background:var(--ng-surface); border-radius:20rpx; }
.page .tb-label,.page .tb-icon { color:var(--ng-secondary); }
.page .tb-item.on .tb-label,.page .tb-item.on .tb-icon { color:var(--ng-secondary); }
.page .map-card,.page .rank-block,.page .block,.page .menu-group,.page .profile-card { border:1rpx solid transparent; border-radius:32rpx; box-shadow:var(--ng-glass-shadow); }
.page .bottom-bar,.page .input-bar,.page .bottom-fixed { background:var(--ng-surface); }
.page .msg-bubble.ai,.page .msg-bubble.guide { background:var(--ng-surface); border-color:var(--ng-border); }
.page .msg-bubble.user { background:rgba(99,102,241,0.18); color:var(--ng-text); }
.aurora-page{background:transparent!important;color:var(--ng-text)}
.aurora-background{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none;background:linear-gradient(145deg,var(--ng-surface) 0%,var(--ng-surface) 35%,var(--ng-surface) 70%,var(--ng-surface) 100%)}
.aurora-page>view:not(.aurora-background):not(.tb-root):not(.bottom-fixed):not(.drawer-overlay):not(.scenic-sheet-overlay):not(.confirm-overlay):not(.spot-drawer):not(.fab-btn):not(.photo-popover-mask):not(.select-overlay):not(.login-reveal):not(.voice-render):not(.about-overlay){position:relative;z-index:1}
.aurora-page .nav{background:transparent!important;border-bottom-color:var(--ng-border)!important;gap:18rpx}
.aurora-page .nav-title{color:var(--ng-text)}
.aurora-page .tb-root{position:fixed!important;background:var(--ng-surface)!important;border-top-color:var(--ng-border)!important}
.aurora-page .input-bar,.aurora-page .bottom-bar,.aurora-page .bottom-fixed{background:var(--ng-surface)!important}
.aurora-wave{position:absolute;width:180%;height:65%;left:-40%;border-radius:45%;background:radial-gradient(ellipse,rgba(99,102,241,0.18),rgba(99,102,241,0.1) 55%,transparent 72%);animation:auroraDrift 16s ease-in-out infinite alternate;will-change:transform}
.aurora-wave-one{top:-10%;transform:rotate(-18deg)}
.aurora-wave-two{bottom:-20%;background:radial-gradient(ellipse,rgba(99,102,241,0.12),rgba(99,102,241,0.12) 55%,transparent 72%);animation-delay:-8s;animation-duration:22s}
.aurora-shine{position:absolute;inset:-40%;background:linear-gradient(115deg,transparent 35%,var(--ng-surface) 47%,var(--ng-surface) 54%,transparent 66%);animation:auroraShimmer 12s ease-in-out infinite alternate;will-change:transform}
.brand-ai{display:flex;align-items:center;justify-content:center;width:72rpx;height:72rpx;flex-shrink:0;border-radius:20rpx;background:var(--ng-night);color:var(--ng-text);font-size:26rpx;font-weight:700;box-shadow:0 10rpx 28rpx rgba(30,41,59,0.28)}
.aurora-page{--tab-icon-size:24px;--tab-label-size:14px;--tab-touch-height:60px;padding-bottom:calc(72px + env(safe-area-inset-bottom))!important}
.aurora-page.no-tabbar{padding-bottom:0!important}
.aurora-page .tb-root{--tab-label-size:13px}
.aurora-page .tb-inner{display:flex;align-items:center;justify-content:space-around;padding:6px 6px!important;min-height:var(--tab-touch-height);box-sizing:border-box}
.aurora-page .tb-item{flex:1;min-width:0;min-height:46px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px}
.aurora-page .tb-hl-ring{width:44px!important;height:28px!important;border-radius:10px!important}
.aurora-page .tb-icon,.aurora-page .tb-hl-ring .tb-icon{font-size:var(--tab-icon-size)!important;line-height:1.15}
.aurora-page .tb-label{font-size:var(--tab-label-size)!important;line-height:1.3;white-space:nowrap;font-weight:600!important}
.aurora-page .tb-safe{height:env(safe-area-inset-bottom)!important;min-height:0!important}
.aurora-page .bottom-fixed .tb-root{position:relative!important;bottom:auto!important}
.aurora-page .bottom-fixed~view{z-index:1}
@media(min-width:390px){.aurora-page{--tab-icon-size:26px;--tab-label-size:15px;--tab-touch-height:64px}.aurora-page .tb-root{--tab-label-size:14px}}
@media(min-width:430px){.aurora-page{--tab-icon-size:28px;--tab-label-size:16px;--tab-touch-height:68px}.aurora-page .tb-root{--tab-label-size:15px}}
@keyframes auroraDrift{from{transform:translate(-6%,0) rotate(-18deg)}to{transform:translate(9%,12%) rotate(12deg)}}
@keyframes auroraShimmer{from{transform:translateX(-18%) rotate(-6deg);opacity:.4}to{transform:translateX(18%) rotate(6deg);opacity:1}}

.tab-enter-right .main,.tab-enter-right .chat-area,.tab-enter-right .profile-card,.tab-enter-right .quick-hints,.tab-enter-right .menu-group{animation:tabEnterRight 320ms cubic-bezier(.22,1,.36,1) both}
.tab-enter-left .main,.tab-enter-left .chat-area,.tab-enter-left .profile-card,.tab-enter-left .quick-hints,.tab-enter-left .menu-group{animation:tabEnterLeft 320ms cubic-bezier(.22,1,.36,1) both}
@keyframes tabEnterRight{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}
@keyframes tabEnterLeft{from{opacity:0;transform:translateX(-20px)}to{opacity:1;transform:translateX(0)}}
/* #ifdef APP-PLUS */
page{--app-page-gradient:linear-gradient(135deg,#eee8ff 0%,#fbfbff 52%,#eef8fc 100%)}
page .page .aurora-background{background:var(--app-page-gradient)!important;background-size:100vw 100vh!important;background-position:0 0!important;background-repeat:no-repeat!important}
.page.aurora-page > .app-status-bar-shield{position:fixed!important;top:0;left:0;right:0;height:var(--status-bar-height);z-index:10000!important;background:var(--app-page-gradient);background-size:100vw 100vh;background-position:0 0;background-repeat:no-repeat;pointer-events:none}
/* #endif */
/* 全局统一返回箭头 */
.app-back-icon{width:40rpx;height:40rpx;background-color:#282332;-webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M19 12H5M11 6l-6 6 6 6'/%3E%3C/svg%3E") center / contain no-repeat;mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M19 12H5M11 6l-6 6 6 6'/%3E%3C/svg%3E") center / contain no-repeat}
/* ==========================================================================
   全系统统一返回键：白底 + 浅紫描边 + 深色细箭头（设计基准：导览页左上返回键）
   统一结构：
     <view class="app-back-btn" ...><view class="app-back-icon"></view></view>
   新增页面一律复用这两个类，不要再单独画箭头/单独改圆角底色。
   ========================================================================== */
.app-back-btn, .nav-back, .planning-back, .detail-back, .guide-back, .wander-back {
  box-sizing: border-box !important;
  width: 44px !important; height: 44px !important;
  min-width: 44px !important; min-height: 44px !important;
  padding: 0 !important;
  border: 1rpx solid rgba(139,120,230,.45) !important;
  border-radius: 50% !important;
  background: #ffffff !important;
  box-shadow: 0 6rpx 18rpx rgba(90,70,180,.12) !important;
  color: #282332 !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  line-height: 1 !important;
}
.app-back-btn:active, .nav-back:active, .planning-back:active, .detail-back:active,
.guide-back:active, .wander-back:active { transform: scale(.94); transition: transform 120ms cubic-bezier(.2,.8,.2,1); }
.app-back-btn .app-back-icon, .nav-back .app-back-icon, .planning-back .app-back-icon,
.detail-back .app-back-icon, .guide-back .app-back-icon, .wander-back .app-back-icon,
.app-back-btn .back-icon, .nav-back .back-icon, .planning-back .back-icon, .detail-back .back-icon {
  width: 40rpx !important; height: 40rpx !important; background-color: #282332 !important;
}
/* 旧页面若仍用 iconfont 画箭头，也统一成同一深色 */
.nav-back.iconfont { font-size: 22px !important; color: #282332 !important; }
/* 统一返回键是 button 时，去掉 uni-app 默认的边框伪元素 */
button.app-back-btn::after, button.nav-back::after, button.planning-back::after,
button.detail-back::after, button.guide-back::after, button.wander-back::after { border: 0 !important; }


/* 全局：滚动到边界不要弹簧回弹（AI导游、我的等所有页面） */
page,html,body,uni-page-body{overscroll-behavior:none!important}
.uni-scroll-view,.uni-page-body,.uni-page-wrapper{overscroll-behavior:none!important}
</style>
