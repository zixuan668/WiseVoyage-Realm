<template>
  <view class="park-home" :class="{ 'park-expanded': expanded, 'park-dragging': dragging }"
    :style="{ '--park-pull': pull + 'px',
      '--park-map-opacity': expanded ? Math.max(0, 1 + pull / 120) : 0 }">
    <view class="park-map-frame" :data-park-provider="provider"
      @touchstart="expanded && startPull($event, -1)" @touchmove="expanded && movePull($event)"
      @touchend="expanded && endPull($event)" @touchcancel="resetPull">
      <ParkMap :points="mapPoints" :lines="mapLines" :action="mapAction" :expanded="expanded"
        :pulling="dragging" :heading="heading" :obstructions="obstructions" @status="provider=$event" @marker="chooseMarker" />
      <text v-if="mapNotice && !expanded" class="park-map-status">{{ t(mapNotice) }}</text>
    </view>
    <view v-if="!expanded" class="park-map-reveal" @touchstart="startPull($event, 1)" @touchmove="movePull"
      @touchend="endPull" @touchcancel="resetPull" />
    <view class="park-status-veil" aria-hidden="true"></view>
    <button class="park-scan" :aria-label="t('扫码领取路线')" @tap.stop="$emit('claim-scan')">
      <text class="park-scan-icon iconfont icon-scan" aria-hidden="true"></text>
      <text class="park-scan-label">{{ t('扫码领取路线') }}</text>
    </button>
    <view class="park-content-layer">
    <scroll-view :scroll-y="!expanded && !dragging" :aria-hidden="expanded" class="park-page" :show-scrollbar="false"
      @scroll="onPageScroll">
      <view class="park-content" @touchstart.capture="pagePullStart" @touchmove.capture="pagePullMove"
        @touchend.capture="pagePullEnd" @touchcancel.capture="resetPull">
        <view class="park-action-panel" @touchstart="startPull($event, 1)" @touchmove="movePull"
          @touchend="endPull" @touchcancel="resetPull">
          <view class="park-actions">
            <button :aria-label="t('景点详情')" @tap="$emit('catalog')">
              <view class="park-action-icon park-icon-pin" aria-hidden="true"></view>
              <text class="park-action-name">{{ t('景点详情') }}</text>
            </button>
            <button :aria-label="t('路径规划')" @tap="$emit('planning', {})">
              <view class="park-action-icon park-icon-route" aria-hidden="true"></view>
              <text class="park-action-name">{{ t('路径规划') }}</text>
            </button>
            <button :aria-label="t('随心逛')" @tap="$emit('planning', { wander: true })">
              <view class="park-action-icon park-icon-compass" aria-hidden="true"></view>
              <text class="park-action-name">{{ t('随心逛') }}</text>
            </button>
          </view>
        </view>
        <button class="park-section-heading" :aria-label="t('查看全部主题路线')" @tap="$emit('planning', { wander: true, featured: true })">
          <text>{{ t('主题路线') }}</text><view class="park-section-arrow" aria-hidden="true"></view>
        </button>
        <view v-if="featured.length" class="park-carousel" role="region" :aria-label="t('主题路线')">
          <swiper :current="carouselIndex" :circular="featured.length > 2" :duration="320" previous-margin="56rpx" next-margin="56rpx"
            :skip-hidden-item-layout="false" @touchstart.stop @touchmove.stop @touchend.stop @touchcancel.stop @change="carouselChanged">
            <swiper-item v-for="(route,index) in featured" :key="route.route_id">
              <button class="park-route" :class="{ 'is-featured': index === carouselIndex }" :aria-label="t(route.name)"
                @tap="pickRoute(route, index)">
                <image v-if="route.image" :src="route.image" mode="aspectFill" />
                <view class="park-route-shade" />
                <view class="park-route-copy">
                  <text class="park-route-title">{{ t(route.name) }}</text>
                  <text v-if="route.stops.length" class="park-route-note">{{ route.stops.slice(0,3).map(name => t(name)).join(' · ') }}</text>
                </view>
              </button>
            </swiper-item>
          </swiper>
        </view>
        <view v-else class="park-route-empty">
          <text>{{ t(catalogError || '正在加载主题路线…') }}</text>
          <button v-if="catalogError" @tap="$emit('retry')">{{ t('重试') }}</button>
        </view>
        <view v-if="featured.length > 1" class="park-pagination" aria-hidden="true">
          <view v-for="(route,index) in featured" :key="route.route_id" :class="{ active: index === carouselIndex }" />
        </view>
      </view>
    </scroll-view>
    </view>

    <view v-if="expanded" class="park-map-page" :data-park-provider="provider">
      <view class="park-map-header">
        <view class="park-map-filter-row">
          <button :aria-expanded="panel === 'facilities'" @tap="togglePanel('facilities')">{{ t('服务设施') }}</button>
          <button :aria-expanded="panel === 'roads'" @tap="togglePanel('roads')">{{ t('道路信息') }}</button>
        </view>
        <view class="park-weather" :class="{ 'is-open': weatherOpen, 'has-error': !weather }">
        <button class="park-weather-small" :aria-hidden="weatherOpen" :aria-label="t('打开天气')" @tap="openWeather">
          <view class="park-weather-temp"><text class="park-weather-icon">{{ weather?.icon || '☁' }}</text>
            <text>{{ degree(weather?.temperature) }}</text></view>
          <text v-if="!weather" class="park-weather-sub">{{ t('颐和园天气') }}</text>
        </button>
        <view class="park-weather-large" :aria-hidden="!weatherOpen">
          <view class="park-sheet-heading">
            <view><text class="park-sheet-title">{{ t('颐和园天气') }}</text><text v-if="weather" class="park-muted">{{ t(weather.title) }}</text></view>
            <button :aria-label="t('收起天气')" @tap="closeWeather">×</button>
          </view>
          <template v-if="weather">
            <view class="park-weather-summary">
              <text class="park-weather-temp">{{ weather.icon }} {{ degree(weather.temperature) }}</text>
              <text class="park-muted">{{ t('最高') }} {{ degree(weather.high) }} / {{ t('最低') }} {{ degree(weather.low) }}</text>
            </view>
            <view class="park-forecast">
              <view v-for="row in weather.hours" :key="row.time">
                <text>{{ t(row.time) }}</text><text class="park-forecast-icon">{{ row.icon }}</text><text>{{ degree(row.temperature) }}</text>
              </view>
              <view v-if="weather.sunset"><text>{{ t('日落') }}</text><text class="park-forecast-icon">☼</text><text>{{ weather.sunset }}</text></view>
            </view>
          </template>
          <view v-else class="park-empty-weather">
            <text>{{ t(weatherError || '正在获取天气…') }}</text>
            <button v-if="weatherError" @tap="fetchWeather">{{ t('重试') }}</button>
          </view>
        </view>
        <button v-if="weather" class="park-weather-source" :aria-label="t('天气数据由 Open-Meteo 提供')"
          :title="t('天气数据由 Open-Meteo 提供')" @tap="openWeatherSource">
          <text class="iconfont icon-arrow-up-right" aria-hidden="true" />
        </button>
        </view>

      <view v-if="panel || activeItem" class="park-sheet park-map-sheet park-layer-popup"
        :class="{ 'is-closing': panelClosing }">
        <view class="park-sheet-heading">
          <text class="park-sheet-title">{{ t(activeItem?.name || (panel === 'facilities' ? '服务设施' : '道路信息')) }}</text>
          <button :aria-label="t('关闭')" @tap="clearPanel">×</button>
        </view>
        <scroll-view scroll-y class="park-sheet-scroll">
          <template v-if="activeItem?.kind === 'facility'">
            <text class="park-sheet-line">{{ t('建议入口') }} · {{ t(activeItem.entrance) }}</text>
            <text class="park-sheet-line">{{ t('位置') }} · {{ t(activeItem.location) }}</text>
            <text class="park-muted">{{ t('官网核对日期') }} · {{ activeItem.checkedAt }}</text>
          </template>
          <template v-else-if="activeItem?.kind === 'scenic'">
            <text class="park-sheet-line">{{ t(activeItem.spot.location || activeItem.spot.description || '') }}</text>
            <view class="park-source-row">
              <button @tap="$emit('planning', { spot: activeItem.spot })">{{ t('景点详情') }}</button>
              <button @tap="openAI('chat')">{{ t('问 AI 导游') }}</button>
            </view>
          </template>
          <template v-else-if="panel === 'facilities'">
            <button v-for="item in facilities" :key="item.id" class="park-list-button" @tap="selectItem(item)">
              <text>{{ t(item.name) }}</text><text>{{ t(item.type) }} ›</text>
            </button>
          </template>
          <template v-else>
            <view class="park-road-options">
              <button :aria-pressed="showSteps" :class="{ active: showSteps }" @tap="showSteps=!showSteps">{{ t('已标注台阶') }}</button>
              <button :aria-pressed="showAccessible" :class="{ active: showAccessible }" @tap="toggleAccessible">{{ t('避台阶参考线') }}</button>
            </view>
            <text v-if="roadMessage" class="park-muted">{{ t(roadMessage) }}</text>
            <text class="park-sheet-line">{{ t('台阶来自路网标注，实际通行请以景区指引和现场为准。') }}</text>
            <view v-for="route in officialRoutes" :key="route.title" class="park-road-row">
              <text>{{ t(route.title) }} · {{ route.meters }} m</text>
              <text class="park-muted">{{ t(route.detail) }}</text>
            </view>
          </template>
        </scroll-view>
      </view>
      </view>

      <view class="park-map-heading">
        <button class="park-compass" :class="{ 'is-following': followingHeading }" :aria-pressed="followingHeading"
          :aria-label="t(followingHeading ? '恢复固定朝向' : '跟随手机朝向')" @tap="toggleHeading">
          <view class="park-compass-needle" :style="{ transform: 'rotate(' + (heading ?? 0) + 'deg)' }" />
          <text>{{ t(cardinal) }}</text>
        </button>
      </view>
      <view class="park-map-tools">
        <button :aria-label="t('回到当前位置')" @tap="locate"><view class="park-target" /></button>
        <button :aria-label="t('放大地图')" @tap="moveMap('zoom', { delta: 1 })">+</button>
        <button :aria-label="t('缩小地图')" @tap="moveMap('zoom', { delta: -1 })">−</button>
      </view>

      <view v-if="mapNotice" class="park-provider" aria-live="polite">{{ t(mapNotice) }}</view>
      <view class="park-map-footer" @touchstart="startPull($event, -1)"
        @touchmove="movePull" @touchend="endPull" @touchcancel="resetPull">
        <view v-if="searchOpen && query.trim()" class="park-search-results">
          <button v-for="item in searchResults" :key="item.id" @tap="selectItem(item)">
            <text>{{ t(item.name) }}</text><text>{{ t(item.type || '景点') }}</text>
          </button>
          <button @tap="askQuery">{{ t('向 AI 导游提问') }} ↗</button>
        </view>
        <view class="park-assistant">
          <button class="park-assistant-search" :aria-label="t('搜索或提问')" @tap="handleAssistant">⌕</button>
          <input v-model="query" class="park-assistant-query" :placeholder="t('想去哪里？问问导游')" :adjust-position="false"
            confirm-type="search" @focus="searchOpen=true" @confirm="submitSearch" />
          <button :aria-label="t('语音问导游')" @tap="openAI('voice')"><text class="iconfont icon-yuyin" /></button>
          <button :aria-label="t('拍照问导游')" @tap="openAI('camera')"><text class="iconfont icon-cam-3" /></button>
          <button class="park-portrait" :aria-label="t('进入 AI 导游')" @tap="openAI('chat')">
            <image src="/static/park-home/guide-portrait.png" mode="aspectFill" />
          </button>
        </view>
      </view>
    </view>


  </view>
