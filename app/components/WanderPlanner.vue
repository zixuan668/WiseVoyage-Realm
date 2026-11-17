<template>
  <view class="wander-planner" :class="['stage-'+stage, motionClass]" :style="motionStyle">
    <view class="wander-header">
      <button class="wander-square wander-back app-back-btn" role="button" :aria-label="t('返回')" @tap="back() || $emit('exit')">
        <view class="app-back-icon wander-back-arrow" aria-hidden="true"></view>
      </button>
      <text class="wander-title">{{ t(title) }}</text>
      <button v-if="arranging" class="wander-loading-cancel" @tap="cancel">{{ t('取消') }}</button>
      <view v-if="mode==='time' && stage==='recommended'" class="wander-tools">
        <button class="wander-square" role="button" :aria-label="t('加入路线')"  @tap="adding=true"><WanderIcon name="plus" /></button>
      </view>
    </view>

    <view class="wander-sheet">
    <scroll-view :key="routeMapStage ? 'route-map' : stage" :scroll-top="scrollTop" @scroll="trackScroll"
      :show-scrollbar="false" class="wander-scroll" :scroll-y="!mapInteracting">
      <view class="wander-content">
        <view v-if="routeMapStage && map.points.length" class="wander-map-frame">
          <RouteRoadMap :key="stage + ':' + mode" class="wander-road" :data="map" :marker-labels="markerLabels"
            :steps="showMapSteps ? mapSteps : []" :compact="stage==='preview'" :blind="mode==='blind'"
            wander @interacting="mapInteracting=$event" />
          <button v-if="stage==='recommended'" class="wander-layer" :aria-pressed="showSteps" @tap="showSteps=!showSteps"><WanderIcon name="layers" />{{ t('台阶图层') }}</button>
          <view v-else-if="showMapSteps" class="wander-map-key"><view></view>{{ t('已标注台阶') }}</view>
        </view>
        <template v-if="stage==='explore'">
          <text class="wander-section-title style-heading">{{ t('这次想怎么逛？') }}</text>
          <button v-for="option in walkingStyles" :key="option.value" class="wander-link style-choice" :aria-pressed="walkStyle===option.value" @tap="pickWalkStyle(option.value)">
            <view class="wander-symbol"><WanderIcon :name="option.icon" /></view><text>{{ t(option.label) }}</text>
            <WanderIcon :name="walkStyle===option.value?'check':'next'" />
          </button>
        </template>

        <template v-else-if="stage==='featured'">
          <button v-for="route in routes" :key="route.route_id" class="wander-feature" @tap="chooseFeatured(route)">
            <image v-if="route.cover_image && !failed[route.cover_image]" :src="imageUrl(route.cover_image)" mode="aspectFill" @error="failed[route.cover_image]=true" />
            <view class="wander-feature-shade"></view>
            <view class="wander-feature-copy"><text>{{ t(route.name) }}</text><text>{{ (route.spot_ids||[]).length }} {{ t('站') }}<template v-if="route.estimated_time_minutes"> · {{ route.estimated_time_minutes }} {{ t('分钟') }}</template></text></view>
            <WanderIcon name="next" />
          </button>
          <text v-if="loading || !routes.length" class="wander-notice" role="status">{{ t(loading?'正在加载…':catalogError||'暂无主题路线') }}</text>
          <button v-if="catalogError && !loading" class="wander-secondary" @tap="$emit('reload')">{{ t('重试') }}</button>
        </template>

        <template v-else-if="stage==='featuredDetail'">
          <view class="wander-card">
            <text v-if="featured.description" class="wander-description">{{ t(featured.description) }}</text>
            <view v-for="(id,index) in featured.spot_ids" :key="id" class="wander-row">
              <text class="wander-number">{{ index+1 }}</text><text>{{ spotName(id) }}</text>
            </view>
          </view>
        </template>

        <template v-else-if="stage==='time'">
          <view class="wander-time-stage">
            <view class="wander-intro"><view class="wander-intro-symbol"><WanderIcon name="leaf" /></view><text>{{ t('给自己留一点随意') }}</text></view>
            <view class="wander-times">
              <button v-for="option in durations" :key="option.value" :id="'wander-time-'+option.value" :aria-pressed="budget===option.value" @tap="budget=option.value">
                <WanderIcon name="walk" />{{ t(option.label) }}
              </button>
            </view>
          </view>
        </template>

        <template v-else-if="stage==='settings' || stage==='preview'">
          <template v-if="stage==='preview'">
            <view class="wander-card wander-total">
              <view class="wander-section-title"><WanderIcon name="flag" />{{ t(mode==='featured'?featured?.name:recommendationName) }}</view>
              <view class="wander-distance">{{ walkingDistance(overview.walking_meters,t) }}</view>
              <text class="wander-metrics">{{ ids.length }} {{ t('站') }}</text>
              <text v-if="stepLegs.length" class="wander-notice">{{ stepLegs.length }} {{ t('段含台阶') }} · {{ walkingDistance(stepMeters,t) }}</text>
              <view v-if="mode==='blind'" class="wander-blind-summary"><WanderIcon name="gift" />{{ t('盲盒景点') }}<template v-if="exit"> → {{ areas[exit].label }}</template></view>
            </view>
          </template>
          <view class="wander-card">
            <view class="wander-section-title"><WanderIcon name="people" />{{ t('同行人数') }}</view>
            <view class="wander-row"><text>{{ t('人数') }}</text><view class="wander-stepper">
              <button class="wander-square" role="button" :aria-label="t('减少人数')" :disabled="party===1" @tap="party--"><WanderIcon name="minus" /></button>
              <text class="wander-count">{{ party }}</text>
              <button class="wander-square" role="button" :aria-label="t('增加人数')" :disabled="party===20" @tap="party++"><WanderIcon name="plus" /></button>
            </view></view>
            <view class="wander-pills">
              <button :aria-pressed="senior"  @tap="updateCondition('senior',!senior)">{{ t('有老人') }}</button>
              <button :aria-pressed="child"  @tap="updateCondition('child',!child)">{{ t('有儿童') }}</button>
            </view>
            <picker :range="areas" range-key="label" :value="entry"  @change="updateCondition('entry',Number($event.detail.value))">
              <view class="wander-row wander-picker"><WanderIcon name="pin" /><text>{{ t('出发入口') }}</text><text>{{ areas[entry].label }}</text><WanderIcon name="next" /></view>
            </picker>
            <picker :range="areas" range-key="label" :value="exit"  @change="updateCondition('exit',Number($event.detail.value))">
              <view class="wander-row wander-picker"><WanderIcon name="arrow" /><text>{{ t('离园出口') }}</text><text>{{ areas[exit].label }}</text><WanderIcon name="next" /></view>
            </picker>
          </view>
        </template>

        <template v-else-if="stage==='recommended'">
          <view class="wander-card wander-recommendation">
            <text v-if="mode==='blind'" class="wander-note">{{ t('选一个去处') }}</text>
            <view v-else class="wander-section-title"><WanderIcon name="heart" />{{ t(selectedStyle.label) }}</view>
            <text class="wander-metrics">{{ areas[entry].label }} · {{ t(durations.find(option=>option.value===budget)?.label) }}</text>
            <view class="candidate-list">
              <button v-for="(candidate,index) in candidates" :key="candidate.ids.join('-')" :id="'wander-candidate-'+index" class="candidate-option"
                :aria-pressed="candidateIndex===index" @tap="openCandidate(index)">
                <view class="wander-symbol"><WanderIcon :name="candidate.icon" /></view>
                <view><text>{{ t(candidate.name) }}<template v-if="mode!=='blind'"> {{ index+1 }}</template></text><text v-if="candidate.reason">{{ t(candidate.reason) }}</text></view>
                <WanderIcon :name="candidateIndex===index?'check':'next'" />
              </button>
            </view>
            <text v-if="candidates.length<2" class="wander-note">{{ t('当前条件下仅找到一条可走路线') }}</text>
            <button v-if="mode==='blind'" class="wander-inline" @tap="shuffleCandidates"><WanderIcon name="spark" />{{ t('换一批') }}</button>
            <text class="wander-route-name">{{ t(mode==='blind'?'确认本次游览路线':recommendationName) }}</text>
            <text v-if="mode!=='blind'" class="wander-metrics">{{ ids.map(id=>spotName(id)).join(' · ') }}</text>
            <view v-else class="wander-blind-summary"><WanderIcon name="gift" />{{ ids.length }} {{ t('站') }}<template v-if="exit"> → {{ areas[exit].label }}</template></view>
            <text class="wander-metrics">{{ walkingDistance(overview.walking_meters,t) }}</text>
            <text v-if="stepLegs.length" class="wander-notice">{{ t('含台阶') }} {{ walkingDistance(stepMeters,t) }}</text>
          </view>
        </template>

        <text v-if="error" class="wander-notice wander-error" role="alert">{{ t(error) }}</text>
      </view>
    </scroll-view>

    <view v-if="['featuredDetail','explore','time','settings','recommended','preview'].includes(stage)" class="wander-footer">
      <text v-if="['recommended','preview'].includes(stage) && routeWarning" class="wander-notice">{{ t(routeWarning) }}</text>
      <button v-if="stage==='featuredDetail'" class="wander-primary" @tap="useFeatured">{{ t('选择此路线') }}</button>
      <button v-if="stage==='explore'" class="wander-primary" :disabled="!walkStyle" @tap="go('time')">{{ t('选择游览时长') }}</button>
      <button v-if="stage==='time'" class="wander-primary" :disabled="arranging" @tap="viewRoute">{{ t(arranging?'正在规划…':'查看路线') }}</button>
      <button v-if="stage==='settings'" class="wander-primary" :disabled="arranging" @tap="generate()"><WanderIcon name="route" />{{ t(arranging?'正在安排…':'继续安排') }}</button>
      <view v-if="stage==='recommended'" class="wander-footer-row">
        <button class="wander-secondary" @tap="back">{{ t(mode==='blind'?'重新选择':'去修改') }}</button>
        <button class="wander-primary" :disabled="!overview.complete || overBudget" @tap="openCandidate(candidateIndex)">{{ t(mode==='blind'?'确认本次路线':'选这条路线') }}</button>
      </view>
      <view v-if="stage==='preview'" class="wander-footer-row">
        <button class="wander-secondary wander-steps-toggle" :aria-pressed="avoidSteps" :disabled="senior || child || walkStyle==='accessible'" @tap="updateCondition('fewSteps',!fewSteps)">{{ t('避开台阶') }}</button>
        <button class="wander-primary" :disabled="!overview.complete || overBudget" @tap="start">{{ t('开始游览') }}</button>
      </view>
    </view>
    </view>
    <view v-if="wanderToast" class="wander-toast" role="status">{{ wanderToast }}</view>
    <PageDock :active="0" />
    <view v-if="adding" class="wander-modal" @tap="adding=false">
      <view class="wander-modal-card" @tap.stop>
        <view class="wander-section-title"><text>{{ t('加入路线') }}</text><button class="wander-square" role="button" :aria-label="t('关闭')" @tap="adding=false"><WanderIcon name="close" /></button></view>
        <scroll-view scroll-y class="wander-modal-scroll">
          <button v-for="spot in addableSpots" :key="spot.spot_id" class="wander-inline" @tap="addStop(spot.spot_id)"><WanderIcon name="plus" />{{ t(spot.spot_name) }}</button>
          <text v-if="!addableSpots.length" class="wander-note">{{ t('暂无可添加的景点') }}</text>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script>
