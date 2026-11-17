<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { request_handler } from '@/api/base'
import { getRouteOverview } from '@/api/tourExperience'
import { saveAvatarToken, avatarHeaders } from '@/api/xingyunTour'
import { createScenicMotion } from '@/utils/scenicMotion'
import DigitalAvatarPlayer from '@/components/DigitalAvatarPlayer.vue'
import covers from '@/data/scenicCoverImages.json'

const motion=createScenicMotion()
const pageEl=ref<HTMLElement|null>(null)
let sharedPhoto=false
const props = defineProps<{ spotIds:number[] }>()
const emit = defineEmits<{ title:[value:string] }>()
const route=useRoute(), router=useRouter()
const native = () => (window as any).plus
const stage=ref('choose'), busy=ref(false), error=ref('')
type Guide={guide_id:number;name:string;character:string;avatar:string;poster_image:string}
type Stop={spot_id:number;spot_name:string;latitude:number;longitude:number;description:string;trigger_radius:number}
type Arrival={arrival_id:string;spot_id:number;created_at:string}
type Journey={id:string;mode:string;guide_id?:number;tour_id?:number;ended:boolean;avoid_steps:boolean;spots:Stop[];arrivals:Arrival[];review:unknown}
const guides=ref<Guide[]>([]), selected=ref<number>(), journey=ref<Journey>()
const active=ref(0), card=ref<Arrival>(), message=ref(''), answer=ref('')
const quick=ref<number>(), satisfaction=ref<number>(), tags=ref<string[]>([]), recommendation=ref(8)
const tagOptions=['讲解清楚','路线方便','风景优美','内容有趣','定位不准','讲解需改进','步行较累']
const tagIcons:Record<string,string>={
  '讲解清楚':'M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM6 11a6 6 0 0 0 12 0M12 17v4M9 21h6',
  '路线方便':'M6 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM18 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM8 17c0-4 8-2 8-6',
  '风景优美':'M3 20l5-9 4 6 3-5 6 8H3zM17 5l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2z',
  '内容有趣':'M12 3l1.6 4.8L18 9.4l-4.4 1.6L12 16l-1.6-5L6 9.4l4.4-1.6L12 3zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15z',
  '定位不准':'M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11zM12 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  '讲解需改进':'M4 5h16v11H9l-5 4V5zM8 9h8M8 12h5',
  '步行较累':'M8 5c0-1 .7-2 1.8-2S11 4 11 5s-.7 2-1.2 2S8 6 8 5zM7 21l1.5-6 2.5-2 1 3 2 1M13 21l-.5-5'
}
const positiveTags=['讲解清楚','路线方便','风景优美','内容有趣']
const negativeTags=['定位不准','讲解需改进','步行较累']
const visibleTags=computed(()=> quick.value===2?positiveTags:quick.value===0?negativeTags:[...positiveTags,...negativeTags])
const endpoint='/tour-experience'
const current=computed(()=>journey.value?.spots[active.value])
const coverMap:Record<string,{url:string}>=covers
const photo=computed(()=>coverMap[current.value?.spot_name || '']?.url)
const location=ref<{latitude:number;longitude:number;accuracy:number}|null>(null)
const locationError=ref(''), locating=ref(false)
const distance=computed(()=>{
 const a=location.value,b=current.value
 if(!a||!b?.latitude||!b.longitude)return null
 const rad=Math.PI/180, x=(b.latitude-a.latitude)*rad, y=(b.longitude-a.longitude)*rad
 return Math.round(6371000*2*Math.asin(Math.min(1,Math.sqrt(Math.sin(x/2)**2+Math.cos(a.latitude*rad)*Math.cos(b.latitude*rad)*Math.sin(y/2)**2))))
})
const direction=computed(()=>{
 const a=location.value,b=current.value
 if(!a||!b)return ''
 const rad=Math.PI/180, d=(b.longitude-a.longitude)*rad
 const angle=(Math.atan2(Math.sin(d)*Math.cos(b.latitude*rad),Math.cos(a.latitude*rad)*Math.sin(b.latitude*rad)-Math.sin(a.latitude*rad)*Math.cos(b.latitude*rad)*Math.cos(d))/rad+360)%360
 return ['北','东北','东','东南','南','西南','西','西北'][Math.round(angle/45)%8]
})
const arrived=computed(()=>journey.value?.arrivals.find(a=>a.spot_id===current.value?.spot_id))
const titles:Record<string,string>={choose:'选择伴游',guide:'伴游讲解',walk:'地图步行',arrival:'到达打卡',card:'探索卡片',quick:'结束评价',tags:'满意标签',done:'评价完成'}
watch(stage,async(v,previous)=>{
 emit('title',titles[v] || '游览');error.value=''
 if(previous&&!sharedPhoto){
  const old=motion.snapshot(pageEl.value)
  await nextTick()
  motion.enter(pageEl.value,old,['arrival','card','tags'].includes(previous)&&['guide','walk','quick'].includes(v))
 }
 if(v==='walk')void drawMap()
},{immediate:true})
async function action(work:()=>Promise<void>){
 if(busy.value)return
 busy.value=true;error.value=''
 try{await work()}catch(e:any){error.value=e.response?.data?.detail||e.response?.data?.message||e.message||'加载失败，请重试'}finally{busy.value=false}
}
function guidePhoto(g:Guide){
 const raw=g.avatar||g.poster_image||''
 if(!raw)return ''
 // 后端文件地址常写成 localhost:8000，手机访问不到，改成同源相对路径走代理
 return raw.replace(/^https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?/i,'')
}
async function loadGuides(){await action(async()=>{guides.value=(await request_handler.get(endpoint+'/companions')).data})}
async function start(mode:'walk'|'guide'){
 if(mode==='guide'&&!selected.value){error.value='请先选择一位伴游，再开始讲解';return}
 await action(async()=>{
  const response=await request_handler.post(endpoint+'/journeys',{spot_ids:props.spotIds,mode,guide_id:mode==='guide'?selected.value:undefined})
  const data=response.data
  if(data.tour_id)saveAvatarToken(data.tour_id,data.access_token)
  const host=window as any
  const appNav=mode==='guide'&&host.plus&&data.tour_id&&host.uni
  if(appNav){
   const chosen=guides.value.find(g=>g.guide_id===selected.value)
   const poster=chosen?guidePhoto(chosen):''
   const url='/pages/tour/tour?sessionId='+encodeURIComponent(data.tour_id)
     +'&poster='+encodeURIComponent(poster)+'&guideName='+encodeURIComponent(chosen?.name||'')
     +'&access='+encodeURIComponent(data.access_token||'')
   try{
    if(typeof host.uni.navigateTo==='function')host.uni.navigateTo({url})
    else if(typeof host.uni.postMessage==='function')host.uni.postMessage({data:{type:'open-tour-page',sessionId:data.tour_id}})
   }catch(e){}
   // 跳转前不渲染页内数字人，避免闪一下；只有跳转失败才回落
   setTimeout(()=>{
    if(document.visibilityState!=='hidden'){
     void router.replace({query:{...route.query,journey:data.id}})
     void restore(data.id,pageEl.value?.querySelector<HTMLElement>('.guide-card.selected'))
    }
   },1200)
   return
  }
  await router.replace({query:{...route.query,journey:data.id}})
  await restore(data.id,mode==='guide'?pageEl.value?.querySelector<HTMLElement>('.guide-card.selected'):undefined)
 })
}
async function restore(id:string,source?:HTMLElement|null){
 journey.value=(await request_handler.get(endpoint+'/journeys/'+id)).data
 const j=journey.value!
 active.value=Math.max(0,j.spots.findIndex(s=>!j.arrivals.some(a=>a.spot_id===s.spot_id)))
 if(source){sharedPhoto=true;motion.photo(source,()=>pageEl.value?.querySelector<HTMLElement>('.avatar-stage')||null)}
 stage.value=j.review?'done':j.ended?'quick':j.mode
 await nextTick()
 sharedPhoto=false
}
function locate(){
 if(locating.value)return
 locating.value=true;locationError.value=''
 const success=(p:any)=>{
  location.value={latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy};locating.value=false;void drawMap()
 }
 const failure=()=>{locating.value=false;locationError.value='定位失败，请允许定位权限并到室外重试'}
 if(native()?.geolocation){native().geolocation.getCurrentPosition(success,failure,{enableHighAccuracy:true,timeout:15000,coordsType:'wgs84'});return}
 navigator.geolocation.getCurrentPosition(p=>{
  location.value={latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy};locating.value=false;void drawMap()
 },e=>{locating.value=false;locationError.value=e.code===1?'请允许定位后重试':'暂时无法获取定位，请到室外重试'},{enableHighAccuracy:true,timeout:15000,maximumAge:5000})
}
let watchId:number|undefined
let nativeWatch:string|undefined
function watchLocation(){
 if(native()?.geolocation){nativeWatch=native().geolocation.watchPosition((p:any)=>{
 location.value={latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy};void drawMap()
 },()=>{locationError.value='定位未就绪，可点击重新定位'},{enableHighAccuracy:true,coordsType:'wgs84'});return}
 if(!navigator.geolocation){locationError.value='当前设备不支持定位';return}
 watchId=navigator.geolocation.watchPosition(p=>{
 location.value={latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy};void drawMap()
 },()=>{locationError.value='定位未就绪，可点击重新定位'},{enableHighAccuracy:true,timeout:20000,maximumAge:5000})
}
async function checkIn(){
 await action(async()=>{
  if(!location.value||!current.value)throw Error('请先获取当前位置')
  card.value=(await request_handler.post(endpoint+'/journeys/'+journey.value!.id+'/arrivals',{spot_id:current.value.spot_id,...location.value})).data
  journey.value!.arrivals=(await request_handler.get(endpoint+'/journeys/'+journey.value!.id)).data.arrivals
  const device=typeof route.query.device==='string'?route.query.device:''
  const token=sessionStorage.getItem('scenic-app-token')||''
  if((device||token)&&current.value){
   const headers:Record<string,string>={'X-Device-Id':device}
   if(token)headers.Authorization='Bearer '+token
   await request_handler.post('/checkins',{spot_id:current.value.spot_id,time:new Date().toISOString()},{headers}).catch(()=>{})
  }
  const host=window as any
  if(host.plus&&host.uni?.postMessage&&current.value){
   host.uni.postMessage({data:{type:'save-checkin',spot:current.value.spot_name,time:new Date().toISOString()}})
  }
  const source=pageEl.value?.querySelector<HTMLElement>('.arrival-cover')
  if(source){sharedPhoto=true;motion.photo(source,()=>pageEl.value?.querySelector<HTMLElement>('.explore-card img')||null)}
  stage.value='card'
  await nextTick()
  sharedPhoto=false
 })
}
async function end(){await action(async()=>{await request_handler.put(endpoint+'/journeys/'+journey.value!.id+'/end');journey.value!.ended=true;stage.value='quick'})}
function toggleTag(tag:string){tags.value=tags.value.includes(tag)?tags.value.filter(t=>t!==tag):[...tags.value,tag]}
async function review(){await action(async()=>{
 await request_handler.put(endpoint+'/journeys/'+journey.value!.id+'/review',{quick:quick.value,satisfaction:satisfaction.value,tags:tags.value,recommendation:recommendation.value})
 stage.value='done'
})}
const avatar=ref<InstanceType<typeof DigitalAvatarPlayer>|null>(null)
async function ask(){if(!message.value.trim()||!journey.value?.tour_id)return
 await action(async()=>{
 const id=journey.value!.tour_id!
 const result=(await request_handler.put('/tour-session/chat',{sessionId:id,message:message.value,currentSpotId:current.value?.spot_id,text_only:true},{headers:avatarHeaders(id)})).data
 if(!result.success)throw Error(result.message)
 answer.value=result.data.message || ''
 message.value=''
 if(answer.value)avatar.value?.speak(answer.value)
 })}