</template>

<script>
import ParkMap from './ParkMap.vue'
import { ACCESS_ROUTES, FACILITIES, STEP_LINES, WEATHER_REFRESH_MS,
  accessibleRoads, featuredRoads, homeRoutes, loadParkWeather, scenicMarkers } from '../common/park-home-data.js'

export default {
  components: { ParkMap },
  props: { spots: Array, routes: Array, catalogError: String, active: Boolean, selectedRouteId: [String, Number] },
  emits: ['planning', 'catalog', 'ai', 'retry', 'map-change', 'claim-scan'],
  data() {
    const initialCard = homeRoutes(this.routes || [], this.spots || []).findIndex(route => route.route_id === this.selectedRouteId)
    return {
      expanded: false, carouselIndex: Math.max(0, initialCard), pull: 0, dragging: false, query: '', searchOpen: false,
      provider: '', mapAction: null, location: null, activeItem: null, lastSpot: null,
      panel: '', panelClosing: false, showSteps: false, showAccessible: false, accessibleLines: [], roadMessage: '',
      pageScrollTop: 0,
      weather: null, weatherError: '', weatherOpen: false,
      featuredLines: [], followingHeading: false, heading: null,
      facilities: FACILITIES, officialRoutes: ACCESS_ROUTES,
    }
  },
  computed: {
    featured() { return homeRoutes(this.routes || [], this.spots || []) },
    scenic() { return scenicMarkers(this.spots || []) },
    selectedRoute() {
      const route = (this.routes || []).find(item => item.route_id === this.selectedRouteId)
      return (route?.spot_ids || []).join(',')
    },
    cardinal() {
      if (!Number.isFinite(this.heading)) return '北'
      return ['北', '东北', '东', '东南', '南', '西南', '西', '西北'][Math.round(this.heading / 45) % 8]
    },
    obstructions() { return [this.weatherOpen, !!this.weather, this.panel, this.activeItem?.id, this.searchOpen && this.query.trim()].join('|') },
    searchResults() {
      const keyword = this.query.trim().toLowerCase().replace(/厕所|公厕/g, '卫生间').replace(/服务站/g, '游客服务中心')
      if (!keyword) return []
      return [...this.scenic, ...this.facilities].filter(item =>
        [item.name, item.type, item.entrance, item.spot?.tags, item.spot?.location].some(value =>
          String(value || '').toLowerCase().includes(keyword))).slice(0, 6)
    },
    mapPoints() {
      const facilities = this.activeItem?.kind === 'facility' ? [this.activeItem]
        : this.panel === 'facilities' ? this.facilities.filter(item => item.id !== 'third-east') : []
      return [...this.scenic, ...facilities, ...(this.location ? [this.location] : [])]
        .filter(point => Number.isFinite(point.latitude) && Number.isFinite(point.longitude))
    },
    mapLines() { return [...this.featuredLines, ...(this.showSteps ? STEP_LINES : []), ...(this.showAccessible ? this.accessibleLines : [])] },
    mapNotice() {
      return {
        offline: '底图加载失败，仍可查看点位和道路', unavailable: '地图暂不可用',
        'amap-failed': '高德底图加载失败，正在切换备用底图', 'osm-loading': '正在加载备用底图…',
      }[this.provider] || ''
    },
  },
  watch: {
    featured(value) { if (this.carouselIndex >= value.length) this.carouselIndex = 0 },
    selectedRoute: { immediate: true, handler: 'loadFeaturedRoads' },
    active(value) {
      if (value && this.expanded) this.startWeatherRefresh()
      if (!value) {
        // 切到别的 Tab 时收起大图，避免回到首页还是全屏地图
        if (this.expanded) this.closeMap()
        this.stopHeading()
        this.stopWeatherRefresh()
      }
    },
  },
  mounted() {
    // #ifdef H5
    this._removeMousePull = this.listenForMousePull()
    // #endif
  },
  beforeUnmount() {
    this._removeMousePull?.()
    clearTimeout(this._panelTimer)
    this.stopWeatherRefresh()
    this.stopHeading()
  },
  methods: {
    degree(value) { return Number.isFinite(value) ? Math.round(value) + '°' : '—' },
    carouselChanged(event) { this.carouselIndex = event.detail.current },
    pickRoute(route, index) {
      if (index !== this.carouselIndex) { this.carouselIndex = index; return }
      this.$emit('planning', { route, wander: true })
    },
    async loadFeaturedRoads(ids) {
      this.featuredLines = []
      if (!ids) return
      try {
        const lines = await featuredRoads(ids.split(',').map(Number))
        if (ids === this.selectedRoute) this.featuredLines = lines
      } catch (_) { /* Keep the live map usable when the route API is unavailable. */ }
    },
    startPull(event, direction) {
      if (event.touches.length !== 1) { this.resetPull(); return }
      this.beginPull(event.touches[0], direction)
    },
    // Let the whole content sheet drag down (not just the map strip) so the
    // sheet collapses smoothly from anywhere once the list is at its top.
    onPageScroll(event) {
      this.pageScrollTop = Math.max(0, Number(event && event.detail && event.detail.scrollTop) || 0)
    },
    pagePullStart(event) {
      if (this.expanded || this.pageScrollTop > 0) return
      if (!event.touches || event.touches.length !== 1) return
      this.beginPull(event.touches[0], 1)
    },
    pagePullMove(event) {
      if (!this._pullStart || this.expanded) return
      if (this.pageScrollTop > 0 || !event.touches || event.touches.length !== 1) { this.resetPull(); return }
      this.updatePull(event.touches[0])
    },
    pagePullEnd(event) { this.finishPull(event.changedTouches && event.changedTouches[0]) },
    movePull(event) {
      if (event.touches.length !== 1) { this.resetPull(); return }
      this.updatePull(event.touches[0])
    },
    endPull(event) { this.finishPull(event.changedTouches?.[0]) },
    beginPull(point, direction) {
      if (this.expanded !== (direction === -1)) return
      this._pullStart = { x: point.clientX, y: point.clientY, direction, time: Date.now() }
    },
    updatePull(point) {
      const start = this._pullStart
      if (!start) return
      const delta = point.clientY - start.y
      if (!this.dragging) {
        const horizontal = Math.abs(point.clientX - start.x)
        if (Math.max(Math.abs(delta), horizontal) < 10) return
        if (delta * start.direction <= horizontal * 1.2) { this.resetPull(); return }
        this.dragging = true
      }
      this.pull = Math.max(0, delta * start.direction) * start.direction
    },
    finishPull(point) {
      const start = this._pullStart
      const dragged = this.dragging
      this.resetPull()
      if (!start || !point || !dragged) return
      const delta = (point.clientY - start.y) * start.direction
      if (delta < 72 && (delta < 38 || delta / Math.max(1, Date.now() - start.time) < .28)) return
      if (start.direction === 1) this.openMap()
      else this.closeMap()
    },
    resetPull() { this._pullStart = null; this.dragging = false; this.pull = 0 },
    // #ifdef H5
    listenForMousePull() {
      const root = this.$el
      let pointer = null
      let swallowClick = false
      const press = event => {
        swallowClick = false
        if (event.pointerType !== 'mouse' || event.button !== 0) return
        const region = event.target.closest?.(this.expanded ? '.park-map-frame,.park-map-footer' : '.park-map-reveal,.park-action-panel')
        if (!region || !root.contains(region) || event.target.closest?.('input,textarea,a')) return
        pointer = event.pointerId
        this.beginPull(event, this.expanded ? -1 : 1)
      }
      const cancel = () => {
        if (pointer === null) return
        pointer = null
        this.resetPull()
      }
      const move = event => {
        if (event.pointerId !== pointer) return
        if (!(event.buttons & 1)) { cancel(); return }
        this.updatePull(event)
        if (this.dragging) event.preventDefault()
      }
      const release = event => {
        if (event.pointerId !== pointer) return
        pointer = null
        swallowClick = this.dragging
        this.finishPull(event)
      }
      const click = event => {
        if (!swallowClick) return
        swallowClick = false
        if (!root.contains(event.target)) return
        event.preventDefault()
        event.stopPropagation()
      }
      root.addEventListener('pointerdown', press, true)
      window.addEventListener('pointermove', move, true)
      window.addEventListener('pointerup', release, true)
      window.addEventListener('pointercancel', cancel, true)
      window.addEventListener('blur', cancel)
      root.addEventListener('click', click, true)
      return () => {
        root.removeEventListener('pointerdown', press, true)
        window.removeEventListener('pointermove', move, true)
        window.removeEventListener('pointerup', release, true)
        window.removeEventListener('pointercancel', cancel, true)
        window.removeEventListener('blur', cancel)
        root.removeEventListener('click', click, true)
      }
    },
    // #endif
    openMap() {
      if (this.expanded) return
      this.expanded = true
      this.$emit('map-change', true)
      this.startWeatherRefresh()
    },
    closeMap() {
      if (!this.expanded) return
      this.expanded = false
      this.stopWeatherRefresh()
      this.closeWeather()
      this.clearPanel(true)
      this.clearSearch()
      this.stopHeading()
      this.$emit('map-change', false)
    },
    backMap() {
      if (this.panel || this.activeItem) this.clearPanel()
      else if (this.weatherOpen) this.closeWeather()
      else this.closeMap()
    },
    togglePanel(panel) {
      if (this.panel === panel && !this.activeItem && !this.panelClosing) { this.clearPanel(); return }
      clearTimeout(this._panelTimer)
      this.panelClosing = false
      this.panel = panel
      this.activeItem = null
    },
    clearPanel(immediate = false) {
      if (immediate === true) {
        clearTimeout(this._panelTimer)
        this.panel = ''; this.activeItem = null; this.panelClosing = false
        return
      }
      if (this.panelClosing || !(this.panel || this.activeItem)) return
      this.panelClosing = true
      this._panelTimer = setTimeout(() => this.clearPanel(true), 110)
    },
    openWeather() { this.weatherOpen = true; this.fetchWeather() },
    closeWeather() { this.weatherOpen = false },
    clearSearch() { this.searchOpen = false; this.query = '' },
    submitSearch() {
      if (this.searchResults.length) this.selectItem(this.searchResults[0])
      else this.askQuery()
    },
    askQuery() {
      const text = this.query.trim()
      if (text) this.openAI('chat', text)
    },
    handleAssistant() {
      if (this.query.trim()) this.submitSearch()
      else this.openAI('chat')
    },
    selectItem(item) {
      this.openMap()
      this.clearSearch()
      this.clearPanel(true)
      this.activeItem = item
      if (item.spot) this.lastSpot = item.spot
      if (Number.isFinite(item.latitude) && Number.isFinite(item.longitude)) {
        this.moveMap('focus', { position: [item.latitude, item.longitude] })
      }
    },
    chooseMarker(id) {
      const item = this.mapPoints.find(candidate => candidate.id === id)
      if (item && item.kind !== 'location') this.selectItem(item)
    },
    moveMap(type, data = {}) { this.mapAction = { type, ...data, id: (this.mapAction?.id || 0) + 1 } },
    async toggleHeading() {
      if (this.followingHeading) { this.stopHeading(); return }
      const session = {}
      this._headingSession = session
      this.followingHeading = true
      const receive = direction => {
        if (this._headingSession !== session || !Number.isFinite(direction) || direction < 0) return
        clearTimeout(this._compassTimeout)
        this.heading = Math.round(direction) % 360
      }
      const unavailable = () => {
        if (this._headingSession !== session) return
        this.stopHeading()
        uni.showToast({ title: this.t('暂时无法读取手机朝向'), icon: 'none' })
      }
      try {
        // #ifdef H5
        const sensor = window.DeviceOrientationEvent
        if (!sensor) { unavailable(); return }
        if (sensor.requestPermission && await sensor.requestPermission() !== 'granted') { unavailable(); return }
        if (this._headingSession !== session) return
        const listener = event => {
          if (Number.isFinite(event.webkitCompassHeading) && event.webkitCompassHeading >= 0) {
            receive(event.webkitCompassHeading)
          } else if ((event.absolute || event.type === 'deviceorientationabsolute') && Number.isFinite(event.alpha)) {
            receive((360 - event.alpha + 360) % 360)
          }
        }
        window.addEventListener('deviceorientation', listener)
        window.addEventListener('deviceorientationabsolute', listener)
        this._removeHeading = () => {
          window.removeEventListener('deviceorientation', listener)
          window.removeEventListener('deviceorientationabsolute', listener)
        }
        // #endif
        // #ifdef APP-PLUS
        const listener = ({ direction }) => receive(direction)
        uni.onCompassChange(listener)
        this._removeHeading = () => uni.offCompassChange(listener)
        // #endif
      } catch (_) { unavailable(); return }
      this._compassTimeout = setTimeout(unavailable, 5000)
      if (!this.location) this.locate()
    },
    stopHeading() {
      clearTimeout(this._compassTimeout)
      try { this._removeHeading?.() } catch (_) { /* The platform can already have stopped the sensor. */ }
      this._removeHeading = null
      this._headingSession = null
      this.heading = null
      this.followingHeading = false
    },
    locate() {
      if (this._locating) return
      this._locating = true
      uni.getLocation({
        type: 'wgs84', isHighAccuracy: true, highAccuracyExpireTime: 7000,
        success: ({ latitude, longitude, accuracy }) => {
          if (!this.expanded) return
          if (latitude < 39.980 || latitude > 40.008 || longitude < 116.244 || longitude > 116.284) {
            uni.showToast({ title: this.t('你当前不在颐和园范围内'), icon: 'none' })
            return
          }
          if (Number.isFinite(accuracy) && accuracy > 150) {
            uni.showToast({ title: this.t('定位精度较低，请到开阔处重试'), icon: 'none' })
            return
          }
          this.location = { id: 'visitor-location', kind: 'location', name: this.t('当前位置'), latitude, longitude }
          this.moveMap('focus', { position: [latitude, longitude] })
        },
        fail: () => uni.showToast({ title: this.t('暂时无法定位，请检查位置权限'), icon: 'none' }),
        complete: () => { this._locating = false },
      })
    },
    startWeatherRefresh() {
      this.stopWeatherRefresh()
      this.fetchWeather()
      this._weatherRefresh = setInterval(() => this.fetchWeather(), WEATHER_REFRESH_MS)
    },
    stopWeatherRefresh() { clearInterval(this._weatherRefresh) },
    async fetchWeather() {
      if (this._weatherPending) return
      this._weatherPending = true
      this.weatherError = ''
      try { this.weather = await loadParkWeather() }
      catch (_) {
        if (!this.weather || Date.now() - this.weather.observedAt > 90 * 60 * 1000) {
          this.weather = null
          this.weatherError = '天气暂不可用'
        }
      }
      finally { this._weatherPending = false }
    },
    async toggleAccessible() {
      this.showAccessible = !this.showAccessible
      if (!this.showAccessible || this.accessibleLines.length || this._accessiblePending) return
      this._accessiblePending = true
      this.roadMessage = '正在获取避台阶参考线…'
      try {
        this.accessibleLines = await accessibleRoads(this.spots || [])
        this.roadMessage = this.accessibleLines.length ? '参考线根据路网避开已标注台阶，实际无障碍通行请以景区指引为准。' : '当前没有可显示的避台阶参考线'
      } catch (_) { this.roadMessage = '避台阶参考线暂不可用' }
      finally { this._accessiblePending = false }
    },
    openAI(mode, question = '') {
      this.searchOpen = false
      this.$emit('ai', { mode, spot: this.activeItem?.spot || this.lastSpot, question })
    },
    openWeatherSource() {
      const url = 'https://open-meteo.com/en/license'
      // #ifdef H5
      window.open(url, '_blank', 'noopener,noreferrer')
      // #endif
      // #ifdef APP-PLUS
      plus.runtime.openURL(url)
      // #endif
    },
  },
}
</script>

<style src="./park-home.css"></style>
