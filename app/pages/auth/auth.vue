<template>
  <view class="auth-page" :class="{ 'auth-english': tourLanguage === 'en' }">
    <button class="auth-lang" :class="{ 'is-eng': tourLanguage !== 'en' }" hover-class="none" :aria-label="tourLanguage === 'en' ? '切换到中文' : 'Switch to English'" :aria-pressed="tourLanguage === 'en'" @tap="setLanguage(tourLanguage === 'en' ? 'zh' : 'en')">{{ tourLanguage === 'en' ? '中' : 'ENG' }}</button>
    <view class="auth-brand"><BrandLogo stacked animated /></view>
    <view class="welcome-card">
      <text class="welcome-title">{{ t(showConnection?'连接服务站':'让每一程，都有故事') }}</text>
    <view class="login-area">
      <view v-show="!showConnection" class="sign-in-form">
      <view >
        <input v-if="registering" class="nickname-input" style="margin-bottom:20rpx" v-model="nickname" :placeholder="t('昵称（用于登录）')" maxlength="40" :disabled="logining||connecting" />
        <input class="nickname-input" v-model="account" :placeholder="t(registering ? '邮箱地址' : '昵称')" maxlength="254" :disabled="logining||connecting" />
        <input class="nickname-input" style="margin:20rpx 0" v-model="password" password :placeholder="t('密码')" :disabled="logining||connecting" />
        <input v-if="registering" class="nickname-input" style="margin:20rpx 0" v-model="confirmPassword" password :placeholder="t('再次输入密码（至少8位）')" :disabled="logining||connecting" />
        <view v-if="registering">
          <input class="nickname-input" v-model="emailCode" type="number" maxlength="6" :placeholder="t('邮箱验证码')" :disabled="logining||connecting" />
          <button class="dialog-cancel" style="margin:20rpx 0" :disabled="sendingCode || logining || connecting || codeRetryAt>0" @tap="sendEmailCode">{{ t(sendingCode ? '正在发送…' : codeRetryAt>0 ? '请稍后再发送' : '发送验证码') }}</button>
        </view>
      </view>
      <button class="primary login-cta" :disabled="logining||connecting" @tap="beginLogin">{{ t(logining ? '正在处理…' : registering ? '注册并登录' : '登录') }}</button>
      <view  class="register-row" @tap="toggleRegistration">
        <text class="register-text">{{ t(registering ? '已有账号，去登录' : '没有账号？邮箱注册') }}</text>
      </view>
      <text v-if="registering && codeNotice" class="notice">{{ t(codeNotice) }}</text>
      <text v-if="error" class="error">{{ t(error) }}</text>
      </view>
      <view class="service-tools">
        <button class="service-toggle" :disabled="logining||sendingCode||connecting" :aria-expanded="showConnection" @tap="toggleConnection">{{ t(showConnection?'返回':'连接服务站') }}</button>
        <text v-if="serviceNotice" class="notice" role="status">{{ t(serviceNotice) }}</text>
        <view v-if="showConnection" class="service-panel">
          <text>{{ t('服务地址') }}</text>
          <input class="service-input" v-model="serviceAddress" :disabled="connecting" :placeholder="t('输入服务地址')" :aria-label="t('服务地址')" />
          <view class="service-actions">
            <button :disabled="connecting" @tap="scanService">{{ t('扫码连接') }}</button>
            <button :disabled="connecting||!serviceAddress.trim()" @tap="connectService()">{{ t(connecting?'正在连接…':'连接') }}</button>
          </view>
          <text v-if="serviceError" class="error" role="alert">{{ t(serviceError) }}</text>
        </view>
      </view>
    </view>
    </view>

  </view>
