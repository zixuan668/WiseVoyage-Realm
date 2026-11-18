<template>
  <view class="tabs-shell">
    <swiper class="pager-viewport" :current="pagerCurrent" :duration="pagerDuration" :circular="false" :disable-touch="pagerLocked" :skip-hidden-item-layout="false" @change="onPagerChange" @animationfinish="onPagerFinish">
      <swiper-item><view class="panel-slot"><Home ref="home" :active="pagerCurrent === 0" @ai="onHomeAi" @map-change="homeMap = $event" /></view></swiper-item>
      <swiper-item><view class="panel-slot"><AiChat ref="ai" /></view></swiper-item>
      <swiper-item><view class="panel-slot"><Mine ref="mine" /></view></swiper-item>
    </swiper>
    <TabDock :current="pagerCurrent" :progress="pagerCurrent" :hidden="dockHidden" @select="selectTab" />
    <FloatingTourButton v-if="tourOrb && current!==0" label="继续导览" @activate="resumeTour" />
  </view>
</template>
<script>
import Home from '../home/home.vue'
import AiChat from '../ai-chat/ai-chat.vue'
import Mine from '../mine/mine.vue'
import TabDock from '../../components/TabDock.vue'
import FloatingTourButton from '../../components/FloatingTourButton.vue'
import { loadScenicDraft } from '../../common/scenic-api.js'