import WanderIcon from './WanderIcon.vue'
import PageDock from './PageDock.vue'
import RouteRoadMap from './RouteRoadMap.vue'
import { assetUrl } from '../common/config.js'
import { STEP_LINES } from '../common/park-home-data.js'
import { previewOptions, roadMap, routeMapLabels, routeRequest } from '../common/route-planning.js'
import { blindPreviewMap, routeLegs, walkingDistance } from '../common/wander.js'

const durations = [{ value: 30, label: '半小时' }, { value: 60, label: '1 小时' }, { value: 120, label: '2 小时' }]
const walkingStyles = [
  {value:'nature',label:'沿湖看水',icon:'cloud',preference:'nature',tags:/临湖|湖岸|湖景|水岸|湖面|昆明湖|湖中岛岸/},
  {value:'ascent',label:'登高看全景',icon:'compass',preference:'photography',tags:/山地|万寿山中轴|登高|高处俯瞰|前山礼仪/},
  {value:'history',label:'看古建',icon:'book',preference:'history',tags:/古建|殿|石桥|传统建筑|宫廷|古迹|戏楼|阁楼/},
  {value:'family',label:'亲子轻松',icon:'people',preference:'family',tags:/亲子|儿童|科普|互动|一起|观察|辨认|比较|认识/},
  {value:'accessible',label:'省力无障碍',icon:'walk',preference:'comprehensive'},
  {value:'blind',label:'随机盲盒',icon:'gift',preference:'comprehensive'},
]
const blindTags = [
  { label:'临湖', icon:'cloud', style:walkingStyles[0], reason:'沿途可以看湖景。' },
  { label:'山地', icon:'compass', style:walkingStyles[1], reason:'沿途有登高看景的路段。' },
  { label:'古建', icon:'book', style:walkingStyles[2], reason:'沿途可以看园林古建。' },
  { label:'亲子', icon:'people', style:walkingStyles[3], reason:'适合和孩子一起观察园林里的细节。' },
  { label:'摄影点', icon:'camera', style:{preference:'photography',tags:/摄影|拍照|构图|倒影|取景/}, reason:'沿途有适合取景的景点。' },
  { label:'无障碍', icon:'walk', reason:'这条路线避开了路网已标注的台阶。' },
]
const gatePoints=[null,[39.9966755,116.2755965],[40.0009937,116.268051],[39.9896694,116.2738739]]
const areas = [{ value: 'auto', label: '不指定' }, { value: 'east', label: '东宫门' }, { value: 'north', label: '北宫门' }, { value: 'south', label: '新建宫门' }]

