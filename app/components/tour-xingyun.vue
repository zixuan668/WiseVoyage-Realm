<template><view class="xingyun-stage" :payload="payload" :change:payload="runtime.apply"><view id="tour-xingyun-avatar"></view><button v-show="audioBlocked" class="avatar-audio-unlock" @click="runtime.unlockAudio">{{ language==='en'?'Enable sound':'开启声音' }}</button></view></template>
<script>
export default {props:{payload:{type:Object,default:()=>({})},language:{type:String,default:'zh'}},data:()=>({audioBlocked:false}),methods:{runtimeEvent(event){if(event.state==='audio'){this.audioBlocked=event.blocked;return}if(event.state==='closed')this.audioBlocked=false;this.$emit('state',event)}}}
</script>
<script module="runtime" lang="renderjs">
import {loadXingyunSdk} from '../common/xingyun-sdk.js'
import {createAvatarAudioController} from '../common/avatar-audio.js'
let avatar=null,generation=0,timer=null,ready=false,gateway='',pending='',ownerRef=null
let audioController=null
let releasing=Promise.resolve()
function release(){
  generation++;clearTimeout(timer);ready=false;gateway='';pending=''
  const previous=avatar,previousAudio=audioController;avatar=null;audioController=null
  releasing=releasing.then(()=>previous&&previous.destroy()).catch(()=>{}).finally(()=>previousAudio&&previousAudio.release())
  return releasing
}
export default {
  methods:{
    unlockAudio(){if(audioController)return audioController.unlock()},
    async apply(value,old,owner){
      ownerRef=owner
      if(!value||value.command==='close'){
        const closing=release(),current=generation
        await closing
        const container=document.getElementById('tour-xingyun-avatar')
        if(current===generation&&container)container.innerHTML=''
        if(owner)owner.callMethod('runtimeEvent',{state:'closed',id:value&&value.id})
        return
      }
      if(value.command==='stop'){pending='';if(ready&&avatar)try{avatar.interactiveidle()}catch(e){}return}
      if(!value.gateway)return
      if(gateway===value.gateway){
        if(value.command==='speak'){pending=value.text||'';if(ready&&avatar){const text=pending;pending='';console.log('[tour-audio] speak',JSON.stringify(audioController&&audioController.describe()));avatar.interactiveidle();avatar.speak(text,true,true)}}
        return
      }
      const closing=release(),version=generation
      await closing
      if(version!==generation)return
      gateway=value.gateway;pending=value.text||''
      const current=generation
      const report=(state,message)=>{if(current===generation&&ownerRef){if(state==='error')console.error('[tour-xingyun]',message);ownerRef.callMethod('runtimeEvent',{state,message,gateway:value.gateway})}}
      const fail=message=>{if(current!==generation)return;report('error',message);release()}
      const connected=()=>{
        if(current!==generation||ready)return
        ready=true;clearTimeout(timer);console.log('[tour-audio] connected',JSON.stringify(audioController&&audioController.describe()));report('connected')
        if(pending){const text=pending;pending='';avatar.speak(text,true,true)}
      }
      report('connecting')
      timer=setTimeout(()=>fail('星云连接超时，请检查网络后重试'),60000)
      try{
        audioController=createAvatarAudioController(window,document,blocked=>{if(current===generation&&ownerRef)ownerRef.callMethod('runtimeEvent',{state:'audio',blocked:blocked})},{streamOutput:value.audioOutput==='media-stream'})
        await loadXingyunSdk()
        if(current!==generation)return
        const headers=value.accessToken?{'X-Tour-Access':value.accessToken}:{Authorization:'Bearer '+value.token}
        avatar=new window.XmovAvatar({containerId:'#tour-xingyun-avatar',appId:'server-proxy',appSecret:'server-proxy',gatewayServer:value.gateway,headers,
          hardwareAcceleration:'prefer-hardware',
          proxyWidget:{subtitle_on:()=>{},subtitle_off:()=>{}},
          onInitEvent:code=>{if(code===4000)connected()},
          onStateChange:state=>{if(state==='idle'||state==='interactive_idle')connected()},
          onVoiceStateChange:state=>{console.log('[tour-audio] voice',state,JSON.stringify(audioController&&audioController.describe()));if(String(state).includes('start'))report('playing');if(String(state).includes('end'))report('ended')},
          onMessage:error=>{if(error.code&&error.code!==4000)fail((error.message||'星云服务连接失败')+'（错误码：'+error.code+'）')},
        })
        await avatar.init({onDownloadProgress:progress=>report('progress','正在加载星云形象 '+Math.round(progress)+'%'),onClose:()=>{if(current===generation)fail('星云连接已断开，请重试')}})
      }catch(e){if(current===generation)fail(e.message||'星云连接失败')}
    },
  },
  beforeUnmount(){release()},
}
</script>
<style scoped>
.xingyun-stage{position:absolute;inset:0;z-index:1;overflow:hidden;border-radius:24rpx;background:transparent}
.avatar-audio-unlock{position:absolute;right:20rpx;bottom:16rpx;z-index:6;min-height:44px;padding:0 24rpx;margin:0;display:flex;align-items:center;justify-content:center;border:1rpx solid #c7d2fe;border-radius:24rpx;background:#fff;color:#5145cd;font-size:26rpx;line-height:1.4}
#tour-xingyun-avatar{position:relative;width:100%;height:100%;transform:translateX(0)}
/* Match the native SDK canvas by attributes: uni-app rewrites canvas selectors.
   Keep remote scale/offset settings from moving the centered display frame. */
#tour-xingyun-avatar :deep([width][height]){position:absolute!important;inset:0!important;width:100%!important;height:100%!important;max-width:100%!important;max-height:100%!important;min-width:0!important;min-height:0!important;margin:0!important;transform:none!important;object-fit:contain!important;object-position:50% 50%!important}
</style>
