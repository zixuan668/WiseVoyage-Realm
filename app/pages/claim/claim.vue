<template>
  <view class="claim-page"><view class="claim-card">
    <text class="claim-title">{{ t(snapshot?'选择数字人':'领取电脑上的路线') }}</text>
    <text class="claim-note">{{ t(snapshot?'请选择一位数字人，确认后开始导览。':'输入网页上的领取码，或扫描路线二维码。') }}</text>
    <view v-if="snapshot" class="claim-route">
      <text>{{ (snapshot.route.stops||[]).map(s=>t(s.spot_name||s.name)).join(' → ') }}</text>
      <text class="claim-duration">{{ t('预计用时') }} {{ snapshot.route.total_minutes }} {{ t('分钟') }}</text>
    </view>
    <input v-if="!snapshot&&!scanned" v-model="code" class="claim-input" :placeholder="t('输入12位领取码')" maxlength="100" :disabled="busy" />
    <view v-if="snapshot&&guides.length" class="claim-guides" role="group" :aria-label="t('选择数字人')">
      <button v-for="guide in guides" :key="guide.guide_id" class="claim-guide" :class="{selected:pickedGuideId===guide.guide_id}" :aria-pressed="pickedGuideId===guide.guide_id" :disabled="busy" @tap="pickedGuideId=guide.guide_id;error=''">
        <image v-if="guideImage(guide)&&!failedImages[guide.guide_id]" :src="guideImage(guide)" mode="aspectFit" class="claim-guide-image" @error="failedImages[guide.guide_id]=true" />
        <view v-else class="claim-guide-placeholder"><text class="iconfont icon-wode1" aria-hidden="true"></text></view>
        <view class="claim-guide-name"><text>{{ guideName(guide) }}</text><text v-if="pickedGuideId===guide.guide_id" class="iconfont icon-check" :aria-label="t('已选择')"></text></view>
      </button>
    </view>
    <view v-else-if="snapshot" class="claim-empty"><text>{{ t('暂无可用数字人，请稍后重试') }}</text><button :disabled="busy" @tap="prepare">{{ t('重试') }}</button></view>
    <text v-if="error" class="claim-error" role="alert">{{ t(error) }}</text>
    <button class="claim-primary" :disabled="busy || (!snapshot&&!code.trim())" @tap="snapshot?beginTour():prepare()">{{ t(busy ? '正在处理…' : snapshot?'开始导览':'领取路线') }}</button>
    <button class="scan" :disabled="busy" @tap="scan">{{ t(snapshot?'重新扫码':'扫描路线二维码') }}</button>
    <button class="cancel" :disabled="busy" @tap="leave">{{ t(snapshot?'暂不开始':'稍后领取') }}</button>
  </view></view>