function matchesStyle(spot, style) {
  if (!spot || !style.tags) return false
  const profile = spot.preference_profile
  return style.tags.test([spot.tags, profile?.reasons?.[style.preference], profile?.reasons?.history].join(' '))
}

export default {
  components: { WanderIcon, RouteRoadMap, PageDock },
  props: { routes: Array, spots: Array, loading: Boolean, catalogError: String },
  emits: ['begin', 'plan', 'exit', 'reload', 'theme-selected'],
  data() {
    return { stage: 'explore', durations, walkingStyles, walkStyle:'', failed: {}, featured: null, featuredFromHome: false, mode: 'time',
      budget: 60, party: 1, senior: false, child: false, fewSteps: false, entry: 1, exit: 0,
      error: '', overview: null, ids: [], returnStage: '',
      recommendationName:'推荐路线', candidates:[], candidateIndex:0, adding: false, arranging: false, saved: false,
      showSteps:false, mapInteracting:false, scrollTop:0, motionClass:'', motionStyle:{}, wanderToast:'' }
  },
  computed: {
    title() {
      return { featured: '主题路线', featuredDetail: this.featured?.name, explore: '随心逛', time:'游览时长', settings: '行程规划', loading: '', recommended: this.mode==='blind'?'盲盒路线预览':'推荐路线',
        preview: '路线结果' }[this.stage]
    },
    routeMapStage() { return this.stage==='preview' || (this.stage==='recommended' && this.mode!=='blind') },
    areas() { return areas.map(area => ({ ...area, label: this.t(area.label) })) },
    selectedStyle() { return walkingStyles.find(option=>option.value===this.walkStyle) || walkingStyles[0] },
    avoidSteps() { return this.senior || this.child || this.fewSteps || (this.mode!=='featured' && this.walkStyle==='accessible') },
    addableSpots() { return this.spots.filter(spot=>!this.ids.includes(spot.spot_id)) },
    map() {
      const map=roadMap(this.overview)
      return this.mode==='blind' ? blindPreviewMap(map,this.overview) : map
    },
    mapSteps() { return STEP_LINES.map(line=>line.path) },
    showMapSteps() { return this.stage==='recommended' ? this.showSteps : this.stepLegs.length>0 },
    markerLabels() {
      const blind = this.mode === 'blind'
      return routeMapLabels(this.overview, this.t, { hideSpotNames: true, hideExit: blind })
    },
    stepLegs() { return routeLegs(this.overview).filter(leg => leg.has_steps) },
    stepMeters() { return this.stepLegs.reduce((sum,leg) => sum+(leg.steps_meters||0),0) },
    overBudget() { return this.mode!=='featured' && this.overview?.total_minutes > this.budget },
    routeWarning() {
      if (!this.overview?.complete) return '部分路段无法确认可步行路径，请返回重新选择路线。'
      if (this.overBudget) return '路线预计超过所选时长，请调整后再确认。'
      if (this.stepLegs.length && this.stage==='recommended') return '路线含台阶，可选择少台阶方案。'
      return ''
    },
    planning() {
      return { preferences: [this.mode==='featured'?'comprehensive':this.selectedStyle.preference],
        time_budget_minutes: this.mode==='featured' ? Math.min(480, Math.max(15, Math.ceil(this.overview?.total_minutes || 120))) : this.budget,
        city: '北京', pace: this.avoidSteps?'relaxed':'standard', start_area: areas[this.entry].value,
        end_area: areas[this.exit].value, avoid_steps: this.avoidSteps }
    },
  },
  watch: {
    // 任何条件变化都让「已存入」失效，需要重新存入
    budget() { this.saved = false },
    walkStyle() { this.saved = false },
    senior() { this.saved = false },
    child() { this.saved = false },
    fewSteps() { this.saved = false },
    entry() { this.saved = false },
    exit() { this.saved = false },
  },
  beforeUnmount() { this.abort(); clearTimeout(this._toastTimer) },
  methods: {
    walkingDistance, imageUrl: assetUrl,
    spotName(id) { return this.t(this.spots.find(s => s.spot_id===id)?.spot_name || '景点') },
    trackScroll(event) { this._scrollPosition = event.detail.scrollTop },
    showWanderToast(text) {
      this.wanderToast = text
      clearTimeout(this._toastTimer)
      this._toastTimer = setTimeout(() => { this.wanderToast = '' }, 2200)
    },
    go(stage) {
      const from=this.stage
      const currentScroll=this._scrollPosition || 0
      this.scrollTop=currentScroll
      this.motionClass=['recommended','preview'].includes(stage) && from!==stage && this._cardOrigin ? 'is-card-expanding' : ''
      this.motionStyle=this.motionClass==='is-card-expanding' ? this._cardOrigin : {}
      this.error=''; this.mapInteracting=false; this.stage=stage
      if (from!==stage && currentScroll!==0) this.$nextTick(() => {
        if (this.stage===stage) this.scrollTop=0
      })
    },
    cardOrigin(selector, next) {
      const query=uni.createSelectorQuery().in(this)
      query.select('.wander-planner').boundingClientRect()
      query.select(selector).boundingClientRect()
      query.exec(([screen, card]) => {
        if (!screen?.width || !screen.height || !card || card.bottom<=screen.top || card.top>=screen.bottom) {
          this._cardOrigin={'--route-card-top':'43%','--route-card-bottom':'43%','--route-card-left':'6%','--route-card-right':'6%'}
        } else {
          const inset=value=>Math.max(0,Math.round(value))+'px'
          this._cardOrigin={'--route-card-top':inset(card.top-screen.top),'--route-card-bottom':inset(screen.bottom-card.bottom),
            '--route-card-left':inset(card.left-screen.left),'--route-card-right':inset(screen.right-card.right)}
        }
        next()
      })
    },
    back() {
      if (this.adding) { this.adding=false; return true }
      if (['explore','featured'].includes(this.stage)) return false
      if (this.stage==='featuredDetail' && this.featuredFromHome) return false
      if (this.arranging) { this.cancel(); return true }
      this.go({featuredDetail:'featured',time:'explore',settings:'featuredDetail',recommended:'time',
        preview:this.mode==='featured'?'settings':'recommended'}[this.stage])
      return true
    },
    openHomeThemes(route) {
      this.featuredFromHome=true
      if (route) this.chooseFeatured(route)
      else this.go('featured')
    },
    chooseFeatured(route) {
      this.mode='featured'
      this.featured=route
      this.go('featuredDetail')
      if (this.featuredFromHome) this.$emit('theme-selected', route.route_id)
    },
    useFeatured() { this.mode='featured'; this.go('settings') },
    chooseTime(value) {
      this.mode=this.walkStyle==='blind'?'blind':'time'
      this.budget=value
      return this.generate([],true)
    },
    pickWalkStyle(value) {
      if (!value) return
      // 重复点击同一项保持选中，不再取消
      this.walkStyle = value
    },
    chooseTimeCard() {
      const value=this.budget
      this.cardOrigin('#wander-time-'+value,()=>{
        if (this.stage==='time' && this.budget===value) this.chooseTime(value)
      })
    },
    viewRoute() {
      if (this.arranging) return
      this.generate([], false, true).then(result => {
        if (!result || !this.ids.length) return
        const areas=['auto','east','north','south'], plan=this.planning||{}
        const handoff={ids:this.ids.slice(),planning:{...plan},senior:this.senior,child:this.child}
        try { uni.setStorageSync('wander-last-handoff', handoff) } catch (_) {}
        const url='/pages/scenic/scenic?view=plan&spotIds='+this.ids.join(',')
          +'&elderly='+(this.senior?'1':'0')+'&children='+(this.child?'1':'0')
          +'&avoidSteps='+(plan.avoid_steps?'1':'0')
          +'&startArea='+(areas.includes(plan.start_area)?plan.start_area:'auto')
          +'&endArea='+(areas.includes(plan.end_area)?plan.end_area:'auto')
        uni.navigateTo({url,fail:()=>uni.showToast({title:this.t('打开路线失败，请重试'),icon:'none'})})
      })
    },
    locationEntry() {
      return new Promise(resolve=>{
        const finish=entry=>{ clearTimeout(timeout); resolve(entry) }
        const timeout=setTimeout(()=>finish(null),5000)
        try {
          uni.getLocation({ type:'wgs84', isHighAccuracy:true, highAccuracyExpireTime:4500,
            success:({latitude,longitude})=>{
              if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
                latitude<39.980 || latitude>40.008 || longitude<116.244 || longitude>116.284) {
                finish(null)
                return
              }
              const distance=gate=>Math.hypot((gate[1]-longitude)*.77,gate[0]-latitude)
              const nearest=gatePoints.slice(1).reduce((best,gate)=>distance(gate)<distance(best)?gate:best)
              finish(gatePoints.indexOf(nearest))
            }, fail:()=>finish(null),
          })
        } catch { finish(null) }
      })
    },
    abort() { this._version=(this._version||0)+1; this._request?.abort(); this._request=null },
    cancel() { this.abort(); this.arranging=false; this.go(this.returnStage) },
    async request(path, options, version) {
      if (version!==this._version) return null
      const task=this._request=routeRequest(path,options,0,20000)
      const result=await task.promise
      return version===this._version ? result : null
    },
    async arrange(work, next) {
      this.returnStage=this.stage
      this.abort()
      const version=this._version
      // 不再切到「正在安排你的路线」整屏；当前页面保持，仅按钮显示安排中
      this.arranging=true
      try {
        const result=await work(version)
        if (version!==this._version) return
        if (next!==this.stage) this.go(next)
        return result
      } catch(error) {
        if (version!==this._version) return
        this.go(this.returnStage)
        this.error=error.message
      } finally {
        if (version===this._version) this.arranging=false
      }
    },
    async buildPreview(ids, version) {
      if (version!==this._version) return
      if (!Array.isArray(ids) || ids.length<1 || ids.length>20 || new Set(ids).size!==ids.length ||
        ids.some(id=>!this.spots.some(spot=>spot.spot_id===id))) throw new Error('所选景点不可用，请重新选择')
      const overview=await this.request('/tour-experience/route-preview',previewOptions(ids,this.planning),version)
      if (!overview) return
      this.ids=ids.slice()
      this.overview=overview
      if (this.mode!=='featured' && this.candidates[this.candidateIndex]) {
        const candidate=this.candidates[this.candidateIndex]
        this.candidates[this.candidateIndex]={...candidate,ids:this.ids.slice(),overview}
      }
      return true
    },
    selectCandidate(index) {
      const candidate=this.candidates[index]
      if(!candidate)return
      this.candidateIndex=index
      this.ids=candidate.ids.slice()
      this.overview=candidate.overview
      this.recommendationName=candidate.name
    },
    openCandidate(index) {
      if (this.stage!=='recommended' || !this.candidates[index]) return
      this.selectCandidate(index)
      if (!this.overview.complete || this.overBudget) return
      this.cardOrigin('#wander-candidate-'+index,()=>{
        if (this.stage==='recommended' && this.candidateIndex===index) this.go('preview')
      })
    },
    shuffleCandidates() {
      return this.generate(this.candidates.map(candidate=>candidate.ids[0]))
    },
    blindCandidate(overview, candidates) {
      const legs=routeLegs(overview)
      const stops=overview.stops.map(stop=>this.spots.find(spot=>spot.spot_id===stop.spot_id) || stop)
      const matches=blindTags.map(tag=>({tag,count:tag.style ? stops.filter(spot=>matchesStyle(spot,tag.style)).length
        : Number(legs.length>0 && legs.every(leg=>leg.has_steps===false))}))
        .filter(match=>match.count>0).sort((a,b)=>b.count-a.count)
      const chosen=matches.find(({tag})=>!candidates.some(candidate=>candidate.name===tag.label)) || matches[0]
      if (!chosen) return { name:'园林步道', icon:'route' }
      return { name:chosen.tag.label, icon:chosen.tag.icon, reason:chosen.tag.reason }
    },
    candidateReason(result,overview) {
      const time={minutes:overview.total_minutes}
      if(this.avoidSteps && !routeLegs(overview).some(leg=>leg.has_steps) && this.walkStyle==='accessible') {
        return this.t('路线避开路网已标注的台阶，预计游览 {minutes} 分钟。',time)
      }
      const style=this.selectedStyle
      const details=(result.score_details || []).filter(item=>item.reason)
      const spotFor=detail=>this.spots.find(item=>item.spot_id===detail.spot_id)
      const detail=details.find(item=>matchesStyle(spotFor(item),style)) || details[0]
      const spot=detail && spotFor(detail)
      const evidence=(spot?.preference_profile?.reasons?.[style.preference] || detail?.reason)?.split(/[；。]/)[0]
      if(evidence && spot) {
        return this.t('经过{spot}，看点是{feature}。',{spot:this.spotName(spot.spot_id),feature:this.t(evidence)})
      }
      return this.t('预计游览 {minutes} 分钟，适合这次的时长。',time)
    },
    generate(skip=[], locate=false, quiet=false) {
      if(this.mode==='featured')return this.arrange(version=>this.buildPreview(this.featured.spot_ids,version),'preview')
      return this.arrange(async version=>{
        if (locate) {
          const entry=await this.locationEntry()
          if (version!==this._version) return
          if (entry!==null) this.entry=entry
        }
        const excluded=new Set(skip), candidates=[], signatures=new Set()
        const style=this.selectedStyle
        const tagged=this.spots.filter(spot=>matchesStyle(spot,style))
        const taggedIds=new Set(tagged.map(spot=>spot.spot_id))
        let focused=taggedIds.size>0 && taggedIds.size<this.spots.length
        const outsideStyle=focused ? this.spots.filter(spot=>!taggedIds.has(spot.spot_id)).map(spot=>spot.spot_id) : []
        for(let attempt=0;attempt<6 && candidates.length<3;attempt++){
          let result
          const excludedIds=focused ? new Set([...excluded,...outsideStyle]) : excluded
          try{result=await this.request('/tour-routes/recommend',{...this.planning,excluded_spot_ids:[...excludedIds].slice(0,100)},version)}
          catch(err){if(candidates.length)break;throw err}
          if(version!==this._version)return
          const ids=result?.spot_ids
          const nextExclude=ids?.find(id=>!excludedIds.has(id))
          if(nextExclude==null){
            if(focused && candidates.length<2){focused=false;continue}
            break
          }
          excluded.add(nextExclude)
          const signature=ids.slice().sort().join(',')
          if(signatures.has(signature))continue
          const overview=await this.request('/tour-experience/route-preview',previewOptions(ids,this.planning),version)
          if(version!==this._version)return
          if(!overview?.complete || !(overview.total_minutes<=this.budget))continue
          signatures.add(signature)
          const card=this.mode==='blind' ? this.blindCandidate(overview,candidates)
            : {name:result.name||style.label,icon:'route',reason:this.candidateReason(result,overview)}
          candidates.push({ids,overview,...card})
        }
        if(!candidates.length)throw new Error('暂无符合时长和通行条件的路线')
        this.candidates=candidates
        this.selectCandidate(0)
        return true
      },this.stage).then(result=>{
        if (result) {
          const handoff = { ids:this.ids.slice(), planning:{...this.planning}, senior:this.senior, child:this.child }
          try { uni.setStorageSync('wander-last-handoff', handoff) } catch (_) {}
          this.saved = true
          if (!quiet) this.showWanderToast(this.t('已存入，可在首页「路径规划」查看'))
        }
        return result
      })
    },
    async updateCondition(key,value) {
      const previous=this[key]
      this[key]=value
      if(this.stage==='settings') {
        return
      }
      const stage=this.stage, ids=this.ids.slice()
      const updated=await this.arrange(version=>this.buildPreview(ids,version),stage)
      if(!updated)this[key]=previous
    },
    addStop(id) {
      this.adding=false
      const ids=this.ids
      if(ids.length>=20){this.error='路线最多支持20站，请先精简行程';return}
      if(ids.includes(id))return
      return this.arrange(version=>this.buildPreview([...ids,id],version),this.stage)
    },
    start() {
      if(!this.overview?.complete || this.overBudget)return
      this.$emit('begin',{ids:this.ids.slice(),planning:{...this.planning},overview:this.overview,
        party:this.party,senior:this.senior,child:this.child,blind:this.mode==='blind'})
    },
  },
}
</script>

