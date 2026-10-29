<template><view class="xingyun-stage" :payload="payload" :change:payload="runtime.apply"><view id="tour-xingyun-avatar"></view></view></template>
<script>
export default {props:{payload:{type:Object,default:()=>({})}},methods:{runtimeEvent(event){this.$emit('state',event)}}}
</script>
<script module="runtime" lang="renderjs">
import { loadXingyunSdk } from '../common/xingyun-sdk.js'
let avatar=null,generation=0,timer=null,ready=false,gateway='',pending='',ownerRef=null,closing=Promise.resolve()
// 旧实例的 destroy 必须完成后再创建新实例，避免快速重连时两个 SDK 同时占用同一个画布。
function release(){
  generation++
  clearTimeout(timer)
  ready=false;gateway='';pending=''
  const previous=avatar
  avatar=null
  if(previous){try{closing=closing.then(()=>previous.destroy()).catch(()=>{})}catch(e){closing=Promise.resolve()}}
  return closing
}
export default {
  methods:{
    async apply(value,old,owner){
      ownerRef=owner
      if(!value||value.command==='close'){
        const disposing=release(),current=generation
        await disposing
        const container=document.getElementById('tour-xingyun-avatar')
        if(current===generation&&container)container.innerHTML=''
        if(owner)owner.callMethod('runtimeEvent',{state:'closed',id:value&&value.id})
        return
      }
      if(value.command==='stop'){pending='';if(ready&&avatar)try{avatar.interactiveidle()}catch(e){}return}
      if(!value.gateway)return
      if(gateway===value.gateway){
        if(value.command==='speak'){pending=value.text||'';if(ready&&avatar){const text=pending;pending='';avatar.interactiveidle();avatar.speak(text,true,true)}}
        return
      }
      const disposing=release(),version=generation
      await disposing
      if(version!==generation)return
      gateway=value.gateway;pending=value.text||''
      const current=generation
      const report=(state,message)=>{if(current===generation&&ownerRef){if(state==='error')console.error('[tour-xingyun]',message);ownerRef.callMethod('runtimeEvent',{state,message,gateway:value.gateway})}}
      const fail=message=>{if(current!==generation)return;report('error',message);release()}
      const connected=()=>{
        if(current!==generation||ready)return
        ready=true;clearTimeout(timer);report('connected')
        if(pending){const text=pending;pending='';avatar.speak(text,true,true)}
      }
      report('connecting')
      timer=setTimeout(()=>fail('星云连接超时，请检查网络后重试'),60000)
      try{
        // 使用随 App 打包的兼容 SDK，不再加载线上 @latest，避免 Android 硬件解码检查失败。
        if(!window.XmovAvatar)await loadXingyunSdk()
        if(current!==generation)return
        if(typeof window.XmovAvatar!=='function')throw new Error('数字人资源加载失败，请重新连接')
        const headers=value.accessToken?{'X-Tour-Access':value.accessToken}:{Authorization:'Bearer '+value.token}
        const instance=new window.XmovAvatar({containerId:'#tour-xingyun-avatar',appId:'server-proxy',appSecret:'server-proxy',gatewayServer:value.gateway,headers,
          hardwareAcceleration:'prefer-hardware',
          proxyWidget:{subtitle_on:()=>{},subtitle_off:()=>{}},
          onInitEvent:code=>{if(code===4000)connected()},
          onStateChange:state=>{if(state==='idle'||state==='interactive_idle')connected()},
          onVoiceStateChange:state=>{if(String(state).includes('start'))report('playing');if(String(state).includes('end'))report('ended')},
          onMessage:error=>{
            if(!error.code||error.code===4000)return
            const code=Number(error.code)
            // 星云云端错误码 5 = 账号积分不足/欠费；原始文案带 Error 前缀，换成可操作说明。
            const message=code===5?'星云账号积分不足，请充值后重试':(error.message||'星云服务连接失败')
            fail(message+'（错误码：'+code+'）')
          },
        })
        avatar=instance
        await instance.init({onDownloadProgress:progress=>report('progress','正在加载星云形象 '+Math.round(progress)+'%'),onClose:()=>{if(current===generation)fail('星云连接已断开，请重试')}})
        if(current===generation)connected()
      }catch(e){if(current===generation)fail(e.message||'星云连接失败')}
    },
  },
  beforeUnmount(){release()},
}
</script>
<style scoped>
.xingyun-stage{position:absolute;inset:0;z-index:1;overflow:hidden;border-radius:24rpx;background:transparent}
#tour-xingyun-avatar{position:absolute;inset:0;width:100%;height:100%;transform:translateX(0)}
/* SDK 会按资源像素、缩放和横向位移写入内联样式；统一铺满显示区域并等比例完整显示源画面。 */
#tour-xingyun-avatar :deep([width][height]){position:absolute!important;inset:0!important;width:100%!important;height:100%!important;min-width:0!important;min-height:0!important;max-width:100%!important;max-height:100%!important;margin:0!important;padding:0!important;border:0!important;transform:none!important;object-fit:contain!important;object-position:50% 50%!important}
</style>