</template>
<script>
import { BASE_URL, SERVER_ORIGIN, setStationServerOrigin, isLocalStationOrigin, assetUrl } from '../../common/config.js'
import { pendingClaim, saveClaim, clearPendingClaim } from '../../common/station-claim.js'
export default {
  data() { return { code:'', origin:'', scanned:false, busy:false, error:'',snapshot:null,guides:[],pickedGuideId:0,failedImages:{} } },
  // 支持两种进入方式：App 扫码后带参数跳转，或系统扫码/剪贴板唤起时读取待领取记录。
  onLoad(options) {
    const decode=v=>{try{return decodeURIComponent(String(v||''))}catch(_){return String(v||'')}}
    const query=options&&options.claim?{token:decode(options.claim),origin:decode(options.server||'')}:null
    const pending=query||pendingClaim()
    if(pending) { this.code=pending.token||pending.code||''; this.origin=pending.origin||''; this.scanned=!!this.code }
  },
  onReady() { if(this.scanned) this.prepare() },
  onUnload() {this._disposed=true;this._version=(this._version||0)+1;(this._requests||[]).forEach(task=>task?.abort())},
  methods: {
    signIn(expired=false) {
      if(this._openingSignIn)return
      this._openingSignIn=true
      uni.reLaunch({url:'/pages/auth/auth'+(expired?'?expired=1':''),fail:()=>{this._openingSignIn=false;if(!this._disposed)this.error='领取失败，请重试'}})
    },
    guideName(guide) {return this.tourLanguage==='en'?(guide.name_en||this.t(guide.name)):guide.name},
    guideImage(guide) {return assetUrl(guide.poster_image||guide.avatar||'')},
    receipt() {
      let receipt=uni.getStorageSync('station-app-receipt')
      if(!receipt){receipt=Array.from({length:48},()=>Math.floor(Math.random()*16).toString(16)).join('');uni.setStorageSync('station-app-receipt',receipt)}
      return receipt
    },
    fetchClaim(path,method='GET',data) {
      const token=uni.getStorageSync('token')
      return new Promise((resolve,reject)=>{
        const task=uni.request({url:BASE_URL+path,method,data,timeout:20000,header:{Authorization:'Bearer '+token},
          success:r=>{
            if(this._disposed||uni.getStorageSync('token')!==token){reject(new Error('账号已变化，请重新领取路线'));return}
            if(r.statusCode===401){uni.removeStorageSync('token');this.signIn(true);reject(new Error('登录已过期，请重新登录'));return}
            if(r.statusCode!==200){reject(new Error(typeof r.data?.detail==='string'?r.data.detail:'领取失败，请重试'));return}
            resolve(r.data)
          },fail:()=>reject(new Error('无法连接服务电脑，请确认在同一个 Wi-Fi 且后端已启动'))})
        this._requests=this._requests||[];this._requests.push(task)
      })
    },
    scan() {
      uni.scanCode({onlyFromCamera:true,success:result=>{
        if(this._disposed)return
        try { const pending=saveClaim(result.result); this.code=pending.token; this.origin=pending.origin; this.scanned=true; this.error=''; this.prepare() }
        catch(e) { this.error=e.message }
      },fail:()=>{this.error='扫码未完成，可以输入领取码'}})
    },
    async prepare() {
      if(this.busy)return
      this.snapshot=null;this.guides=[];this.pickedGuideId=0
      this.error=''
      const token=this.code.trim().replace(/\s/g,'')
      if(!/^[A-HJ-NP-Z2-9]{12}$/i.test(token)&&!/^[A-Za-z0-9_-]{32,100}$/.test(token)){this.error='领取码格式不正确';return}
      const origin=this.origin||SERVER_ORIGIN
      if(!isLocalStationOrigin(origin)){this.error='只允许连接局域网电脑的18000端口';return}
      const receipt=this.receipt(),version=this._version=(this._version||0)+1
      // 同一台电脑可能同时有局域网 IP 和 USB 反向代理地址；先看当前连接的电脑上有没有这张领取码，
      // 有就直接领取，避免无谓地切换地址并重新登录。
      this.busy=true
      try {
      if(origin!==SERVER_ORIGIN){
        const local=await this.currentServerHasClaim(token,receipt)
        if(this._disposed||version!==this._version)return
        if(!local){
        const accepted=await new Promise(resolve=>uni.showModal({title:this.t('连接服务电脑'),content:this.t('将连接 {address}，需要重新登录。请确认这是你扫码的电脑。',{address:origin}),confirmText:this.t('连接'),cancelText:this.t('取消'),success:r=>resolve(r.confirm),fail:()=>resolve(false)}))
        if(this._disposed||version!==this._version)return
        if(!accepted)return
        setStationServerOrigin(origin)
        }
      }
      saveClaim('zhiyouguide://claim?claim='+encodeURIComponent(token)+'&server='+encodeURIComponent(origin))
      if(!uni.getStorageSync('token')){this.signIn();return}
      const [preview,available]=await Promise.all([
        this.fetchClaim('/service-stations/claim/preview-app','POST',{token,receipt}),
        this.fetchClaim('/tour-session/guides?language='+(this.tourLanguage==='en'?'en':'zh'))
      ])
      if(this._disposed||version!==this._version)return
      if(!preview.snapshot?.route?.stops?.length)throw new Error('路线资料不完整，请重新扫码')
      if(!available.success)throw new Error('数字人加载失败，请重试')
      this.snapshot=preview.snapshot;this.guides=(available.data?.guide_list||[]).filter(g=>g.guide_id>0&&g.is_enabled!==false)
      } catch(e) { if(!this._disposed&&version===this._version)this.error=e.message||'领取失败，请重试' }
      finally { if(!this._disposed&&version===this._version)this.busy=false }
    },
    async beginTour() {
      if(this.busy||this._disposed)return
      if(!this.snapshot)return
      let picked=this.guides.find(g=>g.guide_id===this.pickedGuideId)
      // 只有一位可选人物时，点“开始导览”即视为选择这位，避免按钮看起来没有反应。
      if(!picked&&this.guides.length===1){picked=this.guides[0];this.pickedGuideId=picked.guide_id}
      if(!picked){
        this.error=this.guides.length?'请先选择数字人':'暂无可用数字人，请稍后重试'
        uni.showToast({title:this.error,icon:'none'})
        return
      }
      this.busy=true;this.error=''
      const ownerToken=uni.getStorageSync('token')
      try {
        const data=await this.fetchClaim('/service-stations/claim/receive-app','POST',{token:this.code.trim().replace(/\s/g,''),receipt:this.receipt(),guide_id:this.pickedGuideId})
        if(this._disposed||uni.getStorageSync('token')!==ownerToken)return
        if(!data.session_id)throw new Error('领取失败，请重试')
        const sid=data.session_id
        if(data.avatar_access_token)uni.setStorageSync('xingyun-tour-'+sid,data.avatar_access_token)
        clearPendingClaim();uni.reLaunch({url:'/pages/tour/tour?sessionId='+sid})
      } catch(e) {if(!this._disposed)this.error=e.message||'领取失败，请重试'}
      finally {if(!this._disposed)this.busy=false}
    },
    // 当前连接的电脑上是否已有这张领取码（409 表示已被领取过，同样是同一份路线数据）。
    currentServerHasClaim(token,receipt){
      return new Promise(resolve=>{
        uni.request({url:BASE_URL+'/service-stations/claim/preview',method:'POST',data:{token,receipt},timeout:8000,
          success:r=>resolve(r.statusCode===200||r.statusCode===409),fail:()=>resolve(false)})
      })
    },
    leave(){clearPendingClaim();uni.reLaunch({url:'/pages/tabs/tabs?tab=mine'})},
  },
}
</script>
<style scoped>
.claim-route{display:flex;flex-direction:column;gap:10rpx;padding:24rpx;margin:24rpx 0;border-radius:18rpx;background:var(--ng-raised,#f0edf8);font-size:28rpx;line-height:1.7;overflow-wrap:anywhere}.claim-duration{color:var(--ng-secondary,#4b5563);font-size:26rpx}
.claim-guides{display:flex;flex-wrap:wrap;justify-content:center;align-items:stretch;gap:16rpx;margin:24rpx 0}.claim-card .claim-guide{width:calc(50% - 8rpx);margin:0;padding:0;min-width:0;min-height:44px;overflow:hidden;box-sizing:border-box;border:2rpx solid var(--ng-border,#e2e8f0);border-radius:22rpx;background:transparent;text-align:left;line-height:1.5;transition:border-color 150ms ease-out,box-shadow 150ms ease-out}.claim-guide::after{border:0}.claim-guide.selected{border-color:var(--ng-accent-text,#5141ad);box-shadow:0 0 0 2rpx var(--ng-accent-text,#5141ad)}.claim-guide-image,.claim-guide-placeholder{width:100%;height:240rpx;display:flex;align-items:center;justify-content:center}.claim-guide-placeholder{font-size:70rpx;color:var(--ng-secondary)}.claim-guide-name{display:flex;align-items:center;justify-content:space-between;gap:12rpx;padding:16rpx;color:#000;background:transparent;font-size:28rpx;font-weight:600;white-space:normal;overflow-wrap:anywhere}.claim-guide-name .iconfont{flex-shrink:0;font-size:24rpx;color:var(--ng-accent-text,#5141ad)}.claim-empty{font-size:28rpx;text-align:center;padding:20rpx;line-height:1.6}@media(prefers-reduced-motion:reduce){.claim-guide{transition:none!important}}
.claim-page{padding-top:calc(24px + env(safe-area-inset-top))!important;padding-bottom:calc(24px + env(safe-area-inset-bottom))!important}
.claim-page{min-height:100vh;box-sizing:border-box;padding:32rpx 24rpx;background:#f8fafc;color:#1f2937}.claim-card{padding:36rpx 28rpx;background:#fff;border-radius:28rpx}.claim-title{display:block;font-size:38rpx;font-weight:700;text-align:center;margin-bottom:24rpx}.claim-note{display:block;font-size:26rpx;line-height:1.7;color:#64748b;overflow-wrap:anywhere;margin:20rpx 0}.claim-input{height:96rpx;padding:0 20rpx;border:1rpx solid #e2e8f0;border-radius:16rpx;font-size:30rpx;box-sizing:border-box}.server-input{font-size:24rpx}.claim-card button{margin-top:24rpx;min-height:88rpx;font-size:30rpx;border-radius:16rpx}.claim-primary{background:var(--ng-raised,#f0edf8);color:var(--ng-secondary,#4b5563)}.scan{background:#eef2ff;color:#4338ca}.cancel{background:#f8fafc;color:#64748b}.claim-error{display:block;margin-top:24rpx;color:#b42342;font-size:26rpx;line-height:1.5}
</style>