async function exportCard(share=false){await action(async()=>{
 if(!card.value||!current.value)throw Error('请先完成打卡')
 const canvas=document.createElement('canvas');canvas.width=720;canvas.height=960
 const ctx=canvas.getContext('2d')!;ctx.fillStyle='#f6f3ef';ctx.fillRect(0,0,720,960)
 if(photo.value){const img=new Image();img.src=photo.value;await img.decode();ctx.drawImage(img,24,24,672,610)}
 ctx.fillStyle='#282332';ctx.font='36px system-ui';ctx.fillText(current.value.spot_name,36,700)
 ctx.font='22px system-ui';ctx.fillText('到达打卡 · '+new Date(card.value.created_at).toLocaleDateString(),36,753)
 ctx.fillText('智游知境',36,870)
 const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('生成卡片失败')),'image/png'))
 if(native()?.nativeObj?.Bitmap){
  const api=native(), bitmap=new api.nativeObj.Bitmap('exploration-'+card.value.arrival_id)
  const path='_doc/exploration-'+card.value.arrival_id+'.png'
  try{
   await new Promise<void>((resolve,reject)=>bitmap.loadBase64Data(canvas.toDataURL('image/png'),resolve,reject))
   await new Promise<void>((resolve,reject)=>bitmap.save(path,{overwrite:true},resolve,reject))
   if(share&&api.share?.sendWithSystem)await new Promise<void>((resolve,reject)=>api.share.sendWithSystem({type:'image',pictures:[path]},resolve,reject))
   else {await new Promise<void>((resolve,reject)=>api.gallery.save(path,resolve,reject));error.value='卡片已保存到相册'}
  }finally{bitmap.clear()}
  return
 }
 const file=new File([blob],'探索卡片.png',{type:'image/png'})
 if(share&&navigator.canShare?.({files:[file]})){await navigator.share({files:[file],title:current.value.spot_name});return}
 const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=file.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
})}
const mapEl=ref<HTMLElement|null>(null)
let routeGeometry:number[][][]=[]
let map:any, layer:any, mapError=ref(''),mapVersion=0
async function drawMap(){
 const own=++mapVersion;await nextTick()
 if(stage.value!=='walk'||!mapEl.value||!journey.value)return
 try{
 const util=await import('@/utils/leaflet'),coord=await import('../../../../shared/coordinates.js')
 const L=await util.loadScenicMap()
 if(own!==mapVersion||!mapEl.value)return
 if(!map||map.getContainer()!==mapEl.value){map?.remove();map=L.map(mapEl.value,{zoomControl:false});L.tileLayer(util.SCENIC_TILES,{maxZoom:19}).addTo(map);layer=L.layerGroup().addTo(map)}
 layer.clearLayers()
 const points:any[]=[]
 if(!routeGeometry.length){const result=(await getRouteOverview(journey.value.spots.map(s=>s.spot_id),journey.value.avoid_steps?'relaxed':'standard',undefined,{avoid_steps:journey.value.avoid_steps})).data.data;routeGeometry=result.legs.map(l=>l.geometry||[])}
 for(const geometry of routeGeometry){if(geometry.length)L.polyline(geometry.map(([lat,lng])=>coord.wgs84ToGcj02(lat,lng)),{color:'#6957cd',weight:5}).addTo(layer)}
 for(const s of journey.value.spots){if(!s.latitude||!s.longitude)continue;const p=coord.wgs84ToGcj02(s.latitude,s.longitude);points.push(p);L.marker(p).addTo(layer).bindPopup(s.spot_name)}
 if(location.value){const p=coord.wgs84ToGcj02(location.value.latitude,location.value.longitude);points.push(p);L.circleMarker(p,{radius:7,color:'#6352cc'}).addTo(layer)}
 if(points.length){map.fitBounds(L.latLngBounds(points),{padding:[28,28],maxZoom:17});map.invalidateSize()}
 }catch{mapError.value='地图加载失败，请重试'}
}
function back(){
 if(['arrival','card'].includes(stage.value))stage.value=journey.value?.mode || 'walk'
 else if(stage.value==='tags')stage.value='quick'
 else if(stage.value==='done')void router.replace({query:{...route.query,view:'plan',journey:undefined}})
 else if(journey.value&&!journey.value.ended)stage.value=journey.value.mode
 else void router.replace({query:{...route.query,view:'plan',journey:undefined}})
}
defineExpose({back})
onMounted(()=>{watchLocation();const id=String(route.query.journey||'');if(id)void action(()=>restore(id));else void loadGuides()})
onBeforeUnmount(()=>{motion.cancel();if(nativeWatch!==undefined)native()?.geolocation?.clearWatch(nativeWatch);if(watchId!==undefined)navigator.geolocation.clearWatch(watchId);mapVersion++;map?.remove()})
</script>

