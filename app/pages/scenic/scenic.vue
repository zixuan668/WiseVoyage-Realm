<template>
  <view class="native-scenic" :class="{expanded:introOpen,'planner-open':panel==='plan'}" :style="{paddingTop:statusH+'px'}">
    <view class="scenic-nav" :class="{'nav-planner':panel==='plan'}">
      <button class="app-back-btn" :aria-label="t('返回')" @tap="goBack"><view class="app-back-icon"></view></button>
      <text class="nav-page-title">{{ t(panel==='plan'?'路径规划':panel==='catalog'?'全部景点':panel==='list'?'已选景点':'景点图鉴') }}</text>
      <button v-if="panel==='plan'&&showPlanResult" class="nav-start" :disabled="busy||!planOverview||!planOverview.complete" @tap="chooseGuide"><text class="iconfont icon-play" aria-hidden="true"></text><text>{{ t('开始导览') }}</text></button>
      <view v-else-if="panel==='plan'" class="nav-placeholder" aria-hidden="true"></view>
      <button v-else class="nav-more" :aria-label="t('更多操作')" :aria-expanded="menuOpen" @tap="menuOpen=!menuOpen"><text class="iconfont icon-more" aria-hidden="true"></text></button>
    </view>

    <view v-if="stationPlanError || planError" class="planner-error-mask">
      <view class="planner-error-card">
        <text class="pe-msg">{{ stationPlanError || planError }}</text>
        <button class="pe-retry" @tap="retryPlannerError">{{ t('重试') }}</button>
      </view>
    </view>

    <view v-if="menuOpen" class="menu-mask" @tap="menuOpen=false">
      <view class="scenic-menu" :style="{top:(statusH+58)+'px'}" @tap.stop>
        <button class="sm-item" :disabled="!current || busy || !draftReady" @tap="toggleStop(current.id)">
          <view class="sm-icon"><text class="iconfont" :class="added?'icon-minus':'icon-plus'" aria-hidden="true"></text></view>
          <text class="sm-label">{{ t(added?'移出路线':'加入路线') }}</text>
        </button>
        <button class="sm-item" :disabled="!current" @tap="toggleAudio">
          <view class="sm-icon"><text class="iconfont icon-volume" aria-hidden="true"></text></view>
          <text class="sm-label">{{ t('听介绍') }}</text>
        </button>
      </view>
    </view>

    <view v-if="!panel" class="scenic-intro" :class="{expanded:introOpen}" @touchstart="onTouchStart" @touchend="onTouchEnd">
      <template v-if="current">
        <image v-if="cover(current)&&!failedImages[current.id]" :key="current.id" class="scenic-photo" :src="cover(current)" mode="aspectFill" @error="failedImages[current.id]=true" />
        <view v-else class="photo-missing"><text>{{ t('暂无景点图片') }}</text></view>
        <view class="photo-shade"></view>
        <image v-if="cover(current)&&!failedImages[current.id]" class="glass-blur" :key="'blur-'+current.id" :src="cover(current)" mode="aspectFill" aria-hidden="true" />
        <view class="intro-content" :class="{expanded:introOpen}">
          <view v-if="!introOpen" class="thumb-frame">
            <scroll-view scroll-x class="thumb-strip" :show-scrollbar="false" :enhanced="true" @touchstart.stop @touchmove.stop @touchend.stop>
              <button v-for="place in catalog" :key="place.id" class="thumb" :class="{selected:place.id===current.id}" @tap.stop="choosePlace(place.id)">
                <image v-if="cover(place)" :src="cover(place)" mode="aspectFill" /><text>{{ t(place.name) }}</text>
              </button>
            </scroll-view>
          </view>
          <view class="intro-glass" :class="{expanded:introOpen}">
            <view class="intro-heading"><text class="spot-title">{{ t(current.name) }}</text></view>
            <scroll-view v-if="introOpen" scroll-y class="knowledge-scroll" :show-scrollbar="false" @scroll="onKnowledgeScroll" @touchstart.stop="onKnowledgeTouchStart" @touchend.stop="onKnowledgeTouchEnd">
              <view v-for="section in knowledgeSections" :key="section.key" class="knowledge-section"><text class="section-title">{{ t(section.title) }}</text><text class="section-text">{{ t(section.text) }}</text></view>
            </scroll-view>
            <text v-else class="spot-summary" @tap.stop="introOpen=true">{{ t(current.description || current.location || '') }}</text>
            <view class="intro-dots" aria-hidden="true">
              <view v-for="n in 4" :key="n" :class="{ on: n - 1 === Math.min(Math.max(catalog.findIndex(p => p.id === current.id), 0), 3) }"></view>
            </view>
          </view>
        </view>
      </template>
      <view v-else-if="catalogError" class="load-state"><text>{{ t(catalogError) }}</text><button @tap="refresh">{{ t('重新加载') }}</button><button @tap="openPanel('catalog')">{{ t('全部景点') }}</button></view>
      <view v-else-if="loadingHintVisible" class="load-state"><text>{{ t(loading?'正在加载景点…':'暂无可用景点') }}</text></view>
    </view>

    <scroll-view v-else-if="panel==='catalog'" scroll-y class="catalog-scroll" :show-scrollbar="false" :enhanced="true" :bounces="false">
      <view v-if="catalogError" class="inline-error"><text>{{ t(catalogError) }}</text><button @tap="refresh">{{ t('重试') }}</button></view>
      <view class="catalog-grid"><button v-for="place in catalog" :key="place.id" class="catalog-card" @tap="choosePlace(place.id)"><image v-if="cover(place)&&!failedImages[place.id]" :src="cover(place)" mode="aspectFill" @error="failedImages[place.id]=true" /><view v-else class="catalog-no-photo">{{ t('暂无图片') }}</view><text>{{ t(place.name) }}</text></button></view>
      <view v-if="loading&&!catalog.length&&!catalogError" class="catalog-skeleton" aria-busy="true"><view v-for="n in 6" :key="n" class="catalog-sk-card sk-block"></view></view>
      <text v-if="!catalog.length&&loadingHintVisible&&!catalogError&&!loading" class="list-note">{{ t('暂无可用景点') }}</text>
    </scroll-view>

    <scroll-view v-else class="plan-scroll" :scroll-y="stops.length>0&&!dragging&&!mapInteracting&&!planDragActive&&!showPlanResult" :show-scrollbar="false">
      <view v-if="draftError" class="inline-error"><text>{{ t(draftError) }}</text><button @tap="refreshDraft">{{ t('重试') }}</button></view>
      <view v-if="!draftReady&&loadingHintVisible" class="planner-skeleton" aria-busy="true">
        <view class="ps-map sk-block"></view>
        <view class="ps-pad">
          <view class="ps-row">
            <view class="ps-field"><view class="ps-line w60 sk-block"></view><view class="ps-input sk-block"></view></view>
            <view class="ps-field"><view class="ps-line w60 sk-block"></view><view class="ps-input sk-block"></view></view>
          </view>
          <view class="ps-check"><view class="ps-box sk-block"></view><view class="ps-line w50 sk-block"></view></view>
          <view class="ps-tip sk-block"></view>
        </view>
      </view>
      <template v-if="draftReady">
        <view v-if="!showPlanResult" class="station-planner">
          <view class="sp-map">
            <RouteRoadMap v-if="plannerMapData" :data="plannerMapData" :marker-labels="plannerMarkerLabels" :selected-markers="plannerSelectedMarkers" :focus="plannerFocus" @interacting="mapInteracting=$event" />
          </view>
          <view class="sp-body">
            <scroll-view scroll-x class="sp-filter" :show-scrollbar="false" :enhanced="true"><view class="sp-filter-inner"><button v-for="tab in spTabs" :key="tab.key" class="sp-filter-btn" :class="{on:spFilter===tab.key}" @tap="spFilter=tab.key">{{ tab.label }}</button></view></scroll-view>
<view v-show="spFilter==='basic'" class="sp-section">
              <text class="sp-field-label">您有多少时间？</text>
              <scroll-view scroll-x class="sp-time-row" :show-scrollbar="false" :enhanced="true"><view class="sp-time-row-inner">
                <button v-for="h in [1,2,3,4]" :key="h" class="sp-time-chip" :class="{on:stationPlanner.budget===h*60}" @tap="pickStationTime(h*60)">{{ h }}{{ tourLanguage==='en'?' h':' 小时' }}</button>
                <view class="sp-time-custom"><input class="sp-time-input" type="number" :value="timeMode==='custom'?customMinutes:''" placeholder="自定义" placeholder-style="color:#b9b3c6;font-size:10px" @input="onCustomMinutes" /><text class="sp-time-unit">分钟</text></view>
              </view></scroll-view>
              <text class="sp-field-label">请选择游览终点</text>
              <view class="sp-gate-row"><button v-for="gate in gateOptions" :key="gate.v" class="sp-gate-chip" :class="{on:stationPlanner.end_area===gate.v}" @tap="pickStationGate(gate.v)">{{ t(gate.l) }}</button></view>
              <button class="sp-check" @tap="stationPlanner.avoid_steps=!stationPlanner.avoid_steps"><view class="sp-box" :class="{on:stationPlanner.avoid_steps}"></view><text>避开路网已标注的台阶</text></button>
              <text class="sp-hint sp-check-hint">不代表无障碍认证，现场通行条件仍需确认。</text>
              <text v-if="stationPlanner.avoid_steps&&planOverview&&planOverview.has_steps" class="sp-step-warn">所选景点之间仍有台阶路段，可能无法完全避开；可减少景点或咨询现场工作人员。</text>
            </view>
            <view v-show="spFilter==='prefs'" class="sp-section">
              <view class="sp-section-body">
                <text class="sp-field-label">想优先看什么</text>
                <view class="sp-interest"><button v-for="item in spInterests" :key="item.v || 'all'" :class="{on:stationPlanner.interest===item.v}" @tap="pickStationInterest(item.v)">{{ t(item.l) }}</button></view>
                <text class="sp-field-label">步行速度</text>
                <view class="sp-gate-row"><button class="sp-gate-chip" :class="{on:stationPlanner.pace!=='relaxed'}" @tap="pickStationPace('standard')">标准</button><button class="sp-gate-chip" :class="{on:stationPlanner.pace==='relaxed'}" @tap="pickStationPace('relaxed')">慢行多休息</button></view>
              </view>
            </view>
            <view v-show="spFilter==='spots'" class="sp-section">
              <view class="sp-segment"><view class="sp-segment-underline" :class="{right:selectMode==='together'}"></view><button :class="{on:selectMode==='self'}" @tap="selectMode='self'">个人选点</button><button :class="{on:selectMode==='together'}" @tap="selectMode='together'">我们一起选</button></view>
              <view class="sp-segment-divider"></view>
              <view class="sp-spots-head"><text class="sp-spots-title">自选景点</text><text class="sp-count">{{ stops.length }} 处已选</text></view>
              <view class="sp-spot-chips"><button v-for="place in catalog" :key="place.id" :class="{on:selectedIds.includes(place.id)}" @tap="quickToggleStop(place.id)">{{ t(place.name) }}</button></view>
            </view>
            <view v-show="spFilter==='extra'" class="sp-section">
              <view class="sp-extra-display">
                <input class="sp-extra-input" :value="stationPlanner.extra" placeholder="（选填）例如：少走路、想看海棠、带婴儿车" placeholder-style="color:#a9a2ba;font-size:13px" @input="stationPlanner.extra=$event.detail.value" @focus="onExtraFocus" />
              </view>
            </view>
            <view v-show="spFilter==='companion'" class="sp-section">
              <view class="sp-guide-grid"><button v-for="g in guides" :key="g.guide_id" class="sp-guide-card" :class="{on:pickedGuide&&pickedGuide.guide_id===g.guide_id}" @tap="pickGuide(g)"><image :src="guideImage(g)" mode="aspectFit" @error="failedGuideImages[g.guide_id]=true" /><text>{{ g.name }}</text></button></view>
            </view>

            <view v-if="stationPlans.length" class="sp-results">
              <view v-if="stationPlan" class="sp-plan-summary">
                <view><text>{{ t('全程步行') }}</text><text class="sp-fact">{{ t('{n} 分钟',{n:stationPlan.route.walking_minutes}) }}</text></view>
                <view><text>{{ t('路线距离') }}</text><text class="sp-fact">{{ Math.round((stationPlan.route.walking_meters||0)/10)/100 }} km</text></view>
                <view><text>{{ t('总时长') }}</text><text class="sp-fact">{{ t('{n} 分钟',{n:stationPlan.route.total_minutes}) }}</text></view>
              </view>
              <view v-if="stationPlan" class="sp-stops"><view v-for="(stop,index) in stationPlan.route.stops" :key="stop.spot_id" class="sp-stop"><text class="sp-stop-no">{{ index+1 }}</text><text class="sp-stop-name">{{ t(stop.spot_name) }}</text><text class="sp-stop-time">{{ t('{n} 分钟',{n:stop.visit_minutes}) }}</text></view></view>
            </view>
          </view>
          <view class="sp-foot">
            <button class="sp-generate" :class="{incomplete:!canGenerate}" :disabled="stationPlanBusy" @tap="onGenerateTap">{{ stationPlanBusy ? t('正在生成…') : t('查看路线') }}</button>
          </view>
        </view>
        <template v-else-if="showPlanResult">
          <view v-if="panel==='list'" class="saved-stops"><view v-for="(stop,index) in stops" :key="stop.id" class="saved-stop"><text>{{ index+1 }} · {{ t(stop.name) }}</text><button :disabled="busy" @tap="toggleStop(stop.id)">{{ t('移除') }}</button></view><button class="primary-action" @tap="openPanel('plan')">{{ t('规划路线') }}</button></view>
          <view v-else class="native-plan">
            <view v-if="!planOverview&&planBusy" class="plan-loading"><text>{{ t('正在计算路线…') }}</text></view>
            <template v-else-if="planOverview">
              <view class="plan-map">
                <RouteRoadMap :data="planMapData" :marker-labels="planMarkerLabels" :selected-markers="planSelectedMarkers" @interacting="mapInteracting=$event" />
              </view>
              <view class="plan-facts">
                <view><text>{{ t('全程步行') }}</text><text class="fact-value">{{ planFact(planOverview.walking_minutes) }}</text></view>
                <view><text>{{ t('路线距离') }}</text><text class="fact-value">{{ planDistance }}</text></view>
                <view><text>{{ t('总时长') }}</text><text class="fact-value">{{ planFact(planOverview.total_minutes) }}</text></view>
              </view>
              <scroll-view class="plan-stops-scroll" :scroll-y="true" :scroll-top="planScrollTop" :show-scrollbar="false" :enhanced="true" :bounces="false" @scroll="onPlanStopsScroll">
                <view class="plan-stops">
                  <view v-for="(stop,index) in planStops" :key="stop.spot_id" class="plan-stop" :class="{dragging:planDragActive&&planDragIndex===index,ghosted:!!planGhost&&planDragIndex===index}" :style="planShiftStyle(index)">
                    <text class="plan-stop-no">{{ index+1 }}</text>
                    <text class="plan-stop-name">{{ t(stop.spot_name) }}</text>
                    <text class="plan-stop-stay">{{ planFact(stop.visit_minutes) }}</text>
                    <view class="plan-stop-grip" :class="{'is-pressed':planDragActive&&planDragIndex===index}" hover-class="plan-stop-grip-on" :hover-stay-time="80" @touchstart.stop="onPlanGripTouchStart(index,$event)" @touchmove.stop="onPlanGripTouchMove($event)" @touchend.stop="onPlanGripTouchEnd($event)" @touchcancel.stop="onPlanGripTouchCancel($event)"><text class="iconfont icon-drag" aria-hidden="true"></text></view>
                    <button class="plan-stop-remove" :disabled="busy" :aria-label="t('移除')" @tap="toggleStop(stop.spot_id)"><text class="iconfont icon-close" aria-hidden="true"></text></button>
                  </view>
                </view>
              </scroll-view>
              <!-- 长按把手后跟手的悬浮条；固定定位，不受列表滚动窗口裁剪。 -->
              <view v-if="planGhost" class="plan-stop plan-stop-floating" :style="planGhostStyle()" aria-hidden="true">
                <text class="plan-stop-no">{{ planDragIndex+1 }}</text>
                <text class="plan-stop-name">{{ planDragSpot ? t(planDragSpot.spot_name) : '' }}</text>
                <text class="plan-stop-stay">{{ planDragSpot ? planFact(planDragSpot.visit_minutes) : '' }}</text>
                <view class="plan-stop-grip is-pressed"><text class="iconfont icon-drag"></text></view>
                <view class="plan-stop-remove"><text class="iconfont icon-close"></text></view>
              </view>
              <view v-if="!planOverview.complete" class="plan-warning"><text>{{ t('部分路段无法确认可步行路径，请调整景点或通行条件。') }}</text></view>
            </template>
          </view>
        </template>
      </template>
    </scroll-view>

    <view v-if="audioOpen" class="native-audio">
      <button :disabled="audioLoading" @tap="togglePlayback">{{ audioLoading?'…':audioPlaying?'Ⅱ':'▶' }}</button>
      <view class="audio-info"><text>{{ current?t(current.name):'' }}</text><text>{{ formatTime(audioElapsed) }} / {{ audioDuration?formatTime(audioDuration):'—' }}</text></view>
      <button :aria-label="t('关闭讲解')" @tap="stopAudio">×</button>
    </view>
    <view v-if="!panel&&draftError" class="draft-notice" @tap="refreshDraft">{{ t('行程加载失败，点击重试') }}</view>
    <PageDock :active="0" :inline="false" />
  </view>