<style scoped>
.wander-planner {
  position:fixed; top:0; left:0; width:100%; height:100vh; height:100dvh; z-index:12;
  box-sizing:border-box; display:flex; flex-direction:column; min-height:0;
  color:#292c43; background:#fff; padding-top:var(--status-bar-height, 0px); overflow:hidden;
}
.wander-header, .wander-content, .wander-footer { width:100%; max-width:540px; margin:0 auto; box-sizing:border-box; padding-inline:20px; }
.wander-header { position:relative; min-height:64px; display:flex; align-items:center; padding-block:8px; flex:none; }
/* 返回箭头在左，标题居中——返回键旁边不再跟页面名字 */
.wander-title { position:absolute; left:50%; transform:translateX(-50%); max-width:calc(100% - 140px);
  text-align:center; font-size:20px; line-height:1.4; text-wrap:balance; pointer-events:none; }
.wander-header > .wander-square, .wander-tools { position:relative; z-index:1; }
.wander-sheet { flex:1; min-height:0; display:flex; flex-direction:column; width:100%; max-width:540px; margin:0 auto; box-sizing:border-box; background:linear-gradient(151deg,#efedf9 2%,#f7f5fb 94%); border-radius:24px 24px 0 0; overflow:hidden; }
/* 上面白色、下面浅紫，内容区顶部两角圆角 */
.wander-sheet .wander-scroll { flex:1; height:0; min-height:0; }
.wander-scroll { flex:1; height:0; min-height:0; }
.wander-content { display:grid; gap:13px; padding-block:8px 24px; }
.wander-feature image, .wander-feature-shade { position:absolute; inset:0; width:100%; height:100%; }
.wander-feature-shade { background:linear-gradient(0deg,#1c2032db,transparent 88%); }
.wander-planner button { margin:0; line-height:1.45; font-weight:400; box-sizing:border-box; min-height:44px; color:inherit; }
.wander-planner button::after { border:none; }
.wander-planner button:active:not([disabled]) { transform:scale(.96); }
.wander-planner button:focus-visible { outline:2px solid #6550ae; outline-offset:2px; }
.wander-planner button[disabled] { opacity:.46; }
.wander-planner .wander-link, .wander-planner .wander-feature { display:flex; align-items:center; width:100%; text-align:left; gap:14px; padding:12px; border-radius:20px; background:#fff; }
.wander-link > text { flex:1; font-size:17px; }
.wander-link > .wander-icon { color:#716694; margin-right:3px; }
.wander-symbol, .wander-square, .wander-loading-icon { display:grid; place-items:center; background:#ebe4f9; color:#634ba6 !important; border-radius:12px; width:44px; height:44px; flex:none; }
.wander-planner .wander-square { padding:0; }
.wander-planner .wander-feature { min-height:124px; position:relative; isolation:isolate; overflow:hidden; align-items:flex-end; color:#fff; background:#4e4867; padding:16px; }
.wander-feature-copy { position:relative; display:grid; gap:4px; flex:1; font-size:18px; }
.wander-feature-copy text+text { font-size:14px; }
.wander-feature > .wander-icon { z-index:1; }
.wander-section-title { display:flex; gap:8px; align-items:center; font-size:17px; }
.wander-section-title .wander-icon { color:#634ba6; }
.wander-times { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
.wander-times button { padding:12px 4px; min-height:67px; background:#fff; border-radius:16px; font-size:16px; }
.wander-planner .wander-blind { margin-top:12px; }
.wander-card { padding:14px; border-radius:20px; background:#fff; }
.wander-description, .wander-metrics, .wander-notice { display:block; font-size:14px; line-height:1.65; }
.wander-description, .wander-metrics { color:#56516b; margin-block:5px; }
.wander-metrics, .wander-count, .wander-number { font-variant-numeric:tabular-nums; }
.wander-row { display:flex; align-items:center; justify-content:space-between; gap:8px; min-height:48px; font-size:15px; }
.wander-row + .wander-row, picker + picker { border-top:1px solid #efebf5; }
.wander-row .wander-number { display:grid; place-items:center; background:#ece7f8; color:#634ba6; border-radius:50%; width:28px; height:28px; flex:none; }
.wander-row .wander-number + text { flex:1; }
.wander-stepper, .wander-pills { display:flex; align-items:center; gap:6px; }
.wander-count { min-width:28px; text-align:center; }
.wander-pills { flex-wrap:wrap; margin-block:6px; }
.wander-pills button { padding:4px 12px; font-size:14px; border-radius:13px; background:#f4f1f8; }
.wander-pills button[aria-pressed="true"] { background:#e6dcfa; color:#563b99; box-shadow:inset 0 0 0 1px #b8a2df; }
.wander-picker text:nth-last-child(2) { margin-left:auto; color:#645880; }
.wander-picker .wander-icon { color:#716694; }
.wander-road { margin:0; }
.wander-road :deep(.route-dom-map) { height:clamp(254px,39vh,380px); min-height:0; border-radius:18px; }
.stage-preview .wander-road :deep(.route-dom-map) { height:clamp(152px,22vh,195px); border-radius:18px; }
.wander-notice { color:#6e5236; }
.wander-error { color:#963a53; }
.wander-footer { margin-top:auto; padding-top:8px; padding-bottom:8px; flex:none; }
.wander-planner .wander-primary, .wander-planner .wander-secondary {
  width:100%; padding:9px 14px; border-radius:16px; display:flex; justify-content:center; align-items:center; gap:8px; font-size:16px;
}
.wander-planner .wander-primary { color:#fff; background:#6952b3; min-height:50px; }
.wander-planner .wander-secondary { color:#58448b; background:#eae3f6; }
.wander-loading { min-height:52vh; display:grid; justify-items:center; align-content:center; gap:20px; font-size:20px; }

.wander-progress { background:#e5ddf6; width:112px; height:4px; border-radius:4px; overflow:hidden; }
.wander-progress view { width:34%; height:100%; color:#755db7; background:currentColor; animation:wander-progress 1.25s ease-in-out infinite alternate; }
@keyframes wander-progress { to {transform:translateX(194%)} }
.wander-tools, .wander-footer-row { display:flex; align-items:center; gap:8px; }
.wander-tools { margin-left:auto; }
.wander-tools .wander-square, .wander-header > .wander-square { background:#faf8ff; }
.wander-header > .wander-square { margin-left:-8px; }
/* 左上角返回：统一为 App 的白底紫边圆形返回键（外观由全局 .app-back-btn 控制） */
.wander-header > .wander-square.wander-back { margin-left:-8px; }
.wander-header > .wander-square.wander-back::before { display:none !important; }
.wander-header .wander-back-arrow { width:20px; height:20px; background-color:#282332; }
.stage-featured, .stage-featuredDetail { background:#fff; }
.stage-featuredDetail .wander-header > .wander-square:not(.wander-back) {
  position:relative; isolation:isolate; background:transparent;
}
.stage-featuredDetail .wander-header > .wander-square:not(.wander-back)::before {
  position:absolute; inset:6px; z-index:-1; content:''; border-radius:10px; background:#f2edf8;
}
.stage-featuredDetail .wander-card { border:1px solid #eee8f4; }
.wander-footer-row .wander-primary { flex:1.6; }
/* 游览时长页：左「存入导览路线」+ 右「返回首页」，宽度 4:1 */
.wander-time-actions { display:flex; align-items:stretch; gap:10px; width:100%; }
.wander-time-actions .wander-primary { flex:4 1 0%; min-width:0; }
.wander-time-actions .wander-home { flex:1 1 0%; min-width:0; padding:0 4px; font-size:14px; white-space:nowrap; }
.wander-footer-row .wander-secondary { flex:1; min-width:0; }
.wander-footer-row button { min-height:50px; padding-inline:6px; white-space:normal; text-wrap:balance; }
.wander-planner .wander-steps-toggle { flex:1.05; }
.wander-steps-toggle[aria-pressed="true"] { background:#ddd2f2; color:#50388e; }
.wander-footer > .wander-notice { margin:0 0 8px; }
.wander-intro { display:grid; justify-items:center; gap:18px; padding:36px 0 66px; font-size:22px; }
.wander-intro-symbol { display:grid; place-items:center; background:#e6def6; color:#7659bb; border-radius:28px; width:94px; height:94px; }
.wander-intro-symbol .wander-icon { width:38px; height:38px; }
.wander-times button { display:grid; justify-items:start; gap:9px; align-content:center; min-height:90px; text-align:left; padding:12px; border-radius:21px; }
.wander-times button .wander-icon { color:#7659bb; }
.wander-times button[aria-pressed="true"] { background:#745cc0; color:white; }
.wander-times button[aria-pressed="true"] .wander-icon { color:inherit; }
.wander-link { min-height:72px; }
.wander-link.blind-choice { margin-top:14px; }
.wander-link.blind-choice + .blind-choice { margin-top:36px; }
.wander-note { display:block; font-size:15px; color:#645d78; margin-block:10px 0; }
.wander-recommendation { display:grid; gap:5px; }
.wander-route-name { display:block; margin-top:5px; font-size:21px; }
.wander-total .wander-distance { font-size:26px; margin-top:6px; font-variant-numeric:tabular-nums; }
.wander-blind-summary { display:flex; gap:9px; align-items:center; margin-top:4px; font-size:15px; }
.wander-planner .wander-inline { display:flex; align-items:center; gap:8px; padding:4px 2px; color:#496a9f; font-size:15px; background:transparent; text-align:left; }
.wander-map-frame { position:relative; min-width:0; }
.stage-preview .wander-map-frame { border-radius:18px; overflow:hidden; box-shadow:0 0 0 1px #e4e6dd; }
.wander-planner.is-card-expanding { animation:wander-card-expand 290ms cubic-bezier(.2,.75,.25,1) both; }
@keyframes wander-card-expand {
  from { clip-path:inset(var(--route-card-top) var(--route-card-right) var(--route-card-bottom) var(--route-card-left) round 16px); }
  to { clip-path:inset(0 round 0); }
}
.wander-planner .wander-layer, .wander-map-key { position:absolute; z-index:1; right:10px; background:#fff; padding:6px 10px; border-radius:12px; color:#4e4564; font-size:13px; display:flex; align-items:center; gap:6px; }
.wander-planner .wander-layer { top:10px; }
.wander-layer[aria-pressed="true"] { background:#e8ddf8; }
.wander-map-key { top:10px; }
.wander-map-key view { width:17px; border-top:2px dashed #b84758; }
.wander-header { background:#fff; }
.wander-loading-cancel { position:absolute; right:20px; top:50%; transform:translateY(-50%); display:flex; align-items:center; justify-content:center; width:auto; height:34px; min-height:34px; line-height:1; padding:0 16px; border-radius:17px; background:#f0ecfa; color:#5d4b96; font-size:14px; font-weight:500; }
.stage-loading { background:#fff; }
.wander-loading-pair { display:flex; padding:10px 0 14px; }
.wander-loading-pair > view { display:grid; place-items:center; background:#f6f6ffba; color:#65729a; border-radius:26px; width:95px; height:95px; transform:rotate(-12deg); }
.wander-loading-pair > view+view { margin-left:-13px; background:#fafaff; transform:translateY(12px) rotate(9deg); }
/* 两张卡片交替上下浮动 */
.wander-loading-pair > view:first-child { animation:wander-card-up 1.8s ease-in-out infinite; }
.wander-loading-pair > view+view { animation:wander-card-down 1.8s ease-in-out infinite; }
@keyframes wander-card-up { 0%,100% { transform:rotate(-12deg) translateY(0); } 50% { transform:rotate(-9deg) translateY(-10px); } }
@keyframes wander-card-down { 0%,100% { transform:translateY(12px) rotate(9deg); } 50% { transform:translateY(2px) rotate(6deg); } }
.wander-loading-pair .wander-icon { width:38px; height:38px; }
.wander-planner .wander-cancel { width:auto; min-width:116px; margin:0 auto; border-radius:24px; background:#f7f7ff; }
.wander-modal { position:absolute; inset:0; z-index:15; background:#29223f55; display:flex; align-items:flex-end; justify-content:center; }
.wander-modal-card { width:100%; max-width:540px; max-height:75%; padding:18px 18px calc(14px + env(safe-area-inset-bottom)); box-sizing:border-box; background:#fff; border-radius:24px 24px 0 0; display:flex; flex-direction:column; }
.wander-modal-card .wander-section-title { justify-content:space-between; }
.wander-modal-scroll { height:min(46vh,400px); }
.wander-modal-scroll button { width:100%; }
.style-heading { margin:6px 0; }
/* 随心逛风格卡：选中态 = 紫色描边 + 白玻璃 */
.wander-planner .style-choice { min-height:76px; padding:14px 16px; border-radius:24px; background:#fff;
  box-shadow:inset 0 0 0 1rpx rgba(130,110,210,.10), 0 14rpx 28rpx -30rpx rgba(64,44,120,.5);
  transition:background .18s ease, box-shadow .18s ease, transform .12s ease; }
.wander-planner .style-choice:active { transform:scale(.985); }
.wander-planner .style-choice .wander-symbol { width:46px; height:46px; border-radius:14px; background:#f2edff; color:#6547ad !important;
  transition:background .18s ease, color .18s ease; }
.wander-planner .style-choice > text { font-size:17px; color:#282332; transition:color .18s ease; }
.wander-planner .style-choice > .wander-icon { color:#c3bad6; margin-right:2px; transition:color .18s ease; }
.wander-planner .style-choice[aria-pressed="true"] {
  background:rgba(255,255,255,.64);
  -webkit-backdrop-filter:blur(18px) saturate(1.12);
  backdrop-filter:blur(18px) saturate(1.12);
  box-shadow:inset 0 0 0 2rpx #6a5ae0, inset 0 1rpx 0 rgba(255,255,255,.85), 0 18rpx 34rpx -30rpx rgba(64,44,120,.5); }
.wander-planner .style-choice[aria-pressed="true"] .wander-symbol {
  background:rgba(255,255,255,.9); color:#5b49c9 !important;
  box-shadow:inset 0 0 0 1rpx rgba(106,90,224,.32); }
.wander-planner .style-choice[aria-pressed="true"] > text { color:#4a3a86; font-weight:600; }
.wander-planner .style-choice[aria-pressed="true"] > .wander-icon { color:#6a5ae0; }
.candidate-list { display:grid; gap:6px; margin-bottom:4px; }
.wander-planner .candidate-option { display:flex; align-items:center; gap:10px; padding:9px; width:100%; background:#f5f1fa; border-radius:15px; text-align:left; }
.wander-planner .candidate-option[aria-pressed="true"] { background:linear-gradient(135deg,#f2ebff 0%,#eaf1ff 100%);
  box-shadow:inset 0 0 0 1rpx rgba(106,90,224,.18); }
.wander-planner .candidate-option[aria-pressed="true"] .wander-symbol { background:#6a5ae0; color:#fff !important; }
.wander-planner .candidate-option[aria-pressed="true"] > view:nth-child(2) text:first-child { color:#4a3a86; font-weight:600; }
.candidate-option > view:nth-child(2) { flex:1; display:grid; gap:2px; min-width:0; }
.candidate-option text+text { color:#605476; font-size:13px; }
@media(max-height:730px) { .wander-intro{padding:18px 0 30px} .wander-link.blind-choice+.blind-choice{margin-top:24px} }
@media(prefers-reduced-motion:reduce) {
  .wander-progress view, .wander-planner.is-card-expanding, .wander-loading-pair > view { animation:none; }
  .wander-planner button:active { transform:none !important; }
}
/* 底部主按钮统一为紫边白色玻璃，不再整块紫色 */
.wander-planner .wander-primary,
.wander-planner .wander-secondary,
.wander-planner .wander-cancel {
  background: linear-gradient(135deg, rgba(255,255,255,.97), rgba(248,246,255,.9));
  color: #5c4bc0;
  border: 1px solid rgba(139,120,230,.5);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.95), 0 8px 20px -12px rgba(90,70,180,.28);
}
.wander-planner .wander-primary { font-weight: 600; }
.wander-planner .wander-secondary { border-color: rgba(139,120,230,.32); color: #4f4290; }
.wander-planner .wander-primary:active:not([disabled]),
.wander-planner .wander-secondary:active:not([disabled]) { background: #f1ebff; }

/* 选中态统一：紫边白玻璃，不再整块紫色 */
.wander-planner .wander-times button[aria-pressed="true"],
.wander-planner .wander-pills button[aria-pressed="true"],
.wander-planner .wander-steps-toggle[aria-pressed="true"],
.wander-planner .wander-layer[aria-pressed="true"] {
  background: linear-gradient(135deg, rgba(255,255,255,.97), rgba(248,246,255,.9));
  color: #5c4bc0;
  border: 1px solid rgba(139,120,230,.6);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.95), 0 8px 20px -14px rgba(90,70,180,.3);
  font-weight: 600;
}
.wander-planner .wander-times button[aria-pressed="true"] .wander-icon { color: #7659bb; }

.wander-toast {
  position: fixed; left: 50%; bottom: calc(96px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  max-width: 78%;
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(255,255,255,.97);
  border: 1px solid rgba(139,120,230,.45);
  box-shadow: 0 10px 26px -14px rgba(60,45,120,.35);
  color: #5c4bc0;
  font-size: 13px;
  line-height: 1.5;
  text-align: center;
  z-index: 60;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wander-planner .wander-header{height:62px!important;min-height:0!important;max-width:none!important;margin:0!important;padding:0 14px!important;display:flex!important;align-items:center!important}
.wander-planner .wander-header>.wander-square.wander-back{position:absolute!important;left:14px!important;top:50%!important;transform:translateY(-50%)!important;margin:0!important;z-index:3!important}
.wander-planner .wander-title{position:absolute!important;left:50%!important;top:50%!important;transform:translate(-50%,-50%)!important;font-size:18px!important;font-weight:600!important;line-height:1.4!important;color:#2a2438!important;max-width:calc(100% - 120px)!important;white-space:nowrap!important;text-align:center!important}
.wander-planner .wander-intro{text-align:center!important}
.wander-planner .wander-section-title.time-heading{justify-content:center!important;text-align:center!important;gap:6px!important}
.wander-planner .wander-times button{justify-items:center!important;align-content:center!important;justify-content:center!important;text-align:center!important;gap:8px!important}
.wander-planner .wander-times button .wander-icon{margin:0 auto!important}
.wander-planner .style-choice .wander-symbol{background:#fff!important;color:#6547ad!important;border:1px solid #cbbcf0!important;box-shadow:none!important}
.wander-planner .style-choice[aria-pressed="true"]{background:#fff!important;box-shadow:inset 0 0 0 2rpx #6a5ae0, 0 10rpx 24rpx -28rpx rgba(64,44,120,.35)!important;-webkit-backdrop-filter:none!important;backdrop-filter:none!important}
.wander-planner .style-choice[aria-pressed="true"] .wander-symbol{background:#fff!important;color:#5b49c9!important;border:1px solid #8b78e6!important;box-shadow:none!important}
.wander-planner .wander-time-stage{display:flex!important;flex-direction:column!important;margin-top:14vh!important}
.wander-planner .wander-time-stage .wander-intro{padding:0 0 22px!important;text-align:center!important}
</style>