<template>
 <section ref="pageEl" class="journey">
  <p v-if="error" class="error" role="alert">{{error}}</p>
  <template v-if="stage==='choose'">
   <div class="guide-grid"><button v-for="g in guides" :key="g.guide_id" class="guide-card" :class="{selected:selected===g.guide_id}" @click="selected=g.guide_id">
    <img v-if="guidePhoto(g)" :src="guidePhoto(g)" alt="" @error="($event.target as HTMLImageElement).style.display='none'"><strong>{{g.name}}</strong><span>{{g.character}}</span>
   </button></div>
   <div v-if="busy&&!guides.length" class="guide-skeleton" aria-busy="true" aria-label="伴游加载中">
     <div v-for="n in 2" :key="n" class="guide-sk-card"><div class="sk-photo"></div><div class="sk-name"></div></div>
   </div>
   <p v-if="!busy&&!guides.length">暂无可用伴游。</p>
   <button v-if="error" @click="loadGuides">重新加载伴游</button>
   <footer><button class="primary" :disabled="busy" @click="start('guide')">伴游讲解</button></footer>
  </template>
  <template v-else-if="stage==='guide'||stage==='walk'">
   <div v-if="stage==='guide'" class="avatar-stage"><DigitalAvatarPlayer ref="avatar" :guide-id="journey?.guide_id" :tour-id="journey?.tour_id"/><p v-if="answer" class="answer">{{answer}}</p></div>
   <template v-else><div ref="mapEl" class="walking-map"></div><button v-if="mapError" @click="drawMap">{{mapError}}</button></template>
   <div class="destination"><span>第 {{active+1}} 站 / {{journey?.spots.length}} 站</span><h2>{{current?.spot_name}}</h2>
    <p>{{distance===null?'等待定位':distance+' 米 · '+direction+'方向'}} <small v-if="location">定位精度 {{Math.round(location.accuracy)}} 米</small></p>
    <p v-if="locationError">{{locationError}}</p><button :disabled="locating" @click="locate">{{locating?'正在定位…':'重新定位'}}</button>
   </div>
   <form v-if="stage==='guide'" class="chat" @submit.prevent="ask"><input v-model="message" maxlength="2000" placeholder="想了解什么？"><button :disabled="busy||!message.trim()">发送</button></form>
   <footer><button :disabled="busy" @click="end">结束评价</button><button class="primary" @click="stage='arrival'">{{arrived?'查看打卡':'到达打卡'}}</button></footer>
  </template>
  <template v-else-if="stage==='arrival'">
   <img v-if="photo" class="arrival-cover" :src="photo" alt=""><h2>{{current?.spot_name}}</h2><p>{{distance===null?'请先获取定位': '距离景点 '+distance+' 米'}}</p>
   <p v-if="locationError">{{locationError}}</p><button @click="locate">更新定位</button>
   <p class="muted">到达景点附近后确认打卡</p>
   <button class="primary wide" :disabled="busy||!location||location.accuracy>100||distance===null" @click="checkIn">{{arrived?'查看探索卡片':'确认到达'}}</button>
  </template>
  <template v-else-if="stage==='card'">
   <article class="explore-card"><img v-if="photo" :src="photo" alt=""><span>探索卡片</span><h2>{{current?.spot_name}}</h2><p>{{new Date(card?.created_at||arrived?.created_at||'').toLocaleString()}}</p><p>{{current?.description}}</p></article>
   <div class="pair"><button :disabled="busy" @click="exportCard()">保存卡片</button><button :disabled="busy" @click="exportCard(true)">分享卡片</button></div>
   <button v-if="journey&&active<journey.spots.length-1" class="primary wide" @click="active++;stage=journey.mode;answer=''">下一站</button>
   <button v-else class="primary wide" :disabled="busy" @click="end">结束评价</button>
  </template>
  <template v-else-if="stage==='quick'">
   <h2>这次游览怎么样？</h2>
   <div class="expressions"><button v-for="(item,i) in ['不太满意','一般','很满意']" :key="item" :class="{selected:quick===i}" @click="quick=i;satisfaction=i"><span>{{['☹','😐','☺'][i]}}</span>{{item}}</button></div>
   <template v-if="quick!==undefined">
    <p class="section-label">哪些地方让你有这种感觉？</p>
    <div class="tag-grid"><button v-for="tag in visibleTags" :key="tag" :class="{selected:tags.includes(tag)}" @click="toggleTag(tag)">
      <svg class="tag-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path :d="tagIcons[tag]"/></svg>{{ tag }}
    </button></div>
    <label class="recommend">你愿意推荐这次游览吗？<strong>{{recommendation}} / 10</strong><input v-model.number="recommendation" type="range" min="0" max="10" step="1"></label>
   </template>
   <footer><button class="primary" :disabled="busy||quick===undefined" @click="review">{{busy?'正在提交…':'提交评价'}}</button></footer>
  </template>
  <template v-else-if="stage==='tags'">
   <h2>留下你的感受</h2><div class="pair"><button v-for="(item,i) in ['不满意','一般','满意']" :key="item" :class="{selected:satisfaction===i}" @click="satisfaction=i">{{item}}</button></div>
   <div class="tag-grid"><button v-for="tag in tagOptions" :key="tag" :class="{selected:tags.includes(tag)}" @click="toggleTag(tag)">{{tag}}</button></div>
   <label class="recommend">你愿意推荐这次游览吗？<strong>{{recommendation}} / 10</strong><input v-model.number="recommendation" type="range" min="0" max="10" step="1"></label>
   <button class="primary wide" :disabled="busy||satisfaction===undefined" @click="review">{{busy?'正在提交…':'提交评价'}}</button>
  </template>
  <template v-else-if="stage==='done'"><div class="completed"><span>✓</span><h2>评价已保存</h2><p>谢谢你的反馈</p></div><footer><button class="primary" @click="back">返回路线</button></footer></template>
 </section>
