<script setup lang="ts">
import { ArrowUpRight, ArrowDown, Bottom, iconMarkup } from '@/icons'
import { computed, ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { t, locale } from '@/i18n'
import { getRouteOverview, type RouteOverviewData } from '@/api/tourExperience'
import { loadScenicMap, SCENIC_TILES } from '@/utils/leaflet'
import { roadPoints, routeLegs } from '@/utils/routeGeometry'
import { wgs84ToGcj02 } from '../../../shared/coordinates.js'
const props = withDefaults(defineProps<{
  spotIds?: number[]; overview?: RouteOverviewData | null; compare?: RouteOverviewData | null
  pace?: string; showMap?: boolean; compact?: boolean; currentId?: number; mapOnly?: boolean; showStatistics?: boolean
}>(), { showMap:true, pace:'standard', showStatistics:true })
const data=ref<RouteOverviewData|null>(null), busy=ref(false), error=ref(''), mapError=ref(false)
const mapEl=ref<HTMLElement|null>(null), showOriginal=ref(false), activeLeg=ref(0)
const legsExpanded=ref(false)
const displayed=computed(()=>showOriginal.value && props.compare ? props.compare : data.value)
const legs=computed(()=>routeLegs(displayed.value))
let controller:AbortController|undefined, version=0, drawVersion=0, disposed=false
let map:any, group:any, resize:ResizeObserver|undefined, boundsVersion=''
const meters=(v:number|null|undefined)=>v==null?'—':v>=1000?(v/1000).toFixed(2)+' km':v+' m'
function roadName(name:string){const result=t(name);return !name || locale.value==='en' && /[\u3400-\u9fff]/.test(result) ? t('园内步道') : result}
async function refresh(){
  const own=++version;controller?.abort();error.value=''
  if(props.overview){data.value=props.overview;busy.value=false;return}
  if(!props.spotIds?.length){data.value=null;busy.value=false;return}
  busy.value=true;controller=new AbortController()
  try{const response=await getRouteOverview(props.spotIds,props.pace,controller.signal)
    if(disposed||own!==version)return
    if(!response.data.success)throw new Error()
    data.value=response.data.data
  }catch(e:any){if(!disposed&&own===version&&e.code!=='ERR_CANCELED'){data.value=null;error.value=t('路线详情暂时无法加载')}}
  finally{if(own===version)busy.value=false}
}
async function draw(){
  const own=++drawVersion
  await nextTick()
  if(!props.showMap||!mapEl.value||!displayed.value||disposed)return
  try{
    const L=await loadScenicMap()
    if(disposed||own!==drawVersion||!mapEl.value||!displayed.value)return
    if(!map){map=L.map(mapEl.value,{zoomControl:true,attributionControl:false,scrollWheelZoom:false})
      L.tileLayer(SCENIC_TILES,{maxZoom:18}).addTo(map);group=L.layerGroup().addTo(map)
      if(typeof ResizeObserver!=='undefined'){resize=new ResizeObserver(()=>map?.invalidateSize({pan:false}));resize.observe(mapEl.value)}}
    group.clearLayers()
    const route=displayed.value, bounds:number[][]=[]
    routeLegs(route).forEach((leg,index)=>{
      const points=roadPoints(leg);if(!points.length)return
      bounds.push(...points)
      L.polyline(points,{color:showOriginal.value?'#8b96ac':index===activeLeg.value?'#513dbe':'#a69acb',weight:index===activeLeg.value?6:4,opacity:index===activeLeg.value?1:.7,lineCap:'round',lineJoin:'round'})
        .on('click',()=>{activeLeg.value=index}).addTo(group)
    })
    route.stops.forEach(stop=>{
      const lat=stop.access_latitude??stop.latitude,lng=stop.access_longitude??stop.longitude
      if(lat==null||lng==null)return
      const point=wgs84ToGcj02(lat,lng);bounds.push(point)
      const active=stop.spot_id===props.currentId
      const icon=L.divIcon({className:'route-order-marker',html:`<span style="display:grid;place-items:center;width:30px;height:30px;border-radius:50%;border:3px solid white;box-shadow:0 2px 9px #50428155;background:${active?'#23816b':'#6652bd'};color:white;font:600 18px var(--app-font-family)">${stop.order}</span>`,iconSize:[36,36],iconAnchor:[18,18]})
      const label=document.createElement('span');label.textContent=t(stop.spot_name)+' · '+t('步行接入点')
      L.marker(point,{icon,title:t(stop.spot_name)}).bindPopup(label).addTo(group)
    })
    if(route.entry_anchor){const entry=route.entry_anchor,point=wgs84ToGcj02(entry.latitude,entry.longitude);bounds.push(point)
      const icon=L.divIcon({className:'route-entry-marker',html:'<span style="display:grid;place-items:center;width:32px;height:32px;border:3px solid white;border-radius:10px;background:#315c65;color:white;font:700 18px var(--app-font-family)">'+iconMarkup('map-pin')+'</span>',iconSize:[38,38],iconAnchor:[19,19]})
      const label=document.createElement('span');label.textContent=locale.value==='en'&&entry.label_en?entry.label_en:t(entry.label)
      L.marker(point,{icon,title:label.textContent}).bindPopup(label).addTo(group)}
    if(route.exit_anchor){const gate=route.exit_anchor,point=wgs84ToGcj02(gate.latitude,gate.longitude);bounds.push(point)
      const icon=L.divIcon({className:'route-exit-marker',html:'<span style="display:grid;place-items:center;width:32px;height:32px;border:3px solid white;border-radius:10px;background:#23816b;color:white;font:700 18px var(--app-font-family)">'+iconMarkup('arrow-up-right')+'</span>',iconSize:[38,38],iconAnchor:[19,19]})
      const label=document.createElement('span');label.textContent=t(gate.label)
      L.marker(point,{icon,title:t(gate.label)}).bindPopup(label).addTo(group)}
    const key=[route.network_version,route.stops.map(s=>s.spot_id).join(','),route.exit_anchor?.label,route.avoid_steps,showOriginal.value].join('|')
    map.invalidateSize()
    if(bounds.length&&key!==boundsVersion){map.fitBounds(L.latLngBounds(bounds),{padding:[28,28],maxZoom:17,animate:false});boundsVersion=key}
    else if(!bounds.length)map.setView([39.997,116.269],14)
    mapError.value=false
  }catch{if(!disposed&&own===drawVersion)mapError.value=true}
}
watch(()=>[props.spotIds,props.overview,props.pace],refresh,{immediate:true,deep:true})
watch(()=>[displayed.value,props.currentId],()=>{activeLeg.value=Math.max(0,displayed.value?.stops.findIndex(s=>s.spot_id===props.currentId)??0);void draw()},{deep:true,immediate:true})
watch(()=>[activeLeg.value,locale.value],draw)
// The map container may mount after a page transition or a delayed overview.
watch(mapEl, element => { if(element) void draw() }, {flush:'post'})
watch(()=>props.showMap, () => { void draw() })
onBeforeUnmount(()=>{disposed=true;version++;drawVersion++;controller?.abort();resize?.disconnect();map?.remove()})
</script>
<template>
  <section class="route-overview-panel" :class="{compact}" :aria-busy="busy" :aria-label="$t('路线顺序与时间')">
    <p v-if="busy" role="status">{{ $t('正在计算路线详情…') }}</p>
    <p v-if="error" class="route-error" role="alert">{{ error }} <button type="button" @click="refresh">{{ $t('重试') }}</button></p>
    <template v-if="displayed?.stops.length">
      <div v-if="!mapOnly && showStatistics" class="route-statistics"><span><strong>{{ displayed.stops.length }}</strong>{{ $t('站') }}</span><span><strong>{{ meters(displayed.walking_meters) }}</strong>{{ $t('步行') }}</span><span><strong>{{ displayed.total_minutes ?? '—' }}</strong>{{ $t('预计分钟') }}</span></div>
      <div v-if="compare && showMap" class="route-map-switch" role="group" :aria-label="$t('路线对比')"><button type="button" :aria-pressed="!showOriginal" @click="showOriginal=false">{{ $t('调整后') }}</button><button type="button" :aria-pressed="showOriginal" @click="showOriginal=true">{{ $t('调整前') }}</button></div>
      <div v-if="showMap" ref="mapEl" class="route-overview-map"></div>
      <p v-if="!displayed.complete" class="route-error" role="alert">{{ $t('部分路段无法确认可步行路径，请调整景点或通行条件。') }}</p>
      <p v-if="showMap" class="route-map-note">{{ $t('路线沿园内步道绘制；数字标记为步行接入点。') }} <button v-if="mapError" type="button" @click="draw">{{ $t('重新加载地图') }}</button></p>
      <section v-if="showMap && legs.length" class="route-walking-legs" :aria-label="$t('全程步行路线')">
        <header class="walking-legs-heading">
          <h3>{{ $t('全程步行路线') }}</h3>
          <button type="button" class="walking-legs-toggle" :aria-expanded="legsExpanded" :aria-label="$t(legsExpanded?'收起全程路线':'展开全程路线')" @click="legsExpanded=!legsExpanded">
            {{ $t(legsExpanded?'收起':'展开') }}<ArrowDown aria-hidden="true" />
          </button>
        </header>
        <ol v-show="legsExpanded" class="walking-leg-list" tabindex="0" :aria-label="$t('全程步行路线')">
          <li v-for="(leg,index) in legs" :key="index" :class="{active:index===activeLeg}">
            <button type="button" class="walking-leg-button" :aria-pressed="index===activeLeg" @click="activeLeg=index">
              <b aria-hidden="true">{{ index+1 }}</b>
              <span class="walking-leg-content">
                <strong>{{ locale==='en'&&leg.from_name_en?leg.from_name_en:$t(leg.from_name) }} → {{ locale==='en'&&leg.to_name_en?leg.to_name_en:$t(leg.to_name) }}</strong>
                <span v-if="leg.available===false" class="route-error">{{ $t('步行路径待确认') }}</span>
                <span v-else>{{ meters(leg.meters) }} · {{ leg.minutes ?? '—' }} {{ $t('分钟') }}<em v-if="leg.has_steps"> · {{ $t('含已标注台阶') }}</em></span>
              </span>
            </button>
            <details v-if="leg.available!==false && leg.sections?.length" class="walking-leg-sections"><summary>{{ $t('查看途经路段') }}</summary><ol><li v-for="(section,sectionIndex) in leg.sections" :key="sectionIndex"><span>{{ roadName(section.road_name) }}<em v-if="section.steps"> · {{ $t('台阶') }}</em><em v-else-if="section.bridge"> · {{ $t('桥梁') }}</em></span><span>{{ meters(section.meters) }}</span></li></ol></details>
          </li>
        </ol>
      </section>
      <details v-if="!mapOnly" :open="!compact" class="route-leg-details"><summary>{{ $t('查看每段距离与用时') }}</summary><ol><li v-for="(stop,index) in displayed.stops" :key="stop.spot_id" :class="{current:stop.spot_id===currentId}"><div><b>{{ stop.order }}</b><strong>{{ $t(stop.spot_name) }}</strong><span v-if="stop.visit_minutes">{{ $t('停留') }} {{ stop.visit_minutes }} {{ $t('分钟') }}</span><span v-else>{{ $t('当前站，离开后计时') }}</span></div><p v-if="displayed.legs[index]"><Bottom aria-hidden="true" /> {{ meters(displayed.legs[index].meters) }} · {{ $t('步行') }} {{ displayed.legs[index].minutes ?? '—' }} {{ $t('分钟') }}</p></li><li v-if="displayed.exit_leg"><div><b><ArrowUpRight aria-hidden="true" /></b><strong>{{ $t(displayed.exit_leg.to_name) }}</strong><span>{{ $t('离园') }}</span></div><p>{{ meters(displayed.exit_leg.meters) }} · {{ displayed.exit_leg.minutes ?? '—' }} {{ $t('分钟') }}</p></li></ol></details>
      <p v-if="!mapOnly" class="route-estimate-note">{{ $t('停留') }} {{ displayed.visit_minutes }} + {{ $t('步行') }} {{ displayed.walking_minutes ?? '—' }} + {{ $t('休息') }} {{ displayed.rest_minutes }}<template v-if="displayed.exit_leg"> + {{ $t('离园') }} {{ displayed.exit_minutes ?? '—' }}</template><template v-if="displayed.reserve_minutes"> + {{ $t('预留') }} {{ displayed.reserve_minutes }}</template> {{ $t('分钟') }}<span v-if="!displayed.exit_leg"> · {{ $t('未计离园时间') }}</span></p>
    </template>
  </section>
</template>
<style scoped>
.route-overview-panel {
  min-width: 0;
  color: var(--text);
  font-size: 18px;
}
.route-statistics {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.route-statistics > span {
  display: flex;
  align-items: baseline;
  gap: 7px;
  color: var(--text-secondary);
  font-size: 18px;
}
.route-statistics strong {
  font: 600 21px var(--app-font-family);
  color: #6150aa;
}
.route-overview-map {
  height: 280px;
  border-radius: 16px;
  overflow: hidden;
  background: #eff1f6;
  isolation: isolate;
}
.route-map-note,
.route-estimate-note {
  font-size: 18px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 10px 0;
}
.route-leg-details summary {
  cursor: pointer;
  color: #6452ae;
  padding: 6px 0;
  font-size: 18px;
}
.route-leg-details ol {
  list-style: none;
  margin: 10px 0;
  padding: 0;
  display: grid;
  gap: 9px;
}
.route-leg-details li > div {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 18px;
}
.route-leg-details li > div > b {
  width: 25px;
  height: 25px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #eeeafa;
  color: #6853b6;
  font: 600 18px var(--app-font-family);
}
.route-leg-details li.current > div > b {
  background: #dcf3e9;
  color: #20755f;
}
.route-leg-details li > div > span {
  margin-left: auto;
  color: var(--text-secondary);
  font-size: 18px;
}
.route-leg-details li p {
  margin: 5px 0 0 35px;
  font-size: 18px;
  color: var(--text-secondary);
}
.route-leg-details small {
  margin-left: 8px;
  font-size: 18px;
}
.route-error {
  color: #b42342;
}
button {
  border: 0;
  border-radius: 8px;
  background: #eeebfa;
  color: #6652bd;
  padding: 5px 9px;
  font: inherit;
  cursor: pointer;
}
.compact .route-statistics {
  margin: 10px 0;
  gap: 20px;
}
.compact .route-statistics strong {
  font-size: 18px;
}
.compact .route-estimate-note {
  margin-bottom: 0;
}

.route-map-switch{display:flex;gap:6px;margin-bottom:12px}
.route-map-switch button{font-size:18px;padding:8px 16px;background:#f1f3f8;color:#566175}
.route-map-switch button[aria-pressed="true"]{background:#e9e4fa;color:#5c45ac}
.route-walking-legs{margin-top:18px;font-size:18px;line-height:1.6}
.walking-legs-heading{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px 16px;margin-bottom:12px}
.route-walking-legs h3{margin:0;font-size:22px}
.walking-legs-toggle{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;padding:6px 12px;border:1px solid #ded8ed;border-radius:12px;background:#f7f5fb;color:#6652ad;font-size:18px;white-space:nowrap}
.walking-legs-toggle svg{width:20px;height:20px;transition:transform .15s ease}
.walking-legs-toggle[aria-expanded="true"] svg{transform:rotate(180deg)}
.walking-leg-list{display:grid;gap:10px;list-style:none;margin:0;padding:0 4px 0 0;max-height:min(360px,45vh);overflow-y:auto;overscroll-behavior-y:contain;scrollbar-gutter:stable}
.walking-leg-list:focus-visible,.walking-legs-toggle:focus-visible{outline:2px solid #6652ad;outline-offset:3px}
@media(prefers-reduced-motion:reduce){.walking-legs-toggle svg{transition:none}}
.walking-leg-list>li{min-width:0;border:1px solid #e2e8f0;border-radius:12px;background:#fff;overflow:hidden}
.walking-leg-list>li.active{border-color:#c7bdf2;background:#f4f2fa}
.walking-leg-button{display:grid;grid-template-columns:32px minmax(0,1fr);align-items:start;gap:12px;width:100%;padding:14px;text-align:left;border-radius:0;background:transparent;color:inherit;white-space:normal}
.walking-leg-button>b{display:grid;place-items:center;min-height:32px;border-radius:50%;background:#eeeafa;color:#6652bd;font-size:18px}
.walking-leg-content{display:grid;gap:4px;min-width:0;overflow-wrap:anywhere}
.walking-leg-content>span{color:#59657a}.route-walking-legs em{font-style:normal;color:#9a651c}
.walking-leg-content>.route-error{color:#b42342}
.walking-leg-sections{margin:0 14px 12px 58px}
.walking-leg-sections summary{cursor:pointer;color:#6652ad}
.walking-leg-sections ol{list-style:none;padding:0;margin:10px 0 0;display:grid;gap:7px}
.walking-leg-sections li{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid #e7e2f0;padding-bottom:6px;overflow-wrap:anywhere}
.walking-leg-sections li>span:first-child{min-width:0}.walking-leg-sections li>span:last-child{flex-shrink:0}
.route-overview-panel:has(.route-map-switch) .route-overview-map{height:clamp(200px,calc(94dvh - 430px),340px)}
@media(max-width:767px){.route-overview-panel:has(.route-map-switch) .route-overview-map{height:260px}}
</style>