const TAB_KEYS = ['home', 'ai', 'mine']
const validIndex = index => Number.isInteger(index) && index >= 0 && index < TAB_KEYS.length
export default {
  components: { Home, AiChat, Mine, TabDock, FloatingTourButton },
  data() {
    return { current: 0, pagerCurrent: 0, pagerDuration: 260, pendingTab: null, switching: false,
      panelReady: false, shellVisible: false, shownPanel: null, initialized: [false, false, false],
      keyboardOpen: false, itineraryOpen: false, homeMap: false, tourOrb: false }
  },
  computed: {
    // 底部 Tab 栏只在键盘/导览全屏时收起；首页展开地图时保持可见
    dockHidden() { return this.keyboardOpen || this.itineraryOpen },
    // 展开地图时仍锁定左右翻页，避免在图上横滑误切 Tab
    pagerLocked() { return this.dockHidden || this.homeMap },
  },
  onLoad(query) {
    const index = TAB_KEYS.indexOf((query && query.tab) || 'home')
    this.current = this.pagerCurrent = index < 0 ? 0 : index
    this._onKeyboard = event => { this.keyboardOpen = !!(event && event.height > 0) }
    if (uni.onKeyboardHeightChange) uni.onKeyboardHeightChange(this._onKeyboard)
    this._onDockSync = payload => { if (payload && payload.source === 'tour') this.itineraryOpen = !!payload.hide }
    this._onTabsSelect = payload => {
      const key = typeof payload === 'string' ? payload : (payload && payload.tab) || 'home'
      this.selectTab(TAB_KEYS.indexOf(key))
    }
    // 二级页点“AI导游 / 我的”返回前先预选目标 tab，避免回退时首页先闪一下。
    this._onTabsPreselect = payload => {
      const key = typeof payload === 'string' ? payload : (payload && payload.tab) || 'home'
      const index = TAB_KEYS.indexOf(key)
      if (index < 0) return
      this.pendingTab = null
      this.switching = false
      this.preparePanel(index)
      this.pagerDuration = 0
      this.current = this.pagerCurrent = index
      if (this.shellVisible && this.panelReady) { this.shownPanel = null; this.showPanel() }
      setTimeout(() => { this.pagerDuration = 260 }, 60)
    }
    uni.$on('dock:sync', this._onDockSync)
    uni.$on('tabs:select', this._onTabsSelect)
    uni.$on('tabs:preselect', this._onTabsPreselect)
  },
  mounted() {
    this.$nextTick(() => {
      this.panelReady = true
      this.preparePanel(this.current)
      this.showPanel()
    })
  },
  onShow() { this.shellVisible = true; if (this.panelReady) this.showPanel(); this.syncTourOrb() },
  onHide() {
    this.shellVisible = false
    this.hidePanel()
    this.pendingTab = null
    this.current = this.pagerCurrent
    this.switching = false
  },
  onUnload() {
    this.shellVisible = false
    this.hidePanel()
    for (let i = 0; i < TAB_KEYS.length; i++) if (this.initialized[i]) this.callHook(i, 'onUnload')
    if (uni.offKeyboardHeightChange && this._onKeyboard) uni.offKeyboardHeightChange(this._onKeyboard)
    uni.$off('dock:sync', this._onDockSync)
    uni.$off('tabs:select', this._onTabsSelect)
    uni.$off('tabs:preselect', this._onTabsPreselect)
  },
  onBackPress() {
    // 先交给当前 tab 处理；没处理也不触发系统默认的“再按一次退出应用”提示。
    this.callHook(this.current, 'onBackPress')
    return true
  },
  methods: {
    panel(index) { return [this.$refs.home, this.$refs.ai, this.$refs.mine][index] || null },
    // Embedded pages retain their component instances; forward page hooks only when visible.
    hookFns(raw, output) {
      if (!raw) return output
      if (typeof raw === 'function') { output.push(raw); return output }
      if (Array.isArray(raw)) { raw.forEach(item => this.hookFns(item, output)); return output }
      if (typeof raw === 'object') { Object.values(raw).forEach(item => this.hookFns(item, output)) }
      return output
    },
    callHook(index, hook, arg) {
      const vm = this.panel(index)
      if (!vm || !vm.$options) return undefined
      const fns = this.hookFns(vm.$options[hook], [])
      let result
      for (const fn of fns) {
        try {
          const value = fn.call(vm, arg)
          if (value !== undefined) result = value
        } catch (error) { console.error('[tabs] ' + hook + ' failed', error) }
      }
      return result
    },
    preparePanel(index) {
      const panel = this.panel(index)
      if (panel && typeof panel.syncProfileSession === 'function') panel.syncProfileSession()
      if (this.initialized[index] || !this.panelReady) return
      this.initialized[index] = true
      this.callHook(index, 'onLoad', {})
      this.callHook(index, 'onReady')
    },
    hidePanel() {
      if (this.shownPanel == null) return
      this.callHook(this.shownPanel, 'onHide')
      this.shownPanel = null
    },
    showPanel() {
      if (!this.shellVisible || !this.panelReady || this.shownPanel === this.current) return
      this.hidePanel()
      this.preparePanel(this.current)
      this.shownPanel = this.current
      this.callHook(this.current, 'onShow')
    },
    // 首页「问 AI / 语音 / 拍照」按钮带上模式：切到 AI 页后直接进入对应流程。
    onHomeAi(payload) {
      this.selectTab(1)
      const mode = payload && payload.mode
      if (mode !== 'camera') return
      const open = () => {
        const ai = this.$refs.ai
        if (ai && typeof ai.openCamera === 'function') ai.openCamera()
      }
      // 等翻页动画落定再拉起相机，避免相机盖在切换动画上。
      setTimeout(open, 300)
    },
    async syncTourOrb() {
      var saved = null
      try { saved = uni.getStorageSync('home-orb-resume') } catch (error) {}
      if (!saved || !saved.kind) { this.tourOrb = false; return }
      this.tourOrb = saved.kind === 'tour' ? !!saved.sid : true
    },
    resumeTour() {
      var saved = null
      try { saved = uni.getStorageSync('home-orb-resume') } catch (error) {}
      if (!saved || !saved.kind) { this.tourOrb = false; return }
      if (saved.kind === 'tour' && saved.sid) {
        uni.navigateTo({ url: '/pages/tour/tour?sessionId=' + saved.sid })
        return
      }
      var resume = saved.kind === 'plan-result' ? 'result' : '1'
      uni.navigateTo({ url: '/pages/scenic/scenic?view=plan&resume=' + resume })
    },
    selectTab(index) {
      if (!validIndex(index)) return
      if (this.switching) { this.pendingTab = index === this.pagerCurrent ? null : index; return }
      if (index === this.current) return
      this.preparePanel(index)
      this.switching = true
      // 跨过中间标签时直接定位，避免短暂露出无关页面。
      this.pagerDuration = Math.abs(index - this.current) > 1 ? 0 : 260
      this.pagerCurrent = index
      if (uni.hideKeyboard) uni.hideKeyboard()
    },
    onPagerChange(event) {
      const index = event && event.detail && event.detail.current
      if (!validIndex(index)) return
      this.preparePanel(index)
      this.pagerCurrent = index
      this.switching = index !== this.current
    },
    onPagerFinish(event) {
      const index = event && event.detail && event.detail.current
      if (!validIndex(index) || index !== this.pagerCurrent) return
      this.current = index
      this.switching = false
      this.showPanel()
      const next = this.pendingTab
      this.pendingTab = null
      if (next != null && next !== index) this.$nextTick(() => this.selectTab(next))
    },
  },
}
</script>
<style scoped>
.tabs-shell{width:100%;height:100vh;height:100dvh;overflow:hidden;background:linear-gradient(135deg,#eee8ff 0%,#fbfbff 52%,#eef8fc 100%)}
.pager-viewport{width:100%;height:100%;overflow:hidden}
.panel-slot{width:100%;height:100%;overflow:hidden;contain:layout}
</style>
<style>
/* Keep the shared background still while the cached pages move above it. */
.panel-slot .aurora-background{display:none}
</style>