</template>

<style scoped>
.journey{height:100%;overflow-y:auto;box-sizing:border-box;padding:20px 18px calc(10px + env(safe-area-inset-bottom,0px));color:#282332;font-family:var(--app-font-family,system-ui);display:flex;flex-direction:column;background:linear-gradient(160deg,#f8f5ff 0%,#f1edfe 52%,#edf3fb 100%)}
button,input{font:inherit}button{-webkit-tap-highlight-color:transparent;min-height:44px;border:1px solid #ded9e5;border-radius:13px;padding:10px 15px;background:#fff;color:inherit;cursor:pointer;transition:transform 140ms ease-out,background 140ms}
button:active{transform:scale(.96)}button:disabled{opacity:.45;cursor:default}h2{font-size:24px;font-weight:600;line-height:1.4;margin:12px 0}p{font-size:14px;line-height:1.7}.muted,.mode-heading p{color:#80798a}.error{background:#fff0ee;border-radius:12px;padding:12px;color:#9c403c}
.primary{background:#6957cd;border-color:#6957cd;color:white}.wide{width:100%;margin-top:20px}.selected{border-color:#6957cd!important;background:#eee9ff!important}
.guide-skeleton{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:24px 0}
.guide-sk-card{padding:12px;display:flex;flex-direction:column;gap:10px;border-radius:18px;border:1px solid rgba(130,110,210,.12);background:#fff}
.guide-skeleton .sk-photo{height:150px;border-radius:16px;background:linear-gradient(90deg,#f0edf8 25%,#fafafe 37%,#f0edf8 63%);background-size:400% 100%;animation:guide-sk-shimmer 1.4s ease infinite}
.guide-skeleton .sk-name{height:18px;width:60%;margin:0 auto;border-radius:9px;background:linear-gradient(90deg,#f0edf8 25%,#fafafe 37%,#f0edf8 63%);background-size:400% 100%;animation:guide-sk-shimmer 1.4s ease infinite}
@keyframes guide-sk-shimmer{0%{background-position:100% 0}100%{background-position:0 0}}
@media(prefers-reduced-motion:reduce){.guide-skeleton .sk-photo,.guide-skeleton .sk-name{animation:none}}
.guide-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:24px 0}.guide-card{padding:12px;display:flex;flex-direction:column;gap:8px;text-align:left;border-radius:18px;border:1px solid rgba(130,110,210,.18);background:linear-gradient(135deg,rgba(255,255,255,.96),rgba(249,246,255,.9));box-shadow:0 6px 18px -14px rgba(40,30,70,.3);transition:border-color .18s,box-shadow .18s,background .18s}
.guide-card.selected{border:1.5px solid #8b78e6!important;background:linear-gradient(135deg,#fff,#f1ecff)!important;box-shadow:0 10px 24px -16px rgba(90,70,180,.5)!important}.guide-card img{width:100%;height:150px;object-fit:cover;border-radius:16px;background:#fff}
.guide-card strong{width:100%;text-align:center;font-size:18px;font-weight:600}
.guide-card span{width:100%;text-align:center;font-size:12px;color:#777;line-height:1.6}
footer{display:flex;gap:10px;position:sticky;bottom:0;margin-top:auto;padding:10px 0 calc(6px + env(safe-area-inset-bottom,0px));background:linear-gradient(180deg,rgba(241,237,254,0),rgba(241,237,254,.96) 38%);backdrop-filter:blur(10px);z-index:4}footer button{flex:1}
/* 选择方式按钮：白色，按下瞬间浅紫 */
.journey footer button,.journey footer button.primary{background:linear-gradient(135deg,rgba(255,255,255,.96),rgba(248,246,255,.9));color:#282332;border:1px solid rgba(130,110,210,.34);box-shadow:inset 0 1px 0 #fff,0 6px 16px -12px rgba(40,30,70,.3)}
.journey footer button:active,.journey footer button.primary:active{background:#ece7ff;border-color:#c9bff0}
/* 两个按钮同色，不因禁用/未选而变成另一种颜色 */
.journey footer button:disabled{opacity:1;color:#282332;background:linear-gradient(135deg,rgba(255,255,255,.96),rgba(248,246,255,.9));border-color:rgba(130,110,210,.34)}
.walking-map{height:35vh;min-height:180px;border-radius:18px;overflow:hidden;background:#e9e6df}.destination{padding:15px 0}.destination>span,small{font-size:12px;color:#82798b}.destination small{display:block}.chat{display:flex;gap:8px}.chat input{min-width:0;flex:1;padding:10px;border:1px solid #ded9e5;border-radius:12px}
.avatar-stage{min-height:220px}.answer{padding:12px;background:white;border-radius:12px}.arrival-cover{width:100%;height:30vh;object-fit:cover;border-radius:20px}
.explore-card{border-radius:20px;background:#fff;padding:12px;box-shadow:0 8px 28px #30233a12}.explore-card img{width:100%;height:32vh;object-fit:cover;border-radius:13px}.explore-card>span{display:block;font-size:12px;color:#82798b;margin-top:16px}.pair{display:flex;gap:8px;margin:20px 0}.pair button{flex:1}
.expressions{display:flex;gap:8px;margin:28px 0 8px}.expressions button{flex:1;font-size:13px;padding:12px 5px}.expressions span{display:block;font-size:38px;margin-bottom:12px}
.section-label{margin:20px 0 6px;font-size:14px;color:#7d7590}
.tag-grid{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0 18px}
.tag-grid button{display:inline-flex;align-items:center;gap:6px;min-height:40px;padding:8px 14px;border-radius:12px;background:linear-gradient(135deg,rgba(255,255,255,.96),rgba(248,246,255,.9));border:1px solid rgba(130,110,210,.24);color:#38304c;box-shadow:inset 0 1px 0 #fff,0 4px 12px -10px rgba(40,30,70,.28)}
.tag-grid button.selected{background:#f0ebff;border-color:#8b78e6;color:#44358f;box-shadow:inset 0 1px 0 #fff,0 6px 14px -12px rgba(90,70,180,.35)}
.tag-icon{width:16px;height:16px;flex:none}
.tag-grid{display:flex;flex-wrap:wrap;gap:8px;margin:28px 0}.recommend{display:flex;flex-direction:column;gap:20px;line-height:1.6}.recommend input{width:100%;accent-color:#6957cd}.completed{text-align:center;margin-top:20vh}.completed>span{display:inline-grid;place-items:center;width:64px;height:64px;border-radius:50%;background:#e9e4fb;color:#6957cd;font-size:32px}
@media(prefers-reduced-motion:reduce){button{transition:none}}
</style>