</template>
<script>
import { LANGUAGE_STORAGE_KEY, translateTour } from '../../common/tour-language.js'
import BrandLogo from '../../components/BrandLogo.vue'
import { CLAIM_ROUTE, pendingClaim, parseClaim, saveClaim, clearPendingClaim } from '../../common/station-claim.js'
import { BASE_URL, LOGIN_PROVIDER, SERVER_ORIGIN, normalizeServiceOrigin, setServiceOrigin } from '../../common/config.js'
export default {
  components: { BrandLogo },
  data() { return {showConnection:false,connecting:false,serviceAddress:'',serviceError:'',serviceNotice:'',emailCode:'',sendingCode:false,codeRetryAt:0,codeNotice:'',registering:false,confirmPassword:'',account:'',password:'',logining:false,error:'',nickname:''} },
  onShow() { this.tourLanguage=uni.getStorageSync(LANGUAGE_STORAGE_KEY)==='en'?'en':'zh'; uni.setNavigationBarColor({frontColor:'#000000',backgroundColor:'#f8fafc',animation:{duration:0,timingFunc:'linear'}}) },
  onUnload() { clearTimeout(this._emailCodeTimer);this._authDisposed=true;this._connectionVersion=(this._connectionVersion||0)+1;this._serviceProbe?.abort() },
  onLoad(options = {}) {
    if (options.expired === '1') { this.error='登录已过期，请重新输入账号密码'; return }
    // The explicit onboarding action always opens sign-in, even with a saved account.
    if (options.fromOnboarding === '1') return
    if(uni.getStorageSync('login_auto_disabled')) return
    // 登录一次即长期免登录：本地有 token 就直接恢复会话。
    if(uni.getStorageSync('token')) { this.restoreSession(); return }
  },
  methods: {
    toggleConnection() {if(this.logining||this.sendingCode||this.connecting)return;this.showConnection=!this.showConnection;this.serviceAddress=SERVER_ORIGIN;this.serviceError='';this.serviceNotice=''},
    scanService() {
      if(this.connecting||this.logining||this.sendingCode)return
      uni.scanCode({onlyFromCamera:true,success:result=>{
        if(this._authDisposed)return
        try {const claim=parseClaim(result.result);const origin=normalizeServiceOrigin(claim?.origin||result.result);if(!origin)throw new Error('请扫描服务站二维码');this.serviceAddress=origin;this.connectService(claim?result.result:'')}
        catch(e){this.serviceError=e.message||'请扫描服务站二维码'}
      },fail:result=>{if(!String(result?.errMsg||'').includes('cancel'))this.serviceError='扫码失败，请检查相机权限'}})
    },
    async connectService(claimValue) {
      if(this.connecting||this.logining||this.sendingCode)return
      const origin=normalizeServiceOrigin(this.serviceAddress)
      if(!origin){this.serviceError='请输入有效的 HTTPS 服务地址或局域网服务地址';return}
      const version=this._connectionVersion=(this._connectionVersion||0)+1
      this.connecting=true;this.serviceError='';this.serviceNotice=''
      try {
        const result=await new Promise((resolve,reject)=>{this._serviceProbe=uni.request({url:origin+'/api/v1/tour-session/spots',timeout:6000,success:resolve,fail:reject})})
        if(version!==this._connectionVersion)return
        if(result.statusCode!==200||!result.data?.success)throw new Error('无法连接该服务，请检查地址和网络')
        const changed=origin!==SERVER_ORIGIN
        setServiceOrigin(origin)
        if(claimValue)saveClaim(claimValue)
        else if(changed)clearPendingClaim()
        if(changed){clearTimeout(this._emailCodeTimer);this.codeRetryAt=0;this.emailCode='';this.codeNotice='';this.confirmPassword=''}
        this.password='';this.error='';this.serviceNotice='连接成功，请登录';this.showConnection=false
      } catch(e) {if(version===this._connectionVersion)this.serviceError='无法连接该服务，请检查地址和网络'}
      finally {if(version===this._connectionVersion)this.connecting=false}
    },
    t(value) { return translateTour(value, this.tourLanguage) },
    setLanguage(language) { this.tourLanguage=language;uni.setStorageSync(LANGUAGE_STORAGE_KEY,language) },
    networkError(e) {
      this.error='无法连接导览服务，请稍后重试'
    },
    finishLogin(user) {
      if(user.user_id)uni.setStorageSync('user_id',user.user_id)
      uni.setStorageSync('username',user.username||'')
      uni.setStorageSync('avatar',user.avatar||'')
      uni.setStorageSync('login_provider',LOGIN_PROVIDER)
      uni.removeStorageSync('login_auto_disabled')
      this.logining=false
      uni.reLaunch({url:pendingClaim()?CLAIM_ROUTE:'/pages/tabs/tabs?tab=tour',fail:e=>{this.logining=false;this.error='进入导览页面失败，请重试';console.error('Login navigation failed',e)}})
    },
    restoreSession() {
      this.logining=true;this.error=''
      uni.request({url:BASE_URL+'/user/me',header:{Authorization:'Bearer '+uni.getStorageSync('token')},timeout:15000,
        success:r=>{
          this.logining=false
          if(r.statusCode===401){uni.removeStorageSync('token');this.error='登录已过期，请重新输入账号密码';return}
          const d=r.data||{}
          if(r.statusCode!==200||!d.success||!d.data){this.error=d.detail||d.message||'登录状态验证失败';return}
          this.finishLogin(d.data)
        },
        fail:e=>{this.logining=false;this.networkError(e)}})
    },
    beginLogin() {
      if(this.logining||this.connecting)return
      if(this.registering)this.registerWithEmail();else this.loginWithPassword()
    },
    toggleRegistration() {
      if(this.logining||this.connecting)return
      this.registering=!this.registering;this.error='';this.password='';this.confirmPassword='';this.emailCode=''
    },
    sendEmailCode() {
      if(this.sendingCode||this.logining||this.connecting)return
      if(Date.now()<this.codeRetryAt){this.error='请等待60秒后再发送验证码';return}
      const email=this.account.trim().toLowerCase()
      if(!email){this.error='请先填写注册邮箱';return}
      this.sendingCode=true;this.error='';this.codeNotice=''
      uni.request({url:BASE_URL+'/user/email-code',method:'POST',data:{email},timeout:25000,
        success:r=>{
          const d=r.data||{}
          if(r.statusCode!==200||!d.success){this.error=typeof d.detail==='string'?d.detail:'验证码发送失败';return}
          this.codeNotice=d.message;this.codeRetryAt=Date.now()+(d.retry_after||60)*1000
          clearTimeout(this._emailCodeTimer)
          this._emailCodeTimer=setTimeout(()=>{this.codeRetryAt=0},(d.retry_after||60)*1000)
        },fail:e=>this.networkError(e),complete:()=>{this.sendingCode=false}})
    },
    registerWithEmail() {
      const email=this.account.trim().toLowerCase()
      const nickname=this.nickname.trim()
      if(!nickname||nickname.includes('@')){this.error='请填写昵称，不能包含 @';return}
      if(!email||!this.password){this.error='请输入邮箱和密码';return}
      if(this.password.length<8){this.error='密码至少8位';return}
      if(this.password!==this.confirmPassword){this.error='两次输入的密码不一致';return}
      if(!/^\d{6}$/.test(this.emailCode)){this.error='请输入6位邮箱验证码';return}
      this.logining=true;this.error=''
      uni.request({url:BASE_URL+'/user/register',method:'POST',data:{email,nickname,password:this.password,code:this.emailCode},timeout:15000,
        success:r=>{
          this.logining=false
          const d=r.data||{}
          if(r.statusCode!==200||!d.success){this.error=typeof d.detail==='string'?d.detail:'注册失败，请稍后重试';return}
          this.account=nickname;this.registering=false;this.confirmPassword=''
          this.loginWithPassword()
        },
        fail:e=>{this.logining=false;this.networkError(e)}})
    },
    loginWithPassword() {
      const username=this.account.trim()
      if(!username||!this.password){this.error='请输入账号和密码';return}
      this.logining=true;this.error=''
      uni.request({url:BASE_URL+'/user/login',method:'POST',
        header:{'Content-Type':'application/x-www-form-urlencoded'},
        data:'username='+encodeURIComponent(username)+'&password='+encodeURIComponent(this.password),timeout:15000,
        success:r=>{
          const d=r.data||{}
          if(r.statusCode!==200||!d.access_token){this.logining=false;this.error=r.statusCode===401?'账号或密码错误':typeof d.detail==='string'?d.detail:'登录失败，请稍后重试';return}
          uni.setStorageSync('token',d.access_token)
          uni.setStorageSync('login_provider',LOGIN_PROVIDER)
          this.password=''
          this.restoreSession()
        },
        fail:e=>{this.logining=false;this.networkError(e)}})
    },

  }
}
</script>