</template>

<script>
import PageDock from '../../components/PageDock.vue'
import RouteRoadMap from '../../components/RouteRoadMap.vue'
import { SERVER_ORIGIN } from '../../common/config.js'
import { SCENIC_COVERS } from '../../common/scenic-covers.js'
import { scenicContext, scenicRequest, readScenicCatalog, loadScenicCatalog, loadScenicDraft, startTourSession } from '../../common/scenic-api.js'
import { previewOptions, roadMap, routeRequest } from '../../common/route-planning.js'

const GATES = [{value:'auto',label:'任意'},{value:'east',label:'东宫门'},{value:'north',label:'北宫门'},{value:'south',label:'新建宫门'}]
export default {
  components:{PageDock,RouteRoadMap},
  data() { return {
    catalog:readScenicCatalog(),currentId:null,panel:'',entryPanel:'',statusH:20,introOpen:false,knowledgeTop:0,menuOpen:false,
    loading:true,loadingHintVisible:false,catalogError:'',failedImages:{},stops:[],settings:{spot_ids:[]},draftReady:false,draftError:'',busy:false,
    showRouteDetails:false,dragging:false,itineraryState:{busy:false,error:'',data:null,key:''},gates:GATES,
    planOverview:null,planBusy:false,planError:'',mapInteracting:false,planDragActive:false,planDragSettling:false,planDragIndex:-1,planDragTarget:-1,planDragY:0,planDragStartY:0,planDragRowH:50,planStopOrder:[],planGhost:null,planScrollTop:0,planScrollStart:0,
    stationPlanner:{budget:120,start_area:'east',end_area:'east',avoid_steps:false,interest:'',pace:'standard',extra:''},
    timeMode:'preset',
    customMinutes:'',
    plannerFocus:null,
    gateFocus:{east:{latitude:39.9966755,longitude:116.2755965},north:{latitude:40.0009937,longitude:116.268051},south:{latitude:39.9896694,longitude:116.2738739},return:{latitude:39.9966755,longitude:116.2755965}},
    spFilter:'basic',prefsOpen:false,extraOpen:false,selectMode:'self',segmentUnderline:{left:0,width:0},
    spTabs:[{key:'basic',label:'基础条件'},{key:'prefs',label:'游玩偏好'},{key:'spots',label:'选点方式'},{key:'extra',label:'额外需求'},{key:'companion',label:'伴游选择'}],
    spInterests:[{v:'',l:'综合'},{v:'history',l:'历史人文'},{v:'nature',l:'自然风光'},{v:'photo',l:'摄影打卡'},{v:'family',l:'亲子轻松'}],
    timeMenuOpen:false,gateMenuOpen:false,
    gateOptions:[{v:'east',l:'东宫门'},{v:'north',l:'北宫门'},{v:'south',l:'新建宫门'},{v:'return',l:'返回本站'}],guides:[],pickedGuide:null,
    stationPlans:[],stationPlanIndex:0,stationPlanBusy:false,stationPlanError:'',showPlanResult:false,failedGuideImages:{},
    extraEditorOpen:false,extraEditorValue:'',extraEditorTop:260,extraEditorLift:0,extraEditorFocus:false,extraEditorRect:{left:16,top:260,width:320,height:110},
    planProgress:{time:false,gate:false,interest:false,pace:false},_savedGuideId:0,
    audioOpen:false,audioLoading:false,audioPlaying:false,audioElapsed:0,audioDuration:0,
  } },
  computed:{
    current(){return this.catalog.find(p=>String(p.id)===String(this.currentId)) || (this.currentId===null?this.catalog[0]:null) || null},
    thumbSpots(){
      if(!this.catalog.length)return []
      const index=this.catalog.findIndex(p=>p.id===this.current?.id)
      const start=Math.max(0,Math.min(index-2,this.catalog.length-5))
      return this.catalog.slice(start,start+5)
    },
    added(){return !!this.current&&this.stops.some(p=>p.id===this.current.id)},
    selectedIds(){return this.stops.map(p=>p.id)},
    preferenceSummary(){const i=this.spInterests.find(x=>x.v===this.stationPlanner.interest);return (i?i.l:'综合')+' · '+(this.stationPlanner.pace==='relaxed'?'慢行':'标准步速')},
    routeSpots(){return this.catalog.map(p=>({...p,spot_id:p.id,spot_name:p.name}))},
    routePlan(){return {spot_ids:this.selectedIds,pace:(this.settings.elderly||this.settings.children||this.stationPlanner.avoid_steps)?'relaxed':'standard',start_area:this.settings.start_area||'auto',end_area:this.settings.end_area||'auto',avoid_steps:!!(this.settings.avoid_steps||this.settings.elderly||this.settings.children||this.stationPlanner.avoid_steps)}},
    planKey(){return JSON.stringify(previewOptions(this.selectedIds,this.routePlan,this.routePlan.pace))},
    planStops(){
      const stops=(this.planOverview&&this.planOverview.stops)||[]
      const order=this.planStopOrder||[]
      if(!order.length)return stops
      return stops.slice().sort((a,b)=>{
        const ia=order.indexOf(a.spot_id),ib=order.indexOf(b.spot_id)
        return (ia<0?999:ia)-(ib<0?999:ib)
      })
    },
    planMapData(){return this.planOverview?roadMap(this.planOverview):null},
    planMarkerLabels(){const labels={};this.planStops.forEach((stop,index)=>{labels[index+1]=this.t(stop.spot_name)});return labels},
    planDistance(){const meters=Number(this.planOverview&&this.planOverview.walking_meters);return Number.isFinite(meters)&&meters>0?(meters>=1000?(meters/1000).toFixed(1)+' km':Math.round(meters)+' m'):this.t('待确认')},
    planDragSpot(){return this.planStops[this.planDragIndex]||null},
    canContinue(){return this.draftReady&&this.stops.length>0&&!this.busy&&!this.planBusy&&!this.planError&&!!this.planOverview&&!!this.planOverview.complete},
    gateLabels(){return this.gates.map(g=>this.t(g.label))},
    plannerMapData(){
      const spots=(this.catalog||[]).filter(p=>Number.isFinite(Number(p.latitude))&&Number.isFinite(Number(p.longitude)))
      if(!spots.length)return null
      const markers=spots.map((p,i)=>({id:i+1,latitude:Number(p.latitude),longitude:Number(p.longitude)}))
      const points=markers.map(m=>({latitude:m.latitude,longitude:m.longitude}))
      const route=this.planOverview?roadMap(this.planOverview):null
      return {markers,polyline:(route&&route.polyline)||[],points,legIndexes:(route&&route.legIndexes)||[],center:(route&&route.center)||points[0]}
    },
    plannerMarkerLabels(){const labels={};(this.catalog||[]).forEach((p,i)=>{labels[i+1]=this.t(p.name)});return labels},
    plannerSelectedMarkers(){const ids=this.selectedIds.map(String);return (this.catalog||[]).map((p,i)=>ids.includes(String(p.id))?i+1:null).filter(Boolean)},
    planSelectedMarkers(){return this.planStops.map((_,i)=>i+1)},
    canGenerate(){
      return !!(this.planProgress.time&&this.planProgress.gate&&this.planProgress.interest&&this.planProgress.pace
        &&this.stops.length>0&&this.pickedGuide&&!this.stationPlanBusy)
    },
    missingNeeds(){
      const needs=[]
      if(!this.planProgress.time||!this.planProgress.gate)needs.push(this.t('基础条件'))
      if(!this.planProgress.interest||!this.planProgress.pace)needs.push(this.t('游玩偏好'))
      if(!this.stops.length)needs.push(this.t('选点方式'))
      if(!this.pickedGuide)needs.push(this.t('伴游选择'))
      return needs
    },
    extraEditorStyle(){
      const r=this.extraEditorRect||{}
      return 'left:'+(r.left||16)+'px;top:'+(r.top||260)+'px;width:'+(r.width||320)+'px;height:'+(r.height||110)+'px'
    },
    knowledgeSections(){const p=this.current||{};return [{key:'description',title:'景点介绍'},{key:'history_detail',title:'历史与文化'},{key:'tour_tips',title:'值得留意'},{key:'photo_tips',title:'拍照建议'},{key:'best_season',title:'季节建议'}].map(s=>({...s,text:p[s.key]})).filter(s=>s.text)},
  },
  onLoad(query){
    this.restorePlannerProgress()
    this.applyRoutePrefill()
    this.applyResumeSnapshot(query)
    this._context=scenicContext();this._disposed=false
    const info=uni.getSystemInfoSync();this.statusH=info.statusBarHeight||20
    this.panel=['catalog','list','plan'].includes(query?.view)?query.view:'';this.entryPanel=this.panel
    // 本次打开 App 还没手动加入过景点：无论先进图鉴还是先进规划，都从空开始。
    this._freshPlan=!query?.spotIds&&!uni.getStorageSync('scenic-selection-touched')
    if(query?.spotId)this.currentId=query.spotId
    this._handoff=query?.spotIds?query:null
    this._hintTimer=setTimeout(()=>{this.loadingHintVisible=true},180)
    this._wantResult=query?.result==='1'
    // 扫码领取后网页端带来的规划条件：回填到「路径规划」表单。
    // App 端 getStorageSync 有时直接返回 JSON 字符串，这里统一解析。
    const rawPrefill=query?.prefill==='1'?uni.getStorageSync('web-plan-prefill'):null
    this._webPrefill=null
    if(rawPrefill){
      if(typeof rawPrefill==='string'){try{this._webPrefill=JSON.parse(rawPrefill)}catch(_) {this._webPrefill=null}}
      else this._webPrefill=rawPrefill
    }
    if(rawPrefill){try{uni.removeStorageSync('web-plan-prefill')}catch(_) {}}
    this.refresh()
  },
  onShow(){
    if(this._savedGuideId&&!this.pickedGuide)this.loadCompanionGuides()
    const context=scenicContext()
    if(this._context&&context!==this._context){this._context=context;this.busy=false;this.stops=[];this.settings={spot_ids:[]};this.draftReady=false;this.itineraryState={};this.stopAudio();this._loadTask=null;this.refresh()}
    else if(this._loaded&&!this._loadTask)this.refreshDraft()
  },
  watch:{
    stationPlan(){return this.stationPlans[this.stationPlanIndex]||null},
    stationPlanTitle(){const p=this.stationPlan;if(!p)return '';return this.tourLanguage==='en'?(p.title_en||p.title):p.title},
    planKey(){if(this.panel==='plan')this.loadPlan()},
    selectMode(){this.$nextTick(()=>setTimeout(()=>this.updateSegmentUnderline(),30));this.persistPlannerProgress()},
    stops(){this.persistPlannerProgress()},
    showPlanResult(value){if(value)this.$nextTick(()=>this.saveHomeOrbResume())},
    spFilter(value){if(value==='companion')this.loadCompanionGuides();if(value==='spots')this.$nextTick(()=>setTimeout(()=>this.updateSegmentUnderline(),60))},
    panel(value){if(value==='plan')this.loadPlan();else{this._planVersion=(this._planVersion||0)+1;this._planRequest?.abort?.()}},
  },
  onHide(){this.menuOpen=false;this.stopAudio();if(this.planDragActive||this.planGhost)this.cancelPlanDrag()},
  onUnload(){
    // 从规划页直接点底栏「首页」离开时也会走到这里：记下页面状态给首页悬浮球。
    if(this.panel==='plan'||this.showPlanResult)this.saveHomeOrbResume()
    this._disposed=true;clearTimeout(this._hintTimer);clearTimeout(this._planLongPressTimer);clearTimeout(this._planSettleTimer);this.stopPlanAutoScroll();this.stopAudio();this._planVersion=(this._planVersion||0)+1;this._planRequest?.abort?.()
  },
  onBackPress(){
    if(this.showPlanResult){this.showPlanResult=false;return true}
    if(this.showRouteDetails){this.showRouteDetails=false;return true}
    if(this.menuOpen){this.menuOpen=false;return true}
    if(this.panel&&this.panel!==this.entryPanel){this.panel='';return true}
    // 真正离开规划页回首页：记下当前页面与进度，首页悬浮球可以回来。
    this.saveHomeOrbResume()
    return false
  },
  methods:{
    gateLabel(value){const gate=this.gateOptions.find(g=>g.v===value);return gate?gate.l:'东宫门'},
    pickStationTime(minutes){this.stationPlanner.budget=minutes;this.timeMode='preset';this.customMinutes='';this.planProgress.time=true;this.persistPlannerProgress()},
    onCustomMinutes(e){const raw=(e.detail&&e.detail.value||'').replace(/[^0-9]/g,'');this.customMinutes=raw;this.timeMode='custom';const n=Number(raw);if(Number.isFinite(n)&&n>0){this.stationPlanner.budget=Math.min(480,Math.max(20,Math.round(n)));this.planProgress.time=true;this.persistPlannerProgress()}},
    pickStationInterest(value){this.stationPlanner.interest=value||'';this.planProgress.interest=true;this.persistPlannerProgress()},
    pickStationPace(value){this.stationPlanner.pace=value==='relaxed'?'relaxed':'standard';this.planProgress.pace=true;this.persistPlannerProgress()},
    pickGuide(guide){this.pickedGuide=guide;this.persistPlannerProgress()},
    planSignature(){
      const ids=(this.planStops||[]).map(s=>Number(s.spot_id)).join(',')
      return JSON.stringify([this.stationPlanner.start_area,this.stationPlanner.end_area,!!this.stationPlanner.avoid_steps,this.stationPlanner.pace,this.stationPlanner.interest||'',this.stationPlanner.extra||'',ids,String(this.stationPlanner.budget)])
    },
    onGenerateTap(){
      if(this.stationPlanBusy)return
      // 内容没变（包括拖动后的顺序）：直接回到刚才那一页，保留重算后的时长，不再重新优化顺序。
      if(this.planOverview&&this.planOverview.complete&&this._lastPlanSignature===this.planSignature()){
        this.applyBudgetMinutes(this._lastPlanTotal||this.planOverview.total_minutes)
        this.showPlanResult=true
        this.saveHomeOrbResume()
        return
      }
      if(!this.canGenerate){
        uni.showToast({title:this.t('还没完成：')+this.missingNeeds.join('、'),icon:'none'})
        return
      }
      this.generateStationPlans()
    },
    persistPlannerProgress(){
      try{
        let prevGuide=this._savedGuideId||0
        try{
          let prev=uni.getStorageSync('planner-progress')
          if(typeof prev==='string')prev=JSON.parse(prev)
          if(prev&&prev.guideId)prevGuide=Number(prev.guideId)||prevGuide
        }catch(_){ }
        const guideId=this.pickedGuide?Number(this.pickedGuide.guide_id):prevGuide
        if(guideId)this._savedGuideId=guideId
        uni.setStorageSync('planner-progress',{
          progress:{...this.planProgress},
          planner:{...this.stationPlanner},
          selectMode:this.selectMode,
          guideId,
          savedAt:Date.now()
        })
      }catch(_){ }
    },
    saveHomeOrbResume(forceKind){
      try{
        const kind=forceKind||(this.showPlanResult?'plan-result':'plan-form')
        // “返回”不算回到浅层：已经到过结果页/导览页时，不被表单页覆盖。
        const rank={'plan-form':1,'plan-result':2,'tour':3}
        let existing=null
        try{existing=uni.getStorageSync('home-orb-resume')}catch(_){ }
        if(typeof existing==='string'){try{existing=JSON.parse(existing)}catch(_) {existing=null}}
        if(existing&&existing.kind&&(rank[existing.kind]||0)>(rank[kind]||0))return
        if(kind==='plan-result'&&!(this.stationPlans&&this.stationPlans.length))return
        if(kind==='plan-form'&&!this.stops.length)return
        const payload={
          kind,
          progress:{...this.planProgress},
          planner:{...this.stationPlanner},
          selectMode:this.selectMode,
          guideId:this.pickedGuide?this.pickedGuide.guide_id:0,
          savedAt:Date.now()
        }
        if(kind==='plan-result'){
          payload.plan=this.stationPlan||null
          payload.planOverview=this.planOverview||null
          payload.stationPlans=this.stationPlans
          payload.stationPlanIndex=this.stationPlanIndex
          payload.spFilter=this.spFilter
        }
        uni.setStorageSync('home-orb-resume',payload)
      }catch(_){ }
    },
    applyResumeSnapshot(query){
      if(!query||!query.resume)return
      let saved=null
      try{saved=uni.getStorageSync('home-orb-resume')}catch(_){ }
      if(!saved)return
      if(typeof saved==='string'){try{saved=JSON.parse(saved)}catch(_) {saved=null}}
      if(!saved||Date.now()-(Number(saved.savedAt)||0)>6*3600*1000)return
      if(saved.progress)this.planProgress={...this.planProgress,...saved.progress}
      if(saved.planner)this.stationPlanner={...this.stationPlanner,...saved.planner}
      if(saved.selectMode==='together'||saved.selectMode==='self')this.selectMode=saved.selectMode
      if(saved.guideId)this._savedGuideId=Number(saved.guideId)||0
      if(saved.kind==='plan-result'){
        if(saved.plan){
          this.stationPlans=[saved.plan]
          this.stationPlanIndex=0
          this.planOverview=saved.planOverview||saved.plan.route
        this._lastPlanTotal=Number(this.planOverview&&this.planOverview.total_minutes)||0
        this._lastPlanSpotIds=(saved.plan.route&&saved.plan.route.stops?saved.plan.route.stops:[]).map(s=>Number(s.spot_id)).sort((a,b)=>a-b).join(',')
        this.$nextTick(()=>{this._lastPlanSignature=this.planSignature()})
          if(saved.spFilter)this.spFilter=saved.spFilter
          // 先标记数据已就绪再切结果页，避免先闪一下表单/骨架屏。
          this.draftReady=true
          this.showPlanResult=true
        }else{
          // 没拿到完整快照时按同样的条件重算一次，进入结果页。
          setTimeout(()=>{try{this.generateStationPlans()}catch(_){ }},700)
        }
      }
      this.persistPlannerProgress()
    },
    restorePlannerProgress(){
      setTimeout(()=>{ if(this._savedGuideId&&!this.pickedGuide)this.loadCompanionGuides() },300)
      let saved=null
      try{saved=uni.getStorageSync('planner-progress')}catch(_){ }
      if(!saved)return
      if(typeof saved==='string'){try{saved=JSON.parse(saved)}catch(_) {saved=null}}
      if(!saved||Date.now()-(Number(saved.savedAt)||0)>7*24*3600*1000)return
      if(saved.progress)this.planProgress={...this.planProgress,...saved.progress}
      if(saved.planner)this.stationPlanner={...this.stationPlanner,...saved.planner}
      if(saved.selectMode==='together'||saved.selectMode==='self')this.selectMode=saved.selectMode
      this._savedGuideId=Number(saved.guideId)||0
    },
    applyRoutePrefill(){
      let prefill=null
      try{prefill=uni.getStorageSync('planner-route-prefill')}catch(_){ }
      if(!prefill)return
      try{uni.removeStorageSync('planner-route-prefill')}catch(_){ }
      if(typeof prefill==='string'){try{prefill=JSON.parse(prefill)}catch(_) {prefill=null}}
      if(!prefill||Date.now()-(Number(prefill.savedAt)||0)>10*60*1000)return
      const budget=Number(prefill.budget)
      if(Number.isFinite(budget)&&budget>0){
        this.stationPlanner.budget=Math.min(480,Math.max(20,Math.round(budget)))
        // 主题路线的时长通常不是整小时：显示为“自定义 N 分钟”。
        if([60,120,180,240].includes(this.stationPlanner.budget)){
          this.timeMode='preset';this.customMinutes=''
        }else{
          this.timeMode='custom';this.customMinutes=String(this.stationPlanner.budget)
        }
      }
      this.stationPlanner.end_area=this.stationPlanner.end_area||'east'
      this.stationPlanner.interest=''
      this.stationPlanner.pace='standard'
      this.planProgress={time:true,gate:true,interest:true,pace:true}
      this.selectMode='self'
      this.persistPlannerProgress()
    },
    openExtraEditor(){
      const query=uni.createSelectorQuery().in(this)
      query.select('.sp-extra-display').boundingClientRect(rect=>{
        const info=uni.getSystemInfoSync()
        this._winH=info.windowHeight||800
        if(rect){this.extraEditorRect={left:Math.round(rect.left),top:Math.round(rect.top),width:Math.round(rect.width),height:Math.round(rect.height)}}
        this.extraEditorTop=rect?Math.round(rect.top):260
        this.extraEditorValue=this.stationPlanner.extra||''
        this.extraEditorLift=0
        this.extraEditorOpen=true
        this.$nextTick(()=>{setTimeout(()=>{this.extraEditorFocus=true},60)})
      }).exec()
    },
    onExtraInput(event){
      const value=String((event&&event.detail&&event.detail.value)||'')
      this.extraEditorValue=value
      this.stationPlanner.extra=value
    },
    onExtraEditorFocus(){
      this.extraEditorFocus=true
      if(this._kbListener)return
      try{
        this._kbListener=true
        uni.onKeyboardHeightChange(res=>{
          const h=Number(res&&res.height)||0
          const info=uni.getSystemInfoSync()
          const winH=info.windowHeight||this._winH||800
          const barH=180
          const maxLift=Math.max(0,this.extraEditorTop-40)
          const lift=Math.max(0,this.extraEditorTop+barH-(winH-h)+10)
          this.extraEditorLift=Math.min(lift,maxLift)
        })
      }catch(_){this._kbListener=false}
    },
    closeExtraEditor(){
      try{ if(this._kbListener&&uni.offKeyboardHeightChange)uni.offKeyboardHeightChange() }catch(_){ }
      this._kbListener=false
      this.extraEditorOpen=false;this.extraEditorFocus=false;this.extraEditorLift=0
    },
    onExtraEditorBlur(){
      // 键盘收起或点到别处就结束输入，内容已经在输入过程中实时写回卡片。
      setTimeout(()=>{ if(this.extraEditorOpen)this.closeExtraEditor() },100)
    },
    mediaUrl(url){
      const text=String(url||'').trim()
      if(!text)return ''
      const marker='/api/v1/files/'
      if(/^https?:\/\//i.test(text)){
        const at=text.indexOf(marker)
        return at>=0?SERVER_ORIGIN+text.slice(at):text
      }
      return text.charAt(0)==='/'?SERVER_ORIGIN+text:SERVER_ORIGIN+'/'+text
    },
    guideImage(guide){
      if(!guide||this.failedGuideImages[guide.guide_id])return '/static/guide/default-guide.png'
      return this.mediaUrl(guide.poster_image||guide.avatar)
    },
    loadCompanionGuides(){
      if(this.guides.length)return
      if(this._guidesLoading)return
      this._guidesLoading=true
      const token=uni.getStorageSync('token')||''
      uni.request({url:SERVER_ORIGIN+'/tour-session/guides?language='+(this.tourLanguage==='en'?'en':'zh'),timeout:15000,header:token?{Authorization:'Bearer '+token}:{},
        success:res=>{const body=res.data||{};const data=body.data||body;const list=(data.guide_list||data.data?.guide_list||[]).filter(g=>g&&g.guide_id)
          list.forEach(g=>{g.poster_image=this.mediaUrl(g.poster_image);g.avatar=this.mediaUrl(g.avatar)})
          if(!list.some(g=>Number(g.guide_id)===2))list.push({guide_id:2,name:'文轩',poster_image:SERVER_ORIGIN+'/api/v1/files/digital_guide/covers/wenxuan-transparent.png',render_mode:'xingyun'})
          this.guides=list
          if(this._savedGuideId&&!this.pickedGuide){
            const saved=list.find(g=>Number(g.guide_id)===Number(this._savedGuideId))
            if(saved)this.pickedGuide=saved
          }},
        complete:()=>{this._guidesLoading=false}})
    },
    pickStationGate(value){this.stationPlanner.end_area=value;this.planProgress.gate=true;this.persistPlannerProgress();this.gateMenuOpen=false;this.plannerFocus=this.gateFocus[value]||null},
    updateSegmentUnderline(){
      try{
        const query=uni.createSelectorQuery().in(this)
        query.select('.sp-segment').boundingClientRect()
        query.selectAll('.sp-segment button').boundingClientRect()
        query.exec(res=>{
          const seg=res&&res[0],rects=res&&res[1]
          if(!seg||!rects||!rects.length)return
          const rect=rects[this.selectMode==='together'?1:0]||rects[0]
          this.segmentUnderline={left:rect.left-seg.left,width:rect.width}
        })
      }catch(_){}
    },
    alive(context){return !this._disposed&&context===scenicContext()},
    cover(place){return place?SCENIC_COVERS[place.name]||'':''},
    toast(message){uni.showToast({title:this.t(message),icon:'none'})},
    gateIndex(value){const index=this.gates.findIndex(g=>g.value===value);return index<0?0:index},
    openPanel(panel){
      this.stopAudio();this.menuOpen=false;this.panel=panel;this.introOpen=false
      if(panel==='plan'&&!uni.getStorageSync('scenic-selection-touched')&&this.stops.length){
        this._freshPlan=false
        this.clearUntouchedSelection()
      }
    },
    choosePlace(id){if(!this.catalog.some(p=>String(p.id)===String(id)))return;this.stopAudio();this.currentId=id;this.panel='';this.introOpen=false;this.menuOpen=false},
    previewPhoto(place){const src=this.cover(place);if(src)uni.previewImage({current:src,urls:[src]})},
    onTouchStart(e){const p=e.touches?.[0];if(p)this._touch={x:p.clientX,y:p.clientY}},
    onKnowledgeScroll(e){this.knowledgeTop=(e.detail&&e.detail.scrollTop)||0},
    onKnowledgeTouchStart(e){const p=e.touches?.[0];if(p)this._kTouch={x:p.clientX,y:p.clientY}},
    onKnowledgeTouchEnd(e){
      const p=e.changedTouches?.[0],start=this._kTouch
      this._kTouch=null
      if(!p||!start||this.knowledgeTop>0)return
      const dy=p.clientY-start.y
      if(dy>70&&Math.abs(dy)>Math.abs(p.clientX-start.x)*1.2)this.introOpen=false
    },
    onTouchEnd(e){
      const p=e.changedTouches?.[0],start=this._touch
      this._touch=null
      if(!p||!start)return
      const dx=p.clientX-start.x,dy=p.clientY-start.y
      // 上滑展开全屏毛玻璃介绍；展开后下滑收起。
      if(Math.abs(dy)>=60&&Math.abs(dy)>Math.abs(dx)*1.2){
        if(dy<0&&!this.introOpen)this.introOpen=true
        else if(dy>0&&this.introOpen)this.introOpen=false
        return
      }
      if(this.introOpen)return
      if(Math.abs(dx)<60||Math.abs(dx)<Math.abs(dy)*1.5)return
      const index=this.catalog.findIndex(p=>p.id===this.current?.id),next=this.catalog[index+(dx<0?1:-1)]
      if(next)this.choosePlace(next.id)
    },
    goBack(){
      // 路线结果页返回到「生成方案」页面，而不是直接退出
      if(this.showPlanResult){this.showPlanResult=false;return}
      if(this.showRouteDetails){this.showRouteDetails=false;return}
      if(this.panel&&this.panel!==this.entryPanel){this.panel='';return}
      this.saveHomeOrbResume()
      uni.navigateBack({delta:1,fail:()=>uni.reLaunch({url:'/pages/tabs/tabs?tab=home'})})
    },
    async refresh(){
      if(this._loadTask)return this._loadTask
      const context=scenicContext();this.catalogError='';this.loading=true
      const task=Promise.all([
        loadScenicCatalog().then(places=>{if(this.alive(context)){this.catalog=places;if(this.currentId!==null&&!places.some(p=>String(p.id)===String(this.currentId)))this.catalogError='该景点已不可用，请从全部景点重新选择'}}).catch(error=>{if(this.alive(context)&&!this.catalog.length)this.catalogError=error.message}),
        this.refreshDraft(),
      ]).then(async()=>{if(!this.alive(context))return;await this.applyHandoff();if(this.alive(context)&&this._webPrefill)this.applyWebPrefill()}).finally(()=>{if(this.alive(context)){this.loading=false;this._loaded=true;if(this._loadTask===task)this._loadTask=null}})
      this._loadTask=task;return task
    },
    applyDraft(draft){
      this.settings=draft.settings;this.draftReady=true;this.draftError=''
      // 网页端回填后，不让服务端草稿再把景点清空。
      if(this._prefillLock)return
      if(this._freshPlan){
        // 本次还没手动加入过景点：页面直接从空开始，清掉旧景点，并把同行/出入口恢复为未选择。
        this._freshPlan=false;this.stops=[]
        this.clearUntouchedSelection(draft.stops)
      }else{
        this.stops=draft.stops
        if(!uni.getStorageSync('scenic-settings-touched')&&!this._settingsReset){
          const s=draft.settings||{}
          if(s.start_area!=='auto'||s.end_area!=='auto'||s.elderly||s.children||s.avoid_steps){
            this._settingsReset=true
            this.resetDefaultSettings()
          }
        }
      }
    },
    async resetDefaultSettings(){
      const context=scenicContext()
      try{
        await scenicRequest('/scenic-settings',{method:'PUT',data:{start_area:'auto',end_area:'auto',elderly:false,children:false,avoid_steps:false}})
        if(this.alive(context))await this.refreshDraft()
      }catch(_){}
    },
    async clearUntouchedSelection(stops){
      const context=scenicContext();this.busy=true
      try{
        for(const stop of (stops||[]))await scenicRequest('/scenic-selection/'+stop.id,{method:'DELETE'})
        await scenicRequest('/scenic-settings',{method:'PUT',data:{start_area:'auto',end_area:'auto',elderly:false,children:false,avoid_steps:false}})
        if(this.alive(context))await this.refreshDraft()
      }catch(_){}
      finally{if(this.alive(context))this.busy=false}
    },
    async refreshDraft(){
      const context=scenicContext(),version=this._draftVersion=(this._draftVersion||0)+1
      try{const draft=await loadScenicDraft();if(this.alive(context)&&version===this._draftVersion)this.applyDraft(draft)}
      catch(error){if(this.alive(context)&&version===this._draftVersion)this.draftError=error.message}
    },
    async applyHandoff(){
      const query=this._handoff;if(!query||!this.draftReady||!this.catalog.length)return
      this._handoff=null
      const ids=String(query.spotIds).split(',').map(Number)
      if(!ids.length||ids.length>20||new Set(ids).size!==ids.length||ids.some(id=>!Number.isInteger(id)||!this.catalog.some(p=>p.id===id))){this.toast('部分景点已不可用，请重新选择');return}
      const context=scenicContext();this.busy=true
      try{
        for(const id of ids)if(!this.stops.some(p=>p.id===id))await scenicRequest('/scenic-selection?spot_id='+id,{method:'PUT'})
        for(const stop of this.stops)if(!ids.includes(stop.id))await scenicRequest('/scenic-selection/'+stop.id,{method:'DELETE'})
        const data={spot_ids:ids}
        for(const key of ['elderly','children'])if(query[key]!==undefined)data[key]=query[key]==='1'
        if(query.avoidSteps!==undefined)data.avoid_steps=query.avoidSteps==='1'
        for(const [source,key]of [['startArea','start_area'],['endArea','end_area']])if(GATES.some(g=>g.value===query[source]))data[key]=query[source]
        await scenicRequest('/scenic-settings',{method:'PUT',data})
        try{uni.setStorageSync('scenic-selection-touched',1)}catch(_){}
        if(this.alive(context))await this.refreshDraft()
      }catch(error){if(this.alive(context)){this.toast(error.message);await this.refreshDraft()}}
      finally{if(this.alive(context))this.busy=false}
    },
    applyWebPrefill(){
      const p=this._webPrefill;this._webPrefill=null
      if(!p||typeof p!=='object'||!this.catalog.length)return
      this._prefillLock=true
      const budget=Math.min(480,Math.max(20,Math.round(Number(p.b)||120)))
      const interest=['history','nature','photo','family'].includes(p.i)?p.i:''
      this.stationPlanner={
        budget,
        start_area:'east',
        end_area:['east','north','south','return'].includes(p.e)?p.e:'east',
        avoid_steps:!!Number(p.s),
        interest,
        pace:p.p==='relaxed'?'relaxed':'standard',
        extra:typeof p.x==='string'?p.x:''
      }
      const preset=[60,120,180,240].includes(budget)
      this.timeMode=preset?'preset':'custom'
      this.customMinutes=preset?'':String(budget)
      this.selectMode=Number(p.g)?'together':'self'
      const ids=(Array.isArray(p.ids)?p.ids:[]).map(Number).filter(id=>Number.isInteger(id)&&id>0)
      this.stops=ids.map(id=>{const place=this.catalog.find(x=>String(x.id)===String(id));return place?{id:place.id,name:place.name}:null}).filter(Boolean)
      this.panel='plan';this.spFilter='basic';this.showPlanResult=false;this.stationPlans=[];this.stationPlanError='';this.planError=''
      try{uni.setStorageSync('scenic-selection-touched',1)}catch(_) {}
    },
    async toggleStop(id){
      if(this.busy||!this.draftReady)return
      this.stationPlanError='';this.planError='';this.showPlanResult=false
      const context=scenicContext(),removing=this.stops.some(p=>p.id===id);this.busy=true;this.menuOpen=false
      try{
        await scenicRequest(removing?'/scenic-selection/'+id:'/scenic-selection?spot_id='+id,{method:removing?'DELETE':'PUT'})
        try{uni.removeStorageSync('wander-last-handoff')}catch(_){}
        try{uni.setStorageSync('scenic-selection-touched',1)}catch(_){}
        if(this.alive(context))await this.refreshDraft()
        // 最新加入的景点排在路线第一位，进入路径规划时以它为主。
        if(!removing&&this.alive(context)){
          try{
            const next=[id,...this.stops.filter(p=>p.id!==id).map(p=>p.id)]
            await scenicRequest('/scenic-settings',{method:'PUT',data:{spot_ids:next}})
            if(this.alive(context))await this.refreshDraft()
          }catch(_){}
        }
      }
      catch(error){if(this.alive(context))this.toast(error.message)}
      finally{if(this.alive(context))this.busy=false}
    },
    async saveSettings(data){
      if(this.busy||!this.draftReady)return
      // 选了老人/小孩就按无障碍路线：强制避开已有台阶路段。
      if('elderly' in data || 'children' in data){
        const elderly='elderly' in data?!!data.elderly:!!this.settings.elderly
        const children='children' in data?!!data.children:!!this.settings.children
        data.avoid_steps = elderly || children ? true : false
      }
      const context=scenicContext();this.busy=true
      try{const settings=await scenicRequest('/scenic-settings',{method:'PUT',data});try{uni.setStorageSync('scenic-settings-touched',1)}catch(_){};if(!this.alive(context))return;this.settings=settings;if(data.spot_ids){const rows=new Map(this.stops.map(p=>[p.id,p]));this.stops=settings.spot_ids.map(id=>rows.get(id)).filter(Boolean)}}
      catch(error){if(this.alive(context))this.toast(error.message)}
      finally{if(this.alive(context))this.busy=false}
    },
    planFact(value){return value==null?this.t('待确认'):value+' '+this.t('分钟')},
    loadPlan(){
      if(this.panel!=='plan'||!this.draftReady||!this.selectedIds.length){
        this.planOverview=null;this.planBusy=false;this.planError='';return
      }
      const version=this._planVersion=(this._planVersion||0)+1
      this._planRequest?.abort?.()
      const options=previewOptions(this.selectedIds,this.routePlan,this.routePlan.pace)
      this.planBusy=true;this.planError=''
      const context=scenicContext()
      const request=this._planRequest=routeRequest('/tour-experience/route-preview',options,0,15000)
      request.promise.then(data=>{if(this._disposed||version!==this._planVersion||context!==scenicContext())return;this.planOverview=data;if(this._wantResult){this.showPlanResult=true;this._wantResult=false}})
        .catch(error=>{if(this._disposed||version!==this._planVersion)return;this.planOverview=null;this.planError=error.message})
        .finally(()=>{if(!this._disposed&&version===this._planVersion)this.planBusy=false})
    },
    clearStops(){this.stops=[]},
    generateStationPlans(){
      if(this.stationPlanBusy)return
      const stopKey=this.stops.map(s=>Number(s.id)).sort((a,b)=>a-b).join(',')
      // 用上一次真正算出来的总时长当预算（重排后顺序变了、但景点集合没变，也认这份总时长）。
      const knownTotal=(this._lastPlanSpotIds===stopKey&&Number(this._lastPlanTotal)>0)?Number(this._lastPlanTotal):0
      this.applyBudgetMinutes(knownTotal>0?knownTotal:(Number(this.stationPlanner.budget)||120))
      const spotIds=this.stops.map(s=>Number(s.id))
      this.stationPlanBusy=true;this.stationPlanError='';this.stationPlans=[];this.stationPlanIndex=0
      const attempt=(tries)=>{
        const budget=this.stationPlanner.budget
        return scenicRequest('/plan-walk',{method:'POST',data:{budget,start_area:this.stationPlanner.start_area,end_area:this.stationPlanner.end_area,avoid_steps:!!this.stationPlanner.avoid_steps,spot_ids:spotIds,interest:this.stationPlanner.interest||'',extra:this.stationPlanner.extra||'',pace:(this.stationPlanner.pace==='relaxed'||this.stationPlanner.avoid_steps)?'relaxed':'standard'}})
          .then(data=>{
            const plans=Array.isArray(data&&data.plans)?data.plans:[]
            if(!plans.length)throw new Error(this.t('没有找到合适的方案，请调整时间或终点'))
            this.stationPlans=plans;this.stationPlanIndex=0;this.planOverview=plans[0].route
            this.showPlanResult=true;this.planStopOrder=[]
            this._lastPlanTotal=Number(this.planOverview&&this.planOverview.total_minutes)||0
            this._lastPlanSpotIds=stopKey
            this.$nextTick(()=>{this._lastPlanSignature=this.planSignature()})
            this.saveHomeOrbResume()
            this.savePendingRoute(this.planOverview,{start_area:this.stationPlanner.start_area,end_area:this.stationPlanner.end_area,avoid_steps:!!this.stationPlanner.avoid_steps,pace:(this.stationPlanner.pace==='relaxed'||this.stationPlanner.avoid_steps)?'relaxed':'standard'})
          })
          .catch(error=>{
            const msg=String((error&&error.data&&error.data.detail)||(error&&error.message)||'')
            // 差几分钟时静默上调一次预算，不弹提示、不循环。
            if(msg.indexOf('超出时间预算')>=0&&tries<2){
              this.applyBudgetMinutes(Math.min(480,Math.max(Number(this.stationPlanner.budget)+30,knownTotal||0)))
              return attempt(tries+1)
            }
            this.stationPlanError=error?.data?.detail||error?.message||this.t('规划失败，请重试')
          })
      }
      attempt(0).finally(()=>{this.stationPlanBusy=false})
    },
    applyBudgetMinutes(value){
      const minutes=Math.min(480,Math.max(20,Math.round(Number(value)||120)))
      this.stationPlanner.budget=minutes
      if([60,120,180,240].includes(minutes)){this.timeMode='preset';this.customMinutes=''}
      else{this.timeMode='custom';this.customMinutes=String(minutes)}
      this.persistPlannerProgress()
    },
    chooseStationPlan(index){this.stationPlanIndex=index},
    onPlanStopsScroll(event){
      const top=event&&event.detail&&Number.isFinite(event.detail.scrollTop)?event.detail.scrollTop:(this._planScrollTopNow||0)
      this._planScrollTopNow=top
    },
    onPlanGripTouchStart(index,event){
      if(this.busy||this.planDragActive||this.planDragSettling||this.planStops.length<2)return
      const touch=(event&&event.touches&&event.touches[0])||(event&&event.changedTouches&&event.changedTouches[0])
      if(!touch)return
      this._planGripIndex=index
      this._planGripStartX=touch.clientX
      this._planGripStartY=touch.clientY
      clearTimeout(this._planLongPressTimer)
      // 只有按住把手不动 320ms 才抬起条目；快速上下滑仍交给列表滚动。
      this._planLongPressTimer=setTimeout(()=>{this._planLongPressTimer=null;this.startPlanDrag(index)},320)
    },
    onPlanGripTouchMove(event){
      if(this.planDragActive){
        // 拖动中吞掉浏览器滚动，避免列表跟手势一起跑。
        if(event&&event.preventDefault)try{event.preventDefault()}catch(_){}
        this.onPlanDragMove(event)
        return
      }
      const touch=(event&&event.touches&&event.touches[0])||(event&&event.changedTouches&&event.changedTouches[0])
      if(!touch||!this._planLongPressTimer)return
      if(Math.abs(touch.clientY-(this._planGripStartY||0))>8||Math.abs(touch.clientX-(this._planGripStartX||0))>8){
        clearTimeout(this._planLongPressTimer);this._planLongPressTimer=null
      }
    },
    onPlanGripTouchEnd(event){
      clearTimeout(this._planLongPressTimer);this._planLongPressTimer=null
      if(this.planDragActive)this.onPlanDragEnd(event)
    },
    onPlanGripTouchCancel(){
      clearTimeout(this._planLongPressTimer);this._planLongPressTimer=null
      if(this.planDragActive)this.cancelPlanDrag()
    },
    startPlanDrag(index){
      if(this.busy||this.planDragActive||this.planDragSettling||this.planStops.length<2)return
      if(index<0||index>=this.planStops.length)return
      this.planDragActive=true;this.planDragSettling=false
      this.planDragIndex=index;this.planDragTarget=index;this.planDragY=0
      this.planDragStartY=this._planGripStartY||0
      this._planDragStartIndex=index
      this._planDragRects=null;this._planDragScrollRect=null;this.planGhost=null
      // 长按抬起时给一次轻触反馈；不支持震动的端忽略。
      try{uni.vibrateShort&&uni.vibrateShort({type:'light'})}catch(_){}
      try{
        const query=uni.createSelectorQuery().in(this)
        query.select('.plan-stops-scroll').boundingClientRect()
        query.select('.plan-stops-scroll').scrollOffset()
        query.select('.plan-stops').boundingClientRect()
        query.selectAll('.plan-stop').boundingClientRect()
        query.exec(res=>{
          if(!this.planDragActive||!res)return
          const scrollRect=res[0],offset=res[1],contentRect=res[2],rects=res[3]
          if(!rects||!rects.length)return
          const rect=rects[index]||rects[0]
          this._planDragRects=rects.map(r=>({top:r.top,height:r.height}))
          this._planDragScrollRect=scrollRect?{top:scrollRect.top,bottom:scrollRect.top+scrollRect.height}:null
          this._planViewportHeight=scrollRect?scrollRect.height:0
          this._planContentHeight=contentRect?contentRect.height:0
          this.planScrollStart=Number.isFinite(this._planScrollTopNow)?this._planScrollTopNow:(offset&&Number.isFinite(offset.scrollTop)?offset.scrollTop:0)
          this.planScrollTop=this.planScrollStart
          this.planDragRowH=rect.height||50
          if(!this.planDragStartY)this.planDragStartY=rect.top+rect.height/2
          this.planGhost={top:rect.top,left:rect.left,width:rect.width,height:rect.height}
        })
      }catch(_){}
    },
    onPlanDragMove(event){
      if(!this.planDragActive||this.planDragSettling)return
      const touch=(event&&event.touches&&event.touches[0])||(event&&event.changedTouches&&event.changedTouches[0])
      if(!touch)return
      this._planLastTouchY=touch.clientY
      this.planDragY=touch.clientY-this.planDragStartY
      this.updatePlanDragTarget()
      this.updatePlanAutoScroll(touch.clientY)
    },
    updatePlanDragTarget(){
      const rects=this._planDragRects
      if(!rects||!rects.length){
        const step=Math.round(this.planDragY/(this.planDragRowH||50))
        this.planDragTarget=Math.max(0,Math.min(this.planStops.length-1,this._planDragStartIndex+step))
        return
      }
      // 用悬浮条中心与各条目中线比较，取插入位置；滚动窗口内滚动后按滚动差补偿。
      const ghostH=(this.planGhost&&this.planGhost.height)||this.planDragRowH||50
      const base=this.planGhost?this.planGhost.top:(this.planDragStartY-ghostH/2)
      const centerY=base+this.planDragY+ghostH/2
      const scrolled=(this.planScrollTop||0)-(this.planScrollStart||0)
      let insert=0
      for(let i=0;i<rects.length;i++){
        if(i===this._planDragStartIndex)continue
        const mid=rects[i].top-scrolled+rects[i].height/2
        if(centerY>mid)insert++
      }
      this.planDragTarget=Math.max(0,Math.min(this.planStops.length-1,insert))
    },
    updatePlanAutoScroll(y){
      const rect=this._planDragScrollRect
      if(!rect)return
      // 只在自己主动拖出一段距离后才启用边缘滚动，避免刚按住边缘条目就连续滚动。
      if(Math.abs(this.planDragY||0)<24){this.stopPlanAutoScroll();return}
      const edge=Math.min(56,Math.max(32,(rect.bottom-rect.top)/4))
      let dir=0
      if(y<rect.top+edge)dir=-1
      else if(y>rect.bottom-edge)dir=1
      this._planAutoScrollDir=dir
      if(dir&&!this._planAutoScrollTimer)this._planAutoScrollTimer=setInterval(()=>{this.tickPlanAutoScroll()},16)
      else if(!dir)this.stopPlanAutoScroll()
    },
    tickPlanAutoScroll(){
      if(!this.planDragActive||this.planDragSettling||!this._planAutoScrollDir){this.stopPlanAutoScroll();return}
      const max=Math.max(0,(this._planContentHeight||0)-(this._planViewportHeight||0))
      const next=Math.max(0,Math.min(max,(this.planScrollTop||0)+this._planAutoScrollDir*7))
      if(next===(this.planScrollTop||0)){this.stopPlanAutoScroll();return}
      this.planScrollTop=next
      this.updatePlanDragTarget()
    },
    stopPlanAutoScroll(){
      if(this._planAutoScrollTimer){clearInterval(this._planAutoScrollTimer);this._planAutoScrollTimer=null}
      this._planAutoScrollDir=0
    },
    planShiftStyle(index){
      if(!this.planDragActive||index===this.planDragIndex)return ''
      const from=this.planDragIndex,to=this.planDragTarget
      if(from<0||to<0||from===to)return ''
      const h=this.planDragRowH||50
      // 被抬起的条目从队列里抽走，其余条目按落点重新排队；弹簧曲线带一点回弹。
      const spring='transition:transform 320ms cubic-bezier(.2,1.3,.4,1);will-change:transform'
      if(to>from&&index>from&&index<=to)return 'transform:translate3d(0,-'+h+'px,0);'+spring
      if(to<from&&index>=to&&index<from)return 'transform:translate3d(0,'+h+'px,0);'+spring
      return ''
    },
    planGhostStyle(){
      const ghost=this.planGhost
      if(!ghost)return ''
      const scale=this.planDragSettling?1:1.02
      const transition=this.planDragSettling?'transition:transform 260ms cubic-bezier(.2,.9,.3,1);':'transition:none;'
      return 'position:fixed;left:'+ghost.left+'px;top:'+ghost.top+'px;width:'+ghost.width+'px;height:'+ghost.height+'px;z-index:70;margin:0;box-sizing:border-box;pointer-events:none;border-bottom:0;border-radius:12px;background:#fff;box-shadow:0 14px 30px rgba(70,50,130,.24);transform:translate3d(0,'+this.planDragY+'px,0) scale('+scale+');'+transition
    },
    onPlanDragEnd(){
      if(!this.planDragActive||this.planDragSettling)return
      this.stopPlanAutoScroll()
      const from=this.planDragIndex,to=this.planDragTarget
      if(!this.planGhost){this.finishPlanDrag(from,to);return}
      // 松手吸附：悬浮条先滑到落点，等它停稳后再提交顺序。
      this.planDragSettling=true
      this.planDragY=from>=0&&to>=0?(to-from)*(this.planDragRowH||this.planGhost.height||50):0
      clearTimeout(this._planSettleTimer)
      this._planSettleTimer=setTimeout(()=>{this.finishPlanDrag(from,to)},270)
    },
    cancelPlanDrag(){
      if(!this.planDragActive)return
      this.finishPlanDrag(this.planDragIndex,this.planDragIndex)
    },
    finishPlanDrag(from,to){
      clearTimeout(this._planSettleTimer);this._planSettleTimer=null
      clearTimeout(this._planLongPressTimer);this._planLongPressTimer=null
      this.stopPlanAutoScroll()
      if(from>=0&&to>=0&&from!==to){
        const ids=this.planStops.map(stop=>stop.spot_id)
        const moved=ids.splice(from,1)[0]
        ids.splice(to,0,moved)
        this.planStopOrder=ids
        // 顺序变了就按新顺序重新算距离/步行时间/总时长（不回写主题路线卡片）。
        this.$nextTick(()=>{this.recomputePlanOrder(ids)})
      }
      this._planDragRects=null;this._planDragScrollRect=null;this._planGripIndex=-1
      this.planDragActive=false;this.planDragSettling=false
      this.planDragIndex=-1;this.planDragTarget=-1;this.planDragY=0;this.planGhost=null
    },
    async recomputePlanOrder(ids){
      if(!Array.isArray(ids)||ids.length<2)return
      const wanted=ids.map(id=>Number(id)).filter(id=>Number.isInteger(id)&&id>0)
      if(wanted.length<2)return
      try{
        const standardPace=(this.stationPlanner.pace==='relaxed'||this.stationPlanner.avoid_steps)?'relaxed':'standard'
        const request=routeRequest('/tour-experience/route-preview',{
          spot_ids:wanted,
          pace:standardPace,
          start_area:this.stationPlanner.start_area,
          end_area:this.stationPlanner.end_area,
          avoid_steps:!!this.stationPlanner.avoid_steps,
          reserve:0
        },0,15000)
        const route=await request.promise
        if(!route||!Array.isArray(route.stops))throw new Error('empty route')
        this.planOverview=route
        this._lastPlanTotal=Number(route.total_minutes)||0
        this._lastPlanSpotIds=wanted.slice().sort((a,b)=>a-b).join(',')
        this.$nextTick(()=>{this._lastPlanSignature=this.planSignature()})
        if(this.stationPlans[this.stationPlanIndex])this.stationPlans[this.stationPlanIndex].route=route
        // 新路线已经按拖动后的顺序返回，清掉本地排序覆盖。
        this.planStopOrder=[]
        // 把重新计算后的总时长同步回「基础条件」的时间。
        const total=Number(route.total_minutes)
        if(Number.isFinite(total)&&total>0){
          const minutes=Math.min(480,Math.max(20,Math.round(total)))
          this.stationPlanner.budget=minutes
          if([60,120,180,240].includes(minutes)){this.timeMode='preset';this.customMinutes=''}
          else{this.timeMode='custom';this.customMinutes=String(minutes)}
          this.persistPlannerProgress()
        }
        this.saveHomeOrbResume()
      }catch(error){
        uni.showToast({title:this.t('重新计算路线失败，请重试'),icon:'none'})
      }
    },
    savePendingRoute(overview, plan){
      try {
        const ids=((overview&&overview.stops)||[]).map(stop=>Number(stop.spot_id)).filter(id=>Number.isInteger(id)&&id>0)
        if(!ids.length){uni.removeStorageSync('pending-tour-route');return}
        const p=plan||{}
        uni.setStorageSync('pending-tour-route',{ids,plan:{start_area:p.start_area||'auto',end_area:p.end_area||'auto',avoid_steps:!!p.avoid_steps,pace:p.pace==='relaxed'?'relaxed':'standard'},savedAt:Date.now()})
      } catch (_) {}
    },
    retryStationPlans(){this.stationPlanError='';this.planError='';this.stationPlans=[];this.showPlanResult=false;this.generateStationPlans()},
    quickToggleStop(id){
      const place=(this.catalog||[]).find(p=>String(p.id)===String(id))
      if(!place)return
      const removing=this.stops.some(p=>String(p.id)===String(id))
      if(removing)this.stops=this.stops.filter(p=>String(p.id)!==String(id))
      else this.stops=[{id:place.id,name:place.name},...this.stops]
      try{uni.setStorageSync('scenic-selection-touched',1);uni.removeStorageSync('wander-last-handoff')}catch(_){}
      this.stationPlanError='';this.planError='';this.showPlanResult=false
      scenicRequest(removing?'/scenic-selection/'+id:'/scenic-selection?spot_id='+id,{method:removing?'DELETE':'PUT'})
        .catch(()=>{})
        .finally(()=>{this.refreshDraft()})
    },
    retryPlannerError(){this.stationPlanError='';this.planError=''},
    retryPlan(){this.planError='';this.loadPlan()},
    async startTourDirect(ids, plan){
      if(this.busy || !ids || !ids.length) return
      this.busy=true
      try {
        const sid=await startTourSession(ids, plan, this.pickedGuide?this.pickedGuide.guide_id:0)
        try{uni.setStorageSync('home-orb-resume',{kind:'tour',sid:sid,guideId:this.pickedGuide?this.pickedGuide.guide_id:0,savedAt:Date.now()})}catch(_){ }
        uni.navigateTo({url:'/pages/tour/tour?sessionId='+sid})
      } catch(error) {
        uni.showToast({title:this.t(error.message||'开始导览失败，请重试'),icon:'none'})
      } finally { this.busy=false }
    },
    startStationPlan(){
      const plan=this.stationPlan
      const ids=(plan?.route?.stops||[]).map(s=>s.spot_id)
      if(!ids.length)return
      this.startTourDirect(ids,{start_area:this.stationPlanner.start_area,end_area:this.stationPlanner.end_area,avoid_steps:!!this.stationPlanner.avoid_steps,pace:(this.stationPlanner.pace==='relaxed'||this.stationPlanner.avoid_steps)?'relaxed':'standard',total_minutes:plan?.route?.total_minutes})
    },
    chooseGuide(){
      if(this.busy)return
      // 顶部「开始导览」：优先用手动选的景点；没手选时用当前方案里的景点，
      // 否则扫码回填后直接看方案的人会点到没有反应。
      const fromPlan=((this.stationPlan&&this.stationPlan.route&&this.stationPlan.route.stops)||[]).map(s=>Number(s.spot_id))
      const fromOverview=((this.planOverview&&this.planOverview.stops)||[]).map(s=>Number(s.spot_id))
      const fromStops=(this.planStops||[]).map(s=>Number(s.spot_id))
      const chosen=(this.selectedIds&&this.selectedIds.length)?this.selectedIds:(fromStops.length?fromStops:(fromPlan.length?fromPlan:fromOverview))
      const ids=chosen.filter(id=>Number.isInteger(id)&&id>0)
      if(!ids.length){uni.showToast({title:this.t('请先选择景点或生成路线'),icon:'none'});return}
      this.startTourDirect(ids,{...this.routePlan,total_minutes:(this.stationPlan&&this.stationPlan.route&&this.stationPlan.route.total_minutes)||this.planOverview?.total_minutes})
    },
    stopAudio(){
      this._audioVersion=(this._audioVersion||0)+1
      const audio=this._audio;this._audio=null
      if(audio){try{audio.stop();audio.destroy()}catch(_){}}
      this.audioOpen=false;this.audioLoading=false;this.audioPlaying=false;this.audioElapsed=0;this.audioDuration=0
    },
    async toggleAudio(){
      this.menuOpen=false
      if(this.audioOpen){this.stopAudio();return}
      const place=this.current;if(!place)return
      const context=scenicContext(),version=this._audioVersion=(this._audioVersion||0)+1
      const current=()=>this.alive(context)&&version===this._audioVersion&&this.current?.id===place.id
      this.audioOpen=true;this.audioLoading=true
      try{
        const data=await scenicRequest('/scenic-audio/'+place.id)
        if(!current())return
        if(!data?.url)throw new Error('该景点讲解暂不可用')
        const audio=this._audio=uni.createInnerAudioContext()
        audio.onPlay(()=>{if(current()){this.audioPlaying=true;this.audioLoading=false}})
        audio.onPause(()=>{if(current())this.audioPlaying=false})
        audio.onEnded(()=>{if(current())this.audioPlaying=false})
        audio.onTimeUpdate(()=>{if(current()){this.audioElapsed=Number.isFinite(audio.currentTime)?audio.currentTime:0;if(audio.duration>0)this.audioDuration=audio.duration}})
        audio.onCanplay(()=>{if(current())this.audioLoading=false})
        audio.onError(()=>{if(current()){this.stopAudio();this.toast('音频加载失败，请重试')}})
        this.audioDuration=Number.isFinite(data.duration)?data.duration:0
        audio.src=/^https?:\/\//i.test(data.url)?data.url:SERVER_ORIGIN+data.url
        audio.play()
      }catch(error){if(current()){this.stopAudio();this.toast(error.message)}}
    },
    togglePlayback(){if(!this._audio||this.audioLoading)return;try{if(this.audioPlaying)this._audio.pause();else this._audio.play()}catch(_){this.stopAudio();this.toast('音频播放失败，请重试')}},
    formatTime(value){const seconds=Math.max(0,Math.floor(value||0));return Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0')},
  },
}
</script>

<style scoped>
.native-scenic{height:100vh;height:100dvh;display:flex;flex-direction:column;overflow:hidden;background:#fff;color:#282332;padding-bottom:calc(72px + env(safe-area-inset-bottom));box-sizing:border-box}
.native-scenic button{margin:0;padding:0;background:none;border:0;font:inherit;color:inherit;line-height:1.5;border-radius:12px;min-height:44px;display:flex;align-items:center;justify-content:center}
.native-scenic button::after{border:0}.native-scenic button[disabled]{opacity:.45}.native-scenic button:active{transform:scale(.97)}
.scenic-nav{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:8px 18px 10px;flex-shrink:0;background:#fff;z-index:10}.nav-label{font-size:16px;font-weight:600}.nav-more{width:44px;letter-spacing:0;border:1px solid #eee8ff!important;font-size:20px!important}
.nav-more .iconfont{font-size:22px;color:#3d3357}
.scenic-intro{position:relative;flex:1;min-height:0;margin:0;width:100%;box-sizing:border-box;overflow:hidden;border-radius:26px 26px 0 0;background:#f7f4ff}.scenic-photo,.photo-missing,.photo-shade{position:absolute;inset:0;width:100%;height:100%}.photo-missing{display:flex;align-items:center;justify-content:center;color:#8b8495;background:#f4f1f9}.photo-shade{pointer-events:none;background:linear-gradient(180deg,transparent 30%,rgba(22,17,31,.12) 50%,rgba(22,17,31,.83) 100%)}
.intro-content{position:absolute;left:0;right:0;bottom:0;z-index:2;padding:22px 18px 18px;color:white;display:flex;flex-direction:column;max-height:86%;box-sizing:border-box}
.native-scenic.expanded{padding-bottom:0}
.intro-content.expanded{position:absolute;inset:0;z-index:4;max-height:none;border-radius:24px 24px 0 0;overflow:hidden;color:#fff;padding:26px 18px calc(96px + env(safe-area-inset-bottom));background:linear-gradient(135deg,rgba(255,255,255,.20) 0%,rgba(255,255,255,.06) 24%,transparent 48%),linear-gradient(180deg,rgba(33,36,48,.40) 0%,rgba(27,29,42,.52) 45%,rgba(20,22,34,.62) 100%);-webkit-backdrop-filter:blur(28px) saturate(135%);backdrop-filter:blur(28px) saturate(135%);border:1px solid rgba(255,255,255,.72);box-shadow:inset 0 1px 0 rgba(255,255,255,.90),inset 1px 0 0 rgba(255,255,255,.32),inset -1px 0 0 rgba(255,255,255,.18),0 0 12px rgba(255,255,255,.12);text-shadow:0 1px 3px rgba(0,0,0,.22)}
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){.scenic-intro.expanded .scenic-photo{filter:blur(24px)}}
.scenic-intro.expanded .scenic-photo{transform:scale(1.04);transition:transform .35s}
.intro-content.expanded .spot-title{color:#fff}
.intro-content.expanded .section-title{color:#fff}
.intro-content.expanded .section-text{color:rgba(255,255,255,.94)}.thumb-frame{display:flex;align-items:center;margin-bottom:14px;padding:6px;border-radius:18px;background:linear-gradient(160deg,rgba(255,255,255,.16),rgba(20,17,30,.30));border:1px solid rgba(255,255,255,.30);box-shadow:inset 0 1px 0 rgba(255,255,255,.35);flex-shrink:0}.thumb-strip{flex:1;width:0;min-width:0;height:62px;white-space:nowrap}.thumb-frame .thumb{position:relative;display:inline-flex!important;flex-direction:column;width:62px;height:62px;margin-right:6px;border:1px solid #ffffff55!important;border-radius:12px!important;overflow:hidden;vertical-align:top;background:#ffffff20}.thumb.selected{border:2px solid #fff!important}.thumb image{position:absolute;inset:0;width:100%;height:100%}.thumb text{position:absolute;bottom:0;left:0;right:0;text-align:center;white-space:nowrap;font-size:10px;background:linear-gradient(transparent,#1c1729b3);padding:12px 2px 3px;overflow:hidden;text-overflow:ellipsis}.intro-glass{margin-top:12px;padding:14px 2px 10px;background:linear-gradient(180deg,rgba(20,17,30,0) 0%,rgba(20,17,30,.16) 45%,rgba(20,17,30,.24) 100%)}.glass-blur{position:absolute;inset:-48px;width:calc(100% + 96px);height:calc(100% + 96px);filter:blur(26px);opacity:.92;pointer-events:none;z-index:1;-webkit-mask-image:linear-gradient(180deg,transparent 60%,rgba(0,0,0,.6) 76%,#000 92%);mask-image:linear-gradient(180deg,transparent 60%,rgba(0,0,0,.6) 76%,#000 92%)}.intro-content.expanded .intro-glass{margin:0;padding:0;background:none;border:0;box-shadow:none;-webkit-backdrop-filter:none;backdrop-filter:none}.intro-heading{display:flex;align-items:center;justify-content:space-between;flex-shrink:0}.spot-title{font-size:30px;font-weight:600;line-height:1.5}.expand-button{width:44px;font-size:26px!important}.spot-summary{font-size:14px;line-height:1.9;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;margin-top:5px}.intro-actions{display:flex;gap:10px;margin-top:16px;flex-shrink:0}.intro-actions button{flex:1;min-width:0;background:#ffffff26;border:1px solid #ffffff44;font-size:12px;padding:6px 3px}
.knowledge-scroll{flex:1;min-height:0;margin-top:12px}.knowledge-section+.knowledge-section{margin-top:24px}.section-title,.section-text{display:block}.section-title{font-size:18px;font-weight:600;margin-bottom:10px}.section-text{font-size:15px;line-height:1.95;white-space:pre-line}
.catalog-scroll,.plan-scroll{flex:1;height:0;min-height:0;box-sizing:border-box;background:#faf8ff}
.catalog-scroll{background:#f3eefc;border-radius:26px 26px 0 0;overflow:hidden}.catalog-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;padding:16px}.catalog-card{display:flex!important;flex-direction:column;overflow:hidden;background:#fff!important;box-shadow:0 4px 18px #2c1a4e08;min-width:0;align-items:stretch!important}.catalog-card image,.catalog-no-photo{width:100%;height:156px}.catalog-no-photo{display:flex;align-items:center;justify-content:center;background:#eee8f5;color:#8b8495;font-size:13px}.catalog-card>text{padding:10px 12px;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.native-plan{padding:0 0 24px}.plan-scroll{background:#fff}.saved-stops{padding:14px 14px 24px}.plan-options{background:#fff;border-radius:18px;padding:16px;margin-top:16px}.option-heading{font-size:15px;font-weight:600}.option-buttons{display:flex;gap:10px;margin:12px 0 4px}.option-buttons button{flex:1;font-size:13px;background:#f3effa;border:1px solid #eee7f7}.option-buttons .on{color:#6651b2;background:#ece4ff;border-color:#a894e1}.gate-row{display:flex;justify-content:space-between;align-items:center;min-height:52px;border-top:1px solid #f3eff8;font-size:14px}.gate-row picker{padding:12px 0 12px 16px;color:#685490}.primary-action{width:100%;margin-top:20px!important;background:#7962bf!important;color:white!important;padding:12px!important;font-size:15px!important}.saved-stop{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:#fff;border-radius:14px;margin-bottom:10px;font-size:15px}.saved-stop button{color:#7861b3;font-size:13px;padding:4px 12px}.empty-route,.load-state{display:flex;flex-direction:column;gap:20px;align-items:center;justify-content:center;min-height:260px;padding:20px;font-size:15px}.load-state{position:absolute;inset:0}.empty-route button,.load-state button,.inline-error button{padding:8px 18px;background:#eee8ff;color:#6c56a7}.inline-error{padding:16px;display:flex;align-items:center;justify-content:space-between;gap:12px;color:#914e63;font-size:13px}.list-note{display:block;text-align:center;padding:50px 20px;color:#8b8495;font-size:14px}
.menu-mask{position:fixed;inset:0;z-index:90;background:#00000022}.scenic-menu{position:absolute;right:16px;width:auto;min-width:132px;padding:4px;border:1px solid rgba(226,218,245,.92);border-radius:16px;background:#fff;box-shadow:0 16px 40px -18px rgba(46,30,100,.26),0 2px 8px rgba(46,30,100,.05);transform-origin:top right;animation:sm-in .16s cubic-bezier(.2,0,0,1) both}
@keyframes sm-in{from{opacity:0;transform:scale(.96) translateY(-4px)}to{opacity:1;transform:none}}
.scenic-menu .sm-item{display:flex;align-items:center;justify-content:flex-start;gap:10px;min-height:44px;padding:0 8px;border-radius:12px;background:transparent;transition:background-color .16s ease,transform .12s ease}
.scenic-menu .sm-item:active{background:#f7f4ff;transform:scale(.96)}
.scenic-menu .sm-item[disabled]{opacity:.45}
.sm-icon{width:30px;height:30px;flex:none;border-radius:10px;border:1px solid rgba(139,120,230,.55);background:rgba(255,255,255,.55);-webkit-backdrop-filter:blur(8px) saturate(140%);backdrop-filter:blur(8px) saturate(140%);box-shadow:inset 0 1px 0 rgba(255,255,255,.9);display:flex;align-items:center;justify-content:center}
.sm-icon .iconfont{font-size:16px;color:#6a5ae0}
.sm-label{font-size:14px;font-weight:500;color:#2c2740;line-height:1.3;white-space:nowrap}
@media (prefers-reduced-motion: reduce){.scenic-menu{animation:none}.scenic-menu .sm-item{transition:none}}
.native-audio{position:fixed;bottom:calc(84px + env(safe-area-inset-bottom));left:20px;right:20px;z-index:60;display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:18px;border:1px solid #e8def3;background:#fff;box-shadow:0 8px 32px #2e20452b}.native-audio button{width:44px;flex-shrink:0;font-size:20px}.audio-info{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px;font-size:13px}.audio-info text:last-child{font-size:11px;color:#8b8495}.draft-notice{position:fixed;bottom:calc(80px + env(safe-area-inset-bottom));left:24px;right:24px;padding:10px;text-align:center;font-size:12px;color:#5e487c;background:#f5edff;z-index:30;border-radius:12px}
.intro-dots{display:flex;justify-content:center;align-items:center;gap:5px;margin-top:14px;flex-shrink:0}
.intro-dots view{width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.42);transition:background .2s,transform .2s}
.intro-dots view.on{background:#fff;transform:scale(1.25)}
.nav-start{display:flex;align-items:center;gap:6px;min-height:38px;padding:0 14px;border:1px solid #e2dcf5;border-radius:999px;background:#fff;color:#3d3357;font-size:14px;box-shadow:0 4px 14px #2c1a4e0d}
.nav-start .iconfont{font-size:13px;color:#6a5ae0;margin-top:-1px}
.plan-map{height:clamp(240px,34vh,320px);margin:0;border-radius:30px 30px 0 0;overflow:hidden;background:#e8eef1;position:relative;isolation:isolate}
.plan-map :deep(.route-map-wrapper){margin:0;position:absolute;inset:0}
.plan-map :deep(.route-dom-map){height:100%;min-height:0;border-radius:0}
.plan-map :deep(.route-map-message){position:absolute;left:2px;top:2px;margin:0;font-size:11px}
.plan-facts{display:grid;grid-template-columns:repeat(3,1fr);background:#fff;padding:10px 8px 12px;margin:0 0 8px;border-radius:0 0 16px 16px}
.plan-facts view{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0}
.plan-facts text{font-size:12px;color:#6f6685;line-height:1.5}
.plan-facts .fact-value{font-size:18px;font-weight:600;color:#241c36;font-variant-numeric:tabular-nums;line-height:1.4}
.plan-stops-scroll{height:clamp(240px,40vh,420px);width:calc(100% - 24px);margin:10px auto 6px;box-sizing:border-box;border-radius:16px;background:#fff;overflow:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior:contain}
.plan-stops{margin:0;padding:0 14px 26px;background:#fff;border-radius:16px}
.plan-stop-grip{width:34px;height:34px;flex:none;display:flex;align-items:center;justify-content:center;border-radius:10px;color:#241c36;opacity:.5;user-select:none;-webkit-user-select:none;transition:transform .12s ease,opacity .12s ease,background-color .12s ease}
.plan-stop-grip-on,.plan-stop-grip.is-pressed{background:#f3efff;opacity:.85;transform:scale(.94)}
.plan-stop-grip .iconfont,.plan-stop-remove .iconfont{font-size:18px;line-height:1;color:inherit}
.plan-stop{display:flex;align-items:center;gap:10px;padding:14px 0;border-bottom:1px solid #f0edf7}
.plan-stops > .plan-stop:first-child{border-top:1px solid #f0edf7}
.plan-stop:last-child{border-bottom:0}
.plan-stop-no{width:24px;height:24px;flex:none;display:grid;place-items:center;border-radius:50%;background:#ece7fb;color:#5b48a4;font-size:13px;font-variant-numeric:tabular-nums}
.plan-stop-name{flex:1;min-width:0;font-size:16px;font-weight:500;color:#241c36;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.plan-stop-stay{font-size:14px;color:#6f6685;white-space:nowrap}
.plan-stop-remove{width:34px;height:34px;min-height:0;flex:none;padding:0;margin:0;border:0;background:transparent;display:flex;align-items:center;justify-content:center;color:#241c36;opacity:.5;transition:transform .12s ease,opacity .12s ease}
.plan-stop-remove::after{display:none;border:0}
.plan-stop-remove:active{transform:scale(.92);opacity:.85}
.plan-row{display:flex;align-items:center;justify-content:space-between;margin:10px 12px 0;padding:12px 14px;background:#fff;border-radius:16px;font-size:15px;color:#241c36}
.plan-checks{display:flex;align-items:center;gap:14px}
.plan-check{display:flex;align-items:center;gap:7px;min-height:32px;font-size:14px;color:#241c36}
.check-box{width:18px;height:18px;border-radius:5px;border:1.5px solid #d6cfe8;background:#fff;position:relative}
.check-box.on{background:#6a5ae0;border-color:#6a5ae0}
.check-box.on::after{content:'';position:absolute;left:5px;top:1px;width:5px;height:9px;border:2px solid #fff;border-top:0;border-left:0;transform:rotate(45deg)}
.plan-picker{font-size:15px;color:#241c36;padding:4px 0 4px 12px}
.plan-warning{margin:10px 12px 0;padding:10px 12px;border-radius:14px;background:#fff0f2;color:#a43c50;font-size:12px;line-height:1.6}
.plan-loading{min-height:260px;display:flex;align-items:center;justify-content:center;color:#8b8495;font-size:14px}
.thumb-frame{display:inline-flex!important;align-self:flex-start!important;width:auto!important;max-width:100%!important;margin-bottom:8px!important;transform:translateY(6px);box-sizing:border-box}
.thumb-strip{width:334px!important;max-width:100%!important;height:62px!important;white-space:nowrap!important;overflow-x:auto!important}
.thumb-frame .thumb{display:inline-flex!important;flex-direction:column!important;width:62px!important;height:62px!important;margin-right:6px!important;vertical-align:top!important}
.intro-glass{position:relative;margin-top:18px!important;padding:18px 4px 10px!important;background:transparent!important;transform:translateY(2px)}
.intro-glass::before{content:"";position:absolute;left:-18px;right:-18px;top:-26px;bottom:-110px;z-index:-1;pointer-events:none;background:linear-gradient(180deg,rgba(20,17,30,0) 0%,rgba(20,17,30,.20) 28%,rgba(20,17,30,.46) 60%,rgba(12,10,20,.70) 100%);-webkit-backdrop-filter:blur(22px);backdrop-filter:blur(22px);-webkit-mask-image:linear-gradient(180deg,transparent 0%,#000 28%,#000 100%);mask-image:linear-gradient(180deg,transparent 0%,#000 28%,#000 100%)}
.glass-blur{top:auto!important;left:0!important;right:0!important;bottom:calc(-72px - env(safe-area-inset-bottom))!important;width:100%!important;height:52%!important;filter:blur(24px)!important;opacity:1!important;z-index:1!important;-webkit-mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.55) 30%,#000 65%,#000 100%)!important;mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.55) 30%,#000 65%,#000 100%)!important}
.intro-glass::before{display:none!important}
.thumb-frame{width:346px!important;max-width:100%!important}
.thumb-frame{align-self:center!important;margin-left:auto!important;margin-right:auto!important;transform:translateY(28px)}
.glass-blur{height:58%!important;-webkit-mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.18) 16%,rgba(0,0,0,.55) 46%,#000 72%,#000 100%)!important;mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.18) 16%,rgba(0,0,0,.55) 46%,#000 72%,#000 100%)!important}
.scenic-intro::after{content:"";position:absolute;left:0;right:0;bottom:calc(-72px - env(safe-area-inset-bottom));height:58%;z-index:1;pointer-events:none;background:linear-gradient(180deg,rgba(20,17,30,0) 0%,rgba(20,17,30,.08) 22%,rgba(20,17,30,.30) 55%,rgba(14,12,22,.58) 100%)}
.scenic-intro.expanded::after{display:none}
.intro-content.expanded{padding-top:8px!important;animation:intro-expand-in .32s cubic-bezier(.22,1,.36,1)}
@keyframes intro-expand-in{from{opacity:.35;transform:translateY(24px)}to{opacity:1;transform:none}}
.intro-content.expanded{display:flex!important;flex-direction:column!important;height:100vh!important;box-sizing:border-box!important}
.intro-content.expanded .knowledge-scroll{flex:none!important;height:calc(100vh - 250px)!important;min-height:0!important;overflow-y:scroll!important;-webkit-overflow-scrolling:touch!important}
.station-planner{padding:0 0 0;background:#fff;border-radius:26px 26px 0 0;min-height:100%;display:flex;flex-direction:column}
.sp-map{position:relative;height:min(32vh,260px);margin:0;border-radius:26px 26px 0 0;overflow:hidden;background:#e8eef1;flex:none}
.sp-map :deep(.route-map-wrapper){margin:0;position:absolute;inset:0}
.sp-map :deep(.route-dom-map){height:100%;min-height:0;border-radius:0}
.sp-map :deep(.route-map-message){position:absolute;left:2px;top:2px;margin:0;font-size:11px}
.sp-body{padding:2px 18px 12px;flex:1 0 auto;display:flex;flex-direction:column;justify-content:flex-start;overflow:visible!important}
.sp-foot{position:sticky;bottom:0;z-index:6;margin-top:auto!important;padding:4px 18px calc(74px + env(safe-area-inset-bottom))!important;background:#fff;border-top:0!important;box-shadow:none!important}
.native-scenic.planner-open{padding-bottom:0!important}
.sp-foot .sp-spots{margin-top:0}
.sp-title{display:block;font-size:24px;font-weight:700;color:#282332}
.sp-check-hint{padding-left:34px;margin-top:2px!important}
.sp-question{display:block;margin-top:18px;font-size:15px;font-weight:600;color:#3d374d}
.sp-chips{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:12px}
.sp-chips button{min-height:44px;padding:0 18px;border:1px solid #e8e2f5;border-radius:999px;background:#fff;color:#4b4459;font-size:14px}
.sp-chips button.on{border-color:#8b78e6;background:#f2edff;color:#5b4a9e;font-weight:600}
.sp-time-input{display:flex;align-items:center;justify-content:center;gap:2px;min-height:44px;padding:0 18px;border:1px solid #e8e2f5;border-radius:999px;background:#fff;box-sizing:border-box}
.sp-input{width:3ch;min-width:3ch;height:42px;padding:0;border:0;background:transparent;text-align:center;font-size:14px;color:#4b4459}
.sp-unit{font-size:14px;color:#4b4459;white-space:nowrap;line-height:1.4}
.sp-check{display:flex;align-items:center;gap:12px;margin-top:24px;margin-bottom:0;background:none;min-height:44px;text-align:left}
.sp-box{width:22px;height:22px;border:2px solid #e8e2f5;border-radius:6px;flex:none;box-sizing:border-box;background:#fff}
.sp-box.on{border-color:#6a5ae0;background:#6a5ae0;position:relative}
.sp-box.on::after{content:"";position:absolute;left:6px;top:2px;width:6px;height:11px;border:2px solid #fff;border-top:0;border-left:0;transform:rotate(45deg)}
.sp-hint{display:block;margin-top:8px;font-size:12px;line-height:1.6;color:#8b8495}
.sp-spots{margin-top:24px;border:1px solid #ece6fa;border-radius:18px;padding:16px;background:#fbf9ff}
.sp-spots-head{display:flex;align-items:center;gap:10px}
.sp-spots-title{font-size:15px;font-weight:600;color:#3d374d}
.sp-count{font-size:12px;color:#6a5ae0;background:#efe9ff;border-radius:999px;padding:3px 10px}
.sp-spot-actions{display:flex;gap:10px;margin-top:14px}
.sp-pick{flex:1;min-height:44px;border:1px solid #8b78e6;border-radius:14px;color:#5b4a9e;background:#fff;font-size:14px}
.sp-clear{min-height:44px;padding:0 16px;border:1px solid #ece6fa;border-radius:14px;color:#8b8495;background:#fff;font-size:14px}
.sp-generate{width:100%;height:50px;margin-top:24px;border-radius:16px;background:#6a5ae0;color:#fff;font-size:16px;font-weight:600}
.sp-generate.incomplete{background:#d9d3ea;color:#fff}
.sp-generate[disabled]{opacity:.6}
.sp-error{margin-top:14px;padding:12px 14px;border-radius:12px;background:#fff3f3;color:#b04848;font-size:13px;display:flex;justify-content:space-between;gap:12px}
.sp-results{margin-top:26px}
.sp-plan-summary{display:flex;justify-content:space-between;gap:8px;margin-top:18px;padding:14px 0;border-top:1px solid #f0ecf8;border-bottom:1px solid #f0ecf8}
.sp-plan-summary view{display:flex;flex-direction:column;gap:4px;font-size:12px;color:#8b8495}
.sp-fact{font-size:16px;font-weight:700;color:#282332}
.sp-stops{margin-top:8px}
.sp-stop{display:flex;align-items:center;gap:12px;padding:14px 0;border-bottom:1px solid #f4f0fb}
.sp-stop-no{width:24px;height:24px;border-radius:50%;background:#efe9ff;color:#6a5ae0;font-size:12px;display:flex;align-items:center;justify-content:center;flex:none}
.sp-stop-name{flex:1;font-size:15px;color:#282332}
.sp-stop-time{font-size:12px;color:#8b8495}
.native-scenic .station-planner .sp-check{justify-content:flex-start!important;padding:0!important;background:none!important}
.native-scenic .station-planner .sp-chips button{background:#fff!important;color:#4b4459!important;border:1px solid #e8e2f5!important;border-radius:999px!important;min-height:44px!important;padding:0 18px!important}
.native-scenic .station-planner .sp-chips button.on{background:#f2edff!important;color:#5b4a9e!important;border-color:#8b78e6!important;font-weight:600}
.native-scenic .station-planner .sp-generate{background:rgba(255,255,255,.72)!important;color:#5b4a9e!important;border:1px solid #8b78e6!important;border-radius:16px!important;width:100%!important;height:50px!important;font-size:16px!important;font-weight:600!important;margin:18px 0 0!important;box-shadow:0 6px 18px rgba(106,90,224,.12)!important;-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px)}
.native-scenic .station-planner .sp-pick{background:#fff!important;color:#5b4a9e!important;border:1px solid #8b78e6!important;border-radius:14px!important;min-height:44px!important;flex:1}
.native-scenic .station-planner .sp-clear{background:#fff!important;color:#8b8495!important;border:1px solid #ece6fa!important;border-radius:14px!important;min-height:44px!important;padding:0 16px!important}
.scenic-nav{position:relative;border-bottom:0!important;box-shadow:none!important}
.scenic-nav.nav-planner::after{content:"";position:absolute;left:12px;right:12px;top:100%;height:10px;border-left:1px solid #d9cdf8;border-right:1px solid #d9cdf8;border-top:1px solid #d9cdf8;border-radius:12px 12px 0 0;pointer-events:none}
.nav-center-title{position:absolute;left:50%;bottom:0;height:44px;line-height:44px;transform:translateX(-50%);font-size:17px;font-weight:600;color:#282332;white-space:nowrap;pointer-events:none}
.nav-placeholder{width:44px;height:44px;visibility:hidden}
.native-scenic .plan-scroll{background:#fff!important;border-radius:0!important;overflow:hidden!important;margin:0!important;width:100%!important}
.native-scenic .station-planner .sp-gates{flex-wrap:nowrap!important;gap:6px!important}
.native-scenic .station-planner .sp-gates button{flex:1 1 0!important;min-width:0!important;padding:0 6px!important;font-size:13px!important;white-space:nowrap!important}
.scenic-nav.nav-planner::after{display:none!important}
.native-scenic .station-planner .sp-spots{border:0!important;background:transparent!important;border-radius:0!important;padding:0!important;margin-top:8px!important}
.native-scenic .station-planner .sp-spots-head{padding:0!important}
.sp-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:18px}
.sp-row .sp-question{margin:0}
.sp-select{display:flex;align-items:center;justify-content:space-between;gap:2px;min-width:136px;min-height:44px;padding:0 12px;border:1px solid #e8e2f5;border-radius:14px;background:#fff;color:#4b4459;font-size:14px;box-sizing:border-box}
.sp-select.open{border-color:#8b78e6;box-shadow:0 0 0 2px #efe9ff}
.sp-select-input{width:3.6ch;min-width:3.6ch;height:40px;padding:0;border:0;background:transparent;text-align:right;font-size:14px;color:#4b4459}
.sp-select-unit{font-size:13px;color:#7a718c}
.sp-caret{font-size:14px;color:#8b7fa8;transition:transform .18s;line-height:1;transform:rotate(90deg)}
.sp-caret.up{transform:rotate(-90deg)}
.sp-dropdown{margin-top:8px;padding:8px;border:1px solid #eee8f8;border-radius:16px;background:#fff;display:flex;flex-wrap:wrap;gap:8px;box-shadow:0 8px 24px rgba(70,50,130,.10)}
.sp-dropdown button{flex:1 1 calc(50% - 8px);min-height:42px;padding:0 10px;border:1px solid #f0ebfa;border-radius:12px;background:#faf8ff;color:#4b4459;font-size:14px}
.sp-dropdown button.on{border-color:#8b78e6;background:#f2edff;color:#5b4a9e;font-weight:600}
.sp-fields{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px;margin-top:18px;align-items:end}
.sp-field{min-width:0;display:flex;flex-direction:column;gap:8px;position:relative;height:100%;justify-content:flex-end}
.sp-field .sp-dropdown{position:absolute;top:calc(100% + 6px);left:0;right:0;z-index:80;margin-top:0}
.sp-field-label{font-size:14px;font-weight:600;color:#3d374d;line-height:1.4;min-height:20px;display:flex;align-items:flex-end}
.sp-field .sp-select{width:100%;min-width:0;justify-content:space-between}
.sp-gate-value{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sp-field .sp-dropdown-inline{flex-direction:column;gap:6px}
.sp-field .sp-dropdown-inline button{flex:none;width:100%;min-height:40px;font-size:13px;padding:0 8px}
.sp-spot-chips{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:6px 0 0}
.sp-spot-chips button{min-height:42px;width:100%;min-width:0;padding:0 5px;border:1px solid #e8e2f5;border-radius:12px;background:#fff;color:#4b4459;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sp-spot-chips button.on{border-color:#8b78e6;background:#f2edff;color:#5b4a9e;font-weight:600}
.nav-start{min-height:44px!important;height:44px!important;border:1px solid #d9cdf8!important;border-radius:999px!important;color:#5b4a9e!important;padding:0 16px!important;background:#fff!important}
.nav-start .iconfont{color:#5b4a9e!important}
.scenic-nav{height:62px!important;padding-left:14px!important;padding-right:14px!important;padding-top:0!important;padding-bottom:0!important;box-sizing:border-box!important;display:flex!important;align-items:center!important;justify-content:space-between!important}
.scenic-nav .app-back-btn{position:static!important;transform:none!important;margin:0!important;flex:none!important}
.nav-page-title{position:absolute!important;left:50%!important;top:50%!important;transform:translate(-50%,-50%)!important;font-size:19px!important;font-weight:600!important;color:#2a2438!important;letter-spacing:.02em!important;pointer-events:none!important;white-space:nowrap!important}
.nav-center-title{display:none!important}
.native-scenic{box-sizing:border-box!important}
.scenic-nav{padding-top:0!important}
.native-scenic .sp-check:active{transform:none!important}
.native-scenic .sp-check .sp-box{width:22px!important;height:22px!important;flex:none!important}
.sp-step-warn{display:block;margin-top:8px;padding:10px 12px;border:1px solid #f0dfc8;border-radius:12px;background:#fffaf2;color:#9a6b35;font-size:12px;line-height:1.6}
.planner-error-mask{position:fixed;inset:0;z-index:1200;display:flex;align-items:center;justify-content:center;padding:32px;background:rgba(24,18,38,.28);-webkit-backdrop-filter:blur(2px);backdrop-filter:blur(2px)}
.planner-error-card{width:100%;max-width:264px;padding:18px 18px 16px;border-radius:20px;background:#fff;box-shadow:0 18px 46px rgba(40,25,90,.20);display:flex;flex-direction:column;gap:10px}
.pe-title{font-size:17px;font-weight:600;color:#282332}
.pe-msg{font-size:13px;line-height:1.7;color:#6f687d}
.pe-retry{width:100%;min-height:44px;border-radius:14px;border:1px solid #8b78e6;background:#fff;color:#5b4a9e;font-size:15px;font-weight:600;margin-top:2px}
.sp-field .sp-select{width:auto!important;min-width:118px!important;max-width:158px!important;align-self:flex-start!important;justify-content:space-between!important}
.sp-body{padding-left:20px!important;padding-right:20px!important}
.sp-fields{gap:20px!important}
.native-scenic .sp-body{padding-left:16px!important;padding-right:16px!important}
.native-scenic .sp-fields{gap:16px!important;margin:18px 0 0!important;padding:0!important;width:100%!important}
.native-scenic .sp-field{width:100%!important;min-width:0!important}
.native-scenic .sp-field .sp-select{width:100%!important;min-width:0!important;max-width:none!important;align-self:stretch!important}
.native-scenic .sp-field .sp-select{justify-content:flex-start!important}
.native-scenic .sp-field .sp-select-input{width:3.2ch!important;min-width:3.2ch!important;text-align:left!important}
.native-scenic .sp-field .sp-select-unit{margin-left:0!important}
.native-scenic .sp-field .sp-select .sp-caret{margin-left:auto!important}

.planner-skeleton{background:#fff;min-height:100%;padding-bottom:120px;box-sizing:border-box}
.ps-map{height:200px;border-radius:26px 26px 0 0}
.ps-pad{padding:20px 18px}
.ps-row{display:flex;gap:16px}
.ps-field{flex:1;min-width:0}
.ps-line{height:14px;border-radius:7px;margin-bottom:12px}
.ps-input{height:44px;border-radius:14px}
.ps-check{display:flex;align-items:center;gap:12px;margin-top:28px}
.ps-box{width:22px;height:22px;border-radius:6px;flex:none}
.ps-tip{height:12px;width:62%;margin-top:14px;border-radius:6px}
.catalog-skeleton{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;padding:14px}
.catalog-sk-card{height:124px;border-radius:16px}
.sk-block{position:relative;overflow:hidden;background:#f1edf9}
.sk-block::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.75),transparent);transform:translateX(-100%);animation:sk-shimmer 1.25s ease-in-out infinite}
@keyframes sk-shimmer{to{transform:translateX(100%)}}
@media (prefers-reduced-motion: reduce){.sk-block::after{animation:none}}
.plan-stop{position:relative!important}
.plan-drag-handle{flex:none;font-size:17px;line-height:1;color:#b7accd;letter-spacing:-2px;margin-left:2px}
.plan-stop.dragging{background:#fff!important;box-shadow:0 10px 24px rgba(70,50,130,.18)!important;border-radius:12px!important}
.plan-stop.drag-target{box-shadow:none!important;background:#faf8ff!important}

.sp-filter{width:100%;white-space:nowrap}
.sp-filter-inner{display:inline-flex;align-items:center;gap:8px;padding:14px 0 2px}
.sp-filter-btn{flex:none;display:inline-flex;align-items:center;justify-content:center;height:34px;padding:0 14px;border-radius:999px;border:1px solid #e8e2f5;background:#fff;color:#4b4459;font-size:13px;box-sizing:border-box;white-space:nowrap}
.sp-filter-btn.on{background:#fff;border-color:#8b78e6;border-width:1.5px;color:#5b4a9e;font-weight:600;box-shadow:0 4px 12px rgba(106,90,224,.10)}
.sp-panel{margin-top:14px;padding:16px;background:#fff;border:1px solid #f0ebf9;border-radius:18px;box-shadow:0 10px 30px -26px rgba(70,50,130,.4)}
.sp-field-label{display:block;font-size:14px;font-weight:600;color:#3d374d;margin-bottom:10px}
.sp-interest{display:flex;flex-wrap:wrap;gap:8px}
.sp-interest button{min-height:38px;padding:0 14px;border-radius:999px;border:1px solid #e8e2f5;background:#fff;color:#4b4459;font-size:13px}
.sp-interest button.on{background:#f2edff;border-color:#8b78e6;color:#5b4a9e;font-weight:600}

.sp-select-time{width:76px;min-width:0;padding:0 8px;gap:0;justify-content:space-between}
.sp-select-time .sp-select-input{width:2.4ch;min-width:2.4ch;text-align:center;font-size:13px}
.sp-select-time .sp-select-unit{font-size:11px;white-space:nowrap}
.sp-select-time .sp-caret{font-size:10px;margin-left:2px;flex:none}
.catalog-scroll{overflow-anchor:none!important;overscroll-behavior:contain!important;-webkit-overflow-scrolling:touch!important;scroll-behavior:auto!important}
.catalog-card{contain:layout paint!important;transform:translateZ(0)}

.native-scenic .sp-filter-btn{display:inline-flex!important;align-items:center!important;justify-content:center!important;flex:none!important;height:34px!important;min-height:34px!important;padding:0 14px!important;margin:0!important;border-radius:999px!important;border:1px solid #e8e2f5!important;background:#fff!important;color:#4b4459!important;font-size:13px!important;line-height:1!important;box-sizing:border-box!important;white-space:nowrap!important;box-shadow:none!important}
.native-scenic .sp-filter-btn.on{border:1.5px solid #8b78e6!important;color:#5b4a9e!important;background:#fff!important;font-weight:600!important;box-shadow:0 4px 12px rgba(106,90,224,.10)!important}
.native-scenic .sp-filter-btn:active{transform:none!important}
.native-scenic .sp-filter-btn::after{border:0!important}
.intro-content.expanded{background:none!important;-webkit-backdrop-filter:none!important;backdrop-filter:none!important;border-radius:0!important;isolation:isolate}
.intro-content.expanded::before{content:"";position:absolute;left:calc(50% - 50vw);right:calc(50% - 50vw);top:0;bottom:calc(-96px - env(safe-area-inset-bottom));z-index:-1;pointer-events:none;background:linear-gradient(180deg,rgba(28,24,38,0) 0%,rgba(28,24,38,.18) 24%,rgba(26,22,36,.50) 58%,rgba(16,14,24,.72) 100%);-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px);-webkit-mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.15) 10%,rgba(0,0,0,.62) 30%,#000 56%,#000 100%);mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.15) 10%,rgba(0,0,0,.62) 30%,#000 56%,#000 100%)}
.intro-content.expanded .intro-glass{background:none!important;box-shadow:none!important;border:0!important}
.intro-content.expanded::before{-webkit-backdrop-filter:none!important;backdrop-filter:none!important;background:linear-gradient(180deg,rgba(28,24,38,0) 0%,rgba(28,24,38,.10) 20%,rgba(26,22,36,.42) 52%,rgba(16,14,24,.70) 100%)!important}
.glass-blur{display:block!important;top:0!important;left:0!important;right:0!important;bottom:0!important;width:100%!important;height:100%!important;filter:blur(30px)!important;opacity:.92!important;z-index:1!important;-webkit-mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.18) 16%,rgba(0,0,0,.62) 40%,#000 66%,#000 100%)!important;mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.18) 16%,rgba(0,0,0,.62) 40%,#000 66%,#000 100%)!important}
.intro-bottom-blur{display:none!important}

.sp-time-row{width:100%;white-space:nowrap}
.sp-time-row-inner{display:inline-flex;align-items:center;gap:6px;padding:2px 0}
.sp-time-chip{flex:none;height:38px;padding:0 12px;border-radius:999px;border:1px solid #e8e2f5;background:#fff;color:#4b4459;font-size:13px;box-sizing:border-box}
.sp-time-chip.on{border:1.5px solid #8b78e6;color:#5b4a9e;font-weight:600;background:#fff}
.sp-time-custom{flex:none;display:inline-flex;align-items:center;gap:1px;height:38px;padding:0 10px;border-radius:999px;border:1px solid #e8e2f5;background:#fff;color:#4b4459;font-size:13px;box-sizing:border-box}
.sp-time-custom.on{border:1.5px solid #8b78e6}
.sp-time-custom .sp-time-input{width:4.4ch;min-width:4.4ch;height:36px;padding:0;border:0;background:transparent;font-size:13px;text-align:center;color:#4b4459}
.sp-time-ph{font-size:12px;color:#9b93ab}
.sp-time-custom .sp-time-unit{font-size:12px;color:#4b4459;white-space:nowrap}
.native-scenic .sp-time-chip{display:inline-flex!important;align-items:center!important;justify-content:center!important;flex:none!important;height:38px!important;min-height:38px!important;padding:0 12px!important;margin:0!important;border-radius:999px!important;border:1px solid #e8e2f5!important;background:#fff!important;color:#4b4459!important;font-size:13px!important;line-height:1!important;box-sizing:border-box!important;white-space:nowrap!important;box-shadow:none!important}
.native-scenic .sp-time-chip.on{border:1.5px solid #8b78e6!important;color:#5b4a9e!important;background:#fff!important;font-weight:600!important}
.native-scenic .sp-time-chip::after{border:0!important}
.scenic-intro:not(.expanded) .glass-blur{top:auto!important;bottom:calc(-72px - env(safe-area-inset-bottom))!important;height:52%!important;-webkit-mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.25) 22%,rgba(0,0,0,.70) 55%,#000 80%,#000 100%)!important;mask-image:linear-gradient(180deg,transparent 0%,rgba(0,0,0,.25) 22%,rgba(0,0,0,.70) 55%,#000 80%,#000 100%)!important}

.sp-gate-row{display:flex;align-items:center;gap:8px;flex-wrap:nowrap;white-space:nowrap}
.sp-gate-chip{flex:none;display:inline-flex;align-items:center;justify-content:center;height:38px;padding:0 12px;border-radius:999px;border:1px solid #e8e2f5;background:#fff;color:#4b4459;font-size:13px;box-sizing:border-box;white-space:nowrap}
.sp-gate-chip.on{border:1.5px solid #8b78e6;color:#5b4a9e;font-weight:600;background:#fff}
.native-scenic .sp-gate-chip{display:inline-flex!important;align-items:center!important;justify-content:center!important;flex:none!important;height:38px!important;min-height:38px!important;padding:0 12px!important;margin:0!important;border-radius:999px!important;border:1px solid #e8e2f5!important;background:#fff!important;color:#4b4459!important;font-size:13px!important;line-height:1!important;box-sizing:border-box!important;white-space:nowrap!important;box-shadow:none!important}
.native-scenic .sp-gate-chip.on{border:1.5px solid #8b78e6!important;color:#5b4a9e!important;background:#fff!important;font-weight:600!important}
.native-scenic .sp-gate-chip::after{border:0!important}
.native-scenic.expanded{padding-bottom:calc(72px + env(safe-area-inset-bottom))!important}
.intro-content.expanded{animation:intro-sheet-up .34s cubic-bezier(.22,1,.36,1)!important}
@keyframes intro-sheet-up{from{opacity:.55;transform:translateY(56px)}to{opacity:1;transform:none}}
.sp-section{margin:14px 18px 0;padding:14px 14px 12px;border:1px solid #f0ebfa;border-radius:18px;background:#fff}
.sp-section-title{display:block;font-size:16px;font-weight:600;color:#282332;margin-bottom:10px}
.sp-section-toggle{display:flex!important;align-items:center;gap:8px;width:100%;min-height:40px;background:none!important;border:0!important;padding:0!important;text-align:left}
.sp-section-toggle>text:first-child{font-size:16px;font-weight:600;color:#282332}
.sp-section-summary{margin-left:auto;font-size:12px;color:#8b8495;font-weight:400}
.sp-section-body{padding-top:8px}
.sp-section .sp-field-label{display:block;margin:10px 0 6px;font-size:13px;font-weight:500;color:#5b5568}
.sp-segment{display:flex;gap:8px;margin-bottom:10px}
.sp-segment button{flex:1;min-height:38px;border:1px solid #e8e2f5;border-radius:12px;background:#fff;color:#5b5568;font-size:13px}
.sp-segment button.on{border-color:#8b78e6;background:#f2edff;color:#5b4a9e;font-weight:600}
.sp-extra-display{width:100%;min-height:110px;margin-top:8px;padding:12px 14px;border:1px solid #e8e2f5;border-radius:16px;background:#fff;box-sizing:border-box;display:flex;align-items:flex-start}
.sp-extra-input{width:100%;height:44px;font-size:14px;color:#3d374d}
.extra-editor-layer{position:fixed;left:0;right:0;top:0;bottom:0;z-index:3000;pointer-events:none}
.extra-editor-ghost{position:fixed;box-sizing:border-box;background:#fff;border:1px solid #e8e2f5;border-radius:16px;padding:12px 14px;font-size:14px;line-height:1.6;color:#3d374d}
.native-scenic .sp-filter{padding:0 18px!important;box-sizing:border-box!important;width:100%!important}
.native-scenic .sp-filter-inner{display:flex!important;justify-content:space-between!important;width:100%!important;padding:14px 0 2px!important;gap:6px!important}
.native-scenic .sp-filter-btn{flex:0 1 auto!important;padding:0 10px!important;font-size:12.5px!important}
.native-scenic .sp-body{overflow-y:auto!important;padding-bottom:calc(96px + env(safe-area-inset-bottom))!important}
.native-scenic .sp-foot{padding-left:34px!important;padding-right:34px!important}
.native-scenic .sp-time-row-inner{gap:5px!important}
.native-scenic .sp-time-chip{padding:0 10px!important;font-size:12px!important}
.native-scenic .sp-time-custom{min-width:78px!important;padding:0 8px!important;height:36px!important}
.native-scenic .sp-time-custom .sp-time-input{width:5ch!important;min-width:5ch!important;text-align:left!important}
.native-scenic .sp-foot{margin-top:0!important;padding-top:0!important}
.native-scenic .sp-section:last-of-type{margin-bottom:10px!important}
.native-scenic .sp-spot-chips{gap:6px!important}
.native-scenic .sp-spot-chips button{min-height:36px!important;font-size:12px!important}
.sp-filter-btn.on{background:#fff!important;border-color:#8b78e6!important;color:#5b4a9e!important}
.sp-time-chip.on,.sp-gate-chip.on{background:#fff!important;border-color:#8b78e6!important;color:#5b4a9e!important}
.sp-interest button.on{background:#fff!important;border-color:#8b78e6!important;color:#5b4a9e!important}
.sp-spot-chips button.on{background:#fff!important;border-color:#8b78e6!important;color:#5b4a9e!important}
.sp-segment button.on{background:#fff!important;border-color:#8b78e6!important;color:#5b4a9e!important}
.native-scenic .sp-time-custom{min-width:64px!important;max-width:80px!important;padding:0 6px!important;flex:none!important;margin-right:4px}
.native-scenic .sp-time-custom .sp-time-input{width:4ch!important;min-width:4ch!important;text-align:center!important}
.native-scenic .sp-time-custom .sp-time-unit{font-size:11px!important}

.native-scenic .sp-time-custom .sp-time-input{width:5.2ch!important;min-width:5.2ch!important;font-size:12px!important}
.native-scenic .sp-time-custom .sp-time-unit{font-size:11px!important;flex:none!important}

.sp-section{margin:12px 18px 0!important;padding:12px 14px!important}
.sp-section-title{text-align:center!important}
.sp-section-toggle{justify-content:center!important;min-height:28px!important}
.sp-section-toggle .sp-caret{margin-left:2px}
.sp-section-body{padding-top:4px!important}
.sp-section .sp-field-label{margin:8px 0 6px!important}
.sp-extra{min-height:72px!important;margin-top:6px!important}
.sp-spots-head{justify-content:center!important}
.native-scenic .sp-filter-inner{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:8px!important;width:100%!important;padding:14px 0 2px!important}
.native-scenic .sp-filter-btn{width:100%!important;min-width:0!important;padding:0 4px!important;box-sizing:border-box!important;justify-content:center!important;border-width:1px!important;font-size:12.5px!important}
.native-scenic .sp-filter-btn.on{border-width:1px!important;box-shadow:inset 0 0 0 1px #8b78e6,0 4px 12px rgba(106,90,224,.10)!important}
.native-scenic .sp-section-title{min-height:24px!important;margin-bottom:10px!important;display:flex!important;align-items:center!important}
.native-scenic .sp-section-title+.sp-field-label{margin-top:0!important}
.native-scenic .sp-section .sp-field-label{margin-top:12px!important}
.native-scenic .sp-section-title{justify-content:center!important;text-align:center!important}
.native-scenic .sp-section-toggle{justify-content:center!important}
.native-scenic .sp-extra{height:92px!important;min-height:92px!important;max-height:92px!important;margin-top:6px!important}
.native-scenic .sp-spots-head{justify-content:center!important;width:100%!important}
.native-scenic .sp-section-body{padding-top:0!important}
.native-scenic .sp-field-label{min-height:20px!important;line-height:20px!important}
.native-scenic .sp-segment{display:flex!important;gap:16px!important;margin-bottom:10px!important}
.native-scenic .sp-segment button{flex:none!important;min-height:34px!important;padding:0 2px!important;background:none!important;border:0!important;border-radius:0!important;color:#6f687d!important;font-size:14px!important;position:relative!important}
.native-scenic .sp-segment button.on{color:#5b4a9e!important;font-weight:600!important}
.native-scenic .sp-segment button.on::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;border-radius:2px;background:#6a5ae0}
.native-scenic .sp-guide-grid{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px!important}
.native-scenic .sp-guide-card{display:flex!important;flex-direction:column;align-items:center;gap:8px;min-height:190px;padding:12px!important;border:1px solid #e8e2f5!important;border-radius:14px!important;background:#fff!important}
.native-scenic .sp-guide-card.on{border-color:#8b78e6!important;box-shadow:0 6px 18px rgba(106,90,224,.12)!important}
.native-scenic .sp-guide-card image{width:112px;height:150px;object-fit:contain}
.native-scenic .sp-guide-card text{font-size:13px;color:#4b4459}
.native-scenic .sp-filter-inner{grid-template-columns:repeat(5,minmax(0,1fr))!important;gap:4px!important}
.native-scenic .sp-filter-btn{font-size:13px!important;padding:0 2px!important}
.sp-time-row-inner{padding:2px 10px 2px 0!important}
.native-scenic .sp-time-custom{min-width:72px!important;max-width:none!important;padding:0 10px!important;margin-right:0!important;box-sizing:border-box!important}
.native-scenic .sp-time-custom .sp-time-input{width:4.6ch!important;min-width:4.6ch!important}
.native-scenic .sp-extra{height:110px!important;min-height:110px!important;max-height:110px!important}
.native-scenic .sp-time-row-inner{gap:4px!important;padding-right:0!important}
.native-scenic .sp-time-chip{padding:0 8px!important;font-size:12px!important}
.native-scenic .sp-time-custom{min-width:0!important;max-width:none!important;gap:0!important;padding:0 6px!important;height:36px!important;margin:0!important;box-sizing:border-box!important}
.native-scenic .sp-time-custom .sp-time-input{width:3.4ch!important;min-width:3.4ch!important;text-align:right!important;font-size:12px!important}
.native-scenic .sp-time-custom .sp-time-unit{font-size:11px!important;color:#6b6478!important;margin-left:1px!important}
.native-scenic{position:fixed!important;left:0!important;right:0!important;top:0!important;bottom:0!important}
.native-scenic .sp-time-custom{min-width:82px!important;max-width:none!important;padding:0 8px!important;gap:2px!important}
.native-scenic .sp-time-custom .sp-time-input{width:5ch!important;min-width:5ch!important;text-align:center!important}
.plan-stop.ghosted{opacity:0!important;pointer-events:none!important}
/* 长按把手后跟手的悬浮条：固定定位，既不被滚动窗口裁剪，也不占据列表排版。 */
.plan-stop.plan-stop-floating{position:fixed!important;top:0;left:0;margin:0!important;border-bottom:0!important;border-radius:12px!important;background:#fff!important;box-shadow:0 16px 34px rgba(70,50,130,.26)!important;pointer-events:none!important;z-index:70!important;overflow:hidden;will-change:transform}
.plan-stop.plan-stop-floating .plan-stop-grip{opacity:.9;background:#f3efff}
.plan-drag-ghost{opacity:1!important;pointer-events:none!important;display:flex!important;align-items:center!important;gap:10px!important}
.sp-segment{position:relative!important;padding-bottom:8px!important;align-items:flex-end!important}
.sp-segment-underline{position:absolute!important;left:0;bottom:0;height:3px;border-radius:2px;background:#6a5ae0;transition:left .42s cubic-bezier(.34,1.56,.64,1),width .42s cubic-bezier(.34,1.56,.64,1);z-index:2;pointer-events:none}
.native-scenic .sp-segment button.on::after{display:none!important}
.native-scenic .sp-segment button{padding-bottom:2px!important}
.native-scenic .sp-segment{display:grid!important;grid-template-columns:1fr 1fr!important;gap:0!important;position:relative!important;padding-bottom:8px!important;align-items:end!important}
.native-scenic .sp-segment button{justify-content:center!important;text-align:center!important;padding-bottom:2px!important}
.sp-segment-underline{position:absolute!important;left:0!important;bottom:0!important;height:3px!important;width:50%!important;border-radius:2px!important;background:#6a5ae0!important;transition:transform .42s cubic-bezier(.34,1.56,.64,1)!important;z-index:2!important;pointer-events:none!important}
.sp-segment-underline.right{transform:translateX(100%)!important}
.sp-spots-head{justify-content:flex-start!important;width:100%!important}
.native-scenic .sp-spots-head{justify-content:flex-start!important;width:100%!important}
.native-scenic .sp-segment button{font-size:14px!important}
.sp-spots-title{font-size:14px!important;font-weight:600!important}
.native-scenic .sp-segment{padding-bottom:3px!important}
.sp-segment-underline{width:52px!important;left:25%!important;transform:translateX(-50%)!important;height:2.5px!important;background:#b9a9ee!important;bottom:0!important;transition:left .42s cubic-bezier(.34,1.56,.64,1)!important}
.sp-segment-underline.right{left:75%!important;transform:translateX(-50%)!important}
.sp-segment-underline{width:54px!important;left:25%!important;transform:translateX(-50%)!important;bottom:2px!important;height:2.5px!important;background:#b9a9ee!important;transition:left .42s cubic-bezier(.34,1.56,.64,1)!important}
.sp-segment-underline.right{left:75%!important;transform:translateX(-50%)!important}
.native-scenic .sp-segment{padding-bottom:4px!important}
.sp-segment-divider{height:0;border-top:1px solid #f0ebfa;margin:10px 0 12px}
.native-scenic .plan-stop{padding-top:12px!important;padding-bottom:12px!important}
.native-scenic .plan-row{margin-bottom:8px!important}
/* 展开后的景点介绍：文字底下做毛玻璃，背景稍微模糊 */
.native-scenic .intro-content.expanded{-webkit-backdrop-filter:blur(12px) saturate(1.05)!important;backdrop-filter:blur(12px) saturate(1.05)!important}
/* 景点图鉴列表滑动不要弹簧回弹；景点详情的弹性展开保持原样 */
.native-scenic,.catalog-scroll,.catalog-scroll .uni-scroll-view{overscroll-behavior:none!important;-webkit-overflow-scrolling:auto}
/* 景点详情：更明显的玻璃边缘反光；景点名字居中 */
.native-scenic .intro-content.expanded{border-radius:26px 26px 0 0!important;overflow:hidden!important;box-shadow:inset 0 1px 0 rgba(255,255,255,.55),inset 0 0 0 1px rgba(255,255,255,.18)!important}
.native-scenic .intro-content.expanded::after{content:"";position:absolute;left:0;right:0;top:0;height:1.5px;background:linear-gradient(90deg,rgba(255,255,255,0) 0%,rgba(255,255,255,.9) 35%,rgba(255,255,255,.9) 65%,rgba(255,255,255,0) 100%);pointer-events:none;z-index:6}
.native-scenic .intro-content.expanded .intro-heading{text-align:center!important}
.native-scenic .intro-content.expanded .spot-title{text-align:center!important;display:block!important;width:100%!important}
.native-scenic .intro-content{bottom:16px!important;padding-bottom:8px!important}
.native-scenic .thumb-frame{margin-bottom:8px!important;transform:translateY(0)!important}
.native-scenic .intro-glass{margin-top:8px!important;padding-top:6px!important;padding-bottom:4px!important}
.native-scenic .spot-title{font-size:28px!important;line-height:1.28!important}
.native-scenic .intro-dots{margin-top:8px!important}
</style>