<template>
  <view class="scenic-shell">
    <web-view :src="src" @message="onMessage"></web-view>
  </view>
</template>

<script>
import { scenicWebOrigin } from '../../common/config.js'

export default {
  data() {
    return { src: '', deviceId: '' }
  },
  onLoad(query) {
    const spotId = query && query.spotId ? String(query.spotId) : ''
    const view = query && ['plan', 'list', 'catalog', 'journey'].includes(String(query.view)) ? String(query.view) : ''
    const spotIds = query && /^[0-9]+(,[0-9]+)*$/.test(String(query.spotIds || '')) ? String(query.spotIds) : ''
    let device = ''
    try { device = uni.getStorageSync('device_id') || '' } catch (e) {}
    if (!device) {
      device = 'dev-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
      try { uni.setStorageSync('device_id', device) } catch (e) {}
    }
    this.deviceId = device
    this.src = scenicWebOrigin() + '/app/scenic' + (spotId ? '/' + spotId : '') +
      '?device=' + encodeURIComponent(device) + (view ? '&view=' + view : '') + (spotIds ? '&spotIds=' + spotIds : '') +
      ['elderly','children','avoidSteps','startArea','endArea'].filter(key=>query && query[key]!==undefined)
        .map(key=>'&'+key+'='+encodeURIComponent(String(query[key]))).join('')

    // #ifdef APP-PLUS
    const apply = () => {
      try {
        const window = plus.android.runtimeMainActivity().getWindow()
        try { plus.android.importClass(window) } catch (e) {}
        const Color = plus.android.importClass('android.graphics.Color')
        // 底部系统导航条保持白底，并去掉系统自动加的那条灰色分隔线
        window.setNavigationBarColor(Color.parseColor('#ffffff'))
        try { window.setNavigationBarDividerColor(Color.TRANSPARENT) } catch (e) {}
        try { window.setNavigationBarContrastEnforced(false) } catch (e) {}
        plus.navigator.setStatusBarStyle('dark')
        plus.navigator.setStatusBarBackground('#ffffff')
      } catch (error) {}
    }
    if (typeof plus !== 'undefined') apply()
    else document.addEventListener('plusready', apply, { once: true })
    // #endif
  },
  onReady() {
    // Pass authentication inside the native WebView instead of putting it in a URL.
    // #ifdef APP-PLUS
    const page=this.$scope.$getAppWebview()
    const attach=()=>page.children().forEach(view=>{
      const inject=()=>{
        const token=String(uni.getStorageSync('token')||'')
        view.evalJS('try{window.sessionStorage.setItem("scenic-app-token",'+JSON.stringify(token)+')}catch(e){}')
      }
      if(!view.__scenicAuthBound){view.__scenicAuthBound=true;view.addEventListener('loaded',inject)}
      inject()
    })
    attach()
    setTimeout(attach,300)
    // #endif
  },
  onShow() {
    try {
      if (typeof plus !== 'undefined' && plus.navigator) plus.navigator.setFullscreen(false)
    } catch (error) {}
  },
  onBackPress() {
    // 系统返回键与页内返回箭头保持一致：都回 App 首页。
    try {
      this.backHome()
      return true
    } catch (error) {
      return false
    }
  },
  methods: {
    onMessage(event) {
      let messages = event && event.detail ? event.detail.data : null
      if (typeof messages === 'string') {
        try { messages = JSON.parse(messages) } catch (error) {}
      }
      const list = (Array.isArray(messages) ? messages : messages ? [messages] : [])
        .map(item => item && item.data && typeof item.data === 'object' ? item.data : item)
      const last = list[list.length - 1]
      // 景点详情页的返回统一回 App 首页；首页就在栈里时直接回退，保留首页状态。
      if (last && last.type === 'scenic-back') this.backHome()
      if (last && last.type === 'app-tab') this.goAppTab(last.tab)
      if (last && last.type === 'save-checkin' && last.spot) {
        const list = uni.getStorageSync('my_checkins') || []
        list.unshift({ id: Date.now(), spot_name: last.spot, time: new Date(last.time || Date.now()).toLocaleString() })
        uni.setStorageSync('my_checkins', list.slice(0, 50))
      }
      if (last && last.type === 'open-tour-page' && last.sessionId) {
        uni.navigateTo({ url: '/pages/tour/tour?sessionId=' + last.sessionId })
      }
    },
    backHome() {
      const home = '/pages/tabs/tabs'
      const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
      const previous = pages.length > 1 ? pages[pages.length - 2] : null
      const previousRoute = previous && previous.route ? String(previous.route) : ''
      if (previousRoute === 'pages/tabs/tabs') {
        uni.navigateBack({
          delta: 1,
          fail: () => { uni.reLaunch({ url: home }) }
        })
        // 首页组件是缓存实例，回退后再确保停在「首页」这一屏。
        setTimeout(() => { try { uni.$emit('tabs:select', 'home') } catch (error) {} }, 220)
        return
      }
      // 从主题路线、随心逛等入口进来的，也统一落到首页。
      uni.reLaunch({
        url: home,
        fail: () => { uni.navigateBack({ delta: 1 }) }
      })
    },
    goAppTab(tab) {
      const home = '/pages/tabs/tabs'
      const key = ['home', 'ai', 'mine'].includes(String(tab)) ? String(tab) : 'home'
      try { uni.$emit('tabs:preselect', key) } catch (error) {}
      const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
      const previous = pages.length > 1 ? pages[pages.length - 2] : null
      const previousRoute = previous && previous.route ? String(previous.route) : ''
      if (previousRoute === 'pages/tabs/tabs') {
        uni.navigateBack({
          delta: 1,
          success: () => { setTimeout(() => { try { uni.$emit('tabs:select', key) } catch (error) {} }, 220) },
          fail: () => { uni.reLaunch({ url: home + '?tab=' + key }) }
        })
        return
      }
      uni.reLaunch({ url: home + '?tab=' + key })
    }
  }
}
</script>

<style>
page { background: #ffffff !important; }
.scenic-shell { position: relative; width: 100%; height: 100vh; background: #ffffff; }
</style>