<style scoped>
.service-tools{margin-top:12px;font-size:28rpx;line-height:1.6}.service-toggle{min-height:44px;background:transparent;color:var(--ng-accent-text,#5141ad);font-size:inherit;display:flex;align-items:center;justify-content:center}.service-toggle::after,.service-actions button::after{border:0}.service-panel{margin-top:8px;padding:16px;border:1px solid var(--ng-border,#e2e8f0);border-radius:18px;background:var(--ng-surface,#fff)}.service-input{height:44px;margin-top:8px;box-sizing:border-box;width:100%;padding:0 12px;border:1px solid var(--ng-border,#e2e8f0);border-radius:12px;font-size:inherit}.service-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.service-actions button{flex:1;min-width:90px;min-height:44px;margin:0;padding:8px 12px;font-size:inherit;line-height:1.5;display:flex;align-items:center;justify-content:center;background:var(--ng-raised,#f0edf8);color:var(--ng-accent-text,#5141ad);border-radius:12px}.service-actions button[disabled]{opacity:.5}
.auth-page{box-sizing:border-box;min-height:100vh;padding:calc(110rpx + env(safe-area-inset-top)) 36rpx calc(48rpx + env(safe-area-inset-bottom));background:#f8fafc;color:#1f2937}
.auth-brand{display:flex;flex-direction:column;align-items:flex-start;gap:18rpx;margin-bottom:44rpx}.auth-eyebrow{font-size:24rpx;color:#64748b;letter-spacing:2rpx}
.welcome-card{position:relative;overflow:hidden;padding:40rpx 32rpx 28rpx;border:1rpx solid #e2e8f0;border-radius:32rpx;background:#fff;box-shadow:0 20rpx 64rpx -24rpx rgba(30,41,59,.12)}
.welcome-label{display:block;color:#4338ca;font-size:24rpx;margin-bottom:20rpx}.welcome-title{display:block;font-size:48rpx;line-height:1.45;font-weight:700;letter-spacing:-1rpx}.welcome-accent{display:block;color:#4f46e5}.welcome-copy{display:block;margin-top:20rpx;font-size:27rpx;line-height:1.8;color:#64748b}
.register-row{display:flex;justify-content:center;margin-top:32rpx}
.register-text{font-size:24rpx;line-height:1.6;color:#64748b;text-decoration:underline;text-underline-offset:8rpx;text-decoration-thickness:1rpx}
.login-area{margin-top:36rpx;padding:32rpx;border:1rpx solid #e2e8f0;border-radius:32rpx;background:#fff;box-shadow:0 16rpx 48rpx -24rpx rgba(30,41,59,.1)}.login-heading{display:block;font-size:32rpx;font-weight:600}.login-copy{display:block;font-size:25rpx;color:#64748b;margin:12rpx 0 28rpx}
.primary{margin:0;padding:0;height:96rpx;line-height:96rpx;border-radius:20rpx;font-size:30rpx;font-weight:600;background:#4f46e5;color:#fff;box-shadow:0 12rpx 30rpx -12rpx rgba(79,70,229,.4)}.primary::after{border:0}.primary[disabled]{background:#e2e8f0;color:#64748b;box-shadow:none}.error{display:block;margin-top:20rpx;padding:20rpx;border-radius:16rpx;background:#fff1f2;color:#be123c;font-size:24rpx;line-height:1.7;word-break:break-all}.notice{display:block;margin-top:18rpx;font-size:24rpx;color:#64748b;text-align:center}
.profile-overlay{position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;padding:36rpx;background:rgba(15,23,42,.35)}.profile-dialog{width:100%;max-width:640rpx;box-sizing:border-box;padding:36rpx 28rpx;border:1rpx solid #e2e8f0;border-radius:32rpx;background:#fff;box-shadow:0 32rpx 80rpx rgba(30,41,59,.15)}.dialog-title{display:block;font-size:34rpx;font-weight:600;margin-bottom:32rpx}.profile-fields{display:flex;align-items:center;gap:20rpx;margin-bottom:28rpx}.avatar-picker{margin:0;padding:0;width:120rpx;height:120rpx;border-radius:24rpx;background:#eef2ff;color:#4338ca;font-size:23rpx;display:flex;align-items:center;justify-content:center;flex-shrink:0}.profile-avatar{width:100%;height:100%}.nickname-input{flex:1;min-width:0;height:96rpx;padding:0 20rpx;border:1rpx solid #e2e8f0;border-radius:20rpx;background:#f8fafc;color:#1f2937;font-size:28rpx}.dialog-actions{display:flex;gap:20rpx}.dialog-actions button{flex:1}.dialog-cancel{margin:0;padding:0;height:96rpx;line-height:96rpx;border-radius:20rpx;background:#f1f5f9;color:#475569;font-size:28rpx}.dialog-cancel::after{border:0}

.auth-brand{align-items:center;}
/* Keep the selected lavender page composition; only the icon moves. */
.auth-page{padding-top:calc(140rpx + env(safe-area-inset-top));background:linear-gradient(135deg,#eee8ff 0%,#fbfbff 52%,#eef8fc 100%)!important;}
.auth-brand{margin-bottom:48rpx;gap:12rpx;}.auth-eyebrow{font-size:22rpx;color:#8b84ac;letter-spacing:4rpx;}
.welcome-card{border:0;border-radius:36rpx;padding:32rpx;background:rgba(255,255,255,.92);box-shadow:0 20rpx 60rpx -24rpx rgba(70,54,130,.12);}
.welcome-label{font-size:23rpx;color:#8b74c9;margin-bottom:14rpx;display:block;text-align:center;}.welcome-title{font-size:36rpx;color:#30285e;line-height:1.5;display:block;text-align:center;}.welcome-copy{font-size:25rpx;margin-top:14rpx;color:#8a84a0;display:block;text-align:center;}
.register-row{margin-top:26rpx;}
.register-text{color:#8b84a3;font-size:23rpx;letter-spacing:.5rpx;}
.login-area{margin-top:26rpx;padding:0;border:0;box-shadow:none;background:transparent;}.primary{border-radius:22rpx;}
/* 登录按钮：柔和浅紫色静态渐变。 */
.primary.login-cta{background:linear-gradient(110deg,#9879df 0%,#aa8fe7 55%,#b7a0ec 100%);animation:none;box-shadow:0 12rpx 30rpx -12rpx rgba(152,121,223,.32)}
.primary.login-cta[disabled]{background:#e2e8f0;color:#64748b;box-shadow:none;animation:none}
.auth-page{position:relative;}
/* 登录页语言按钮：与引导页一致的白色圆形 ENG/中 切换 */
.auth-lang{position:absolute;right:36rpx;top:calc(32rpx + env(safe-area-inset-top));width:64rpx;height:64rpx;min-height:0;margin:0;padding:0;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.68);border:1rpx solid rgba(255,255,255,.92);box-shadow:0 6rpx 16rpx rgba(103,80,217,.14),inset 0 1rpx 0 rgba(255,255,255,.95);color:#5b45e0;font-size:26rpx;letter-spacing:0;-webkit-tap-highlight-color:transparent}
.auth-lang.is-eng{font-size:19rpx;font-weight:600;letter-spacing:0}
.auth-lang::after{border:0}
.auth-english .auth-eyebrow{letter-spacing:1rpx;}.auth-english .welcome-title{font-size:36rpx;letter-spacing:0;}.auth-english .register-text{font-size:22rpx;letter-spacing:0;}
</style>
