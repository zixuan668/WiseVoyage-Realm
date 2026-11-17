<template>
  <TabDock :current="active" :progress="active" :hidden="hidden" inline @select="pick" />
</template>
<script>
import TabDock from './TabDock.vue'
const TABS = ['home', 'ai', 'mine']
export default {
  name: 'PageDock',
  components: { TabDock },
  // 二级页也常驻底部 tab：active 传 0/1/2 高亮对应 tab，传 -1 时由 TabDock 自己处理。
  props: {
    active: { type: Number, default: -1 },
    hidden: { type: Boolean, default: false },
  },
  methods: {
    pick(i) {
      const tab = TABS[i] || 'home'
      const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
      const previous = pages.length > 1 ? pages[pages.length - 2] : null
      const previousRoute = previous && previous.route ? String(previous.route) : ''
      const selectTab = () => { try { uni.$emit('tabs:select', tab) } catch (error) {} }
      // 先把目标 tab 预选好，再回退，避免 tabs 页显示上一屏再滑过去。
      try { uni.$emit('tabs:preselect', tab) } catch (error) {}
      if (previousRoute === 'pages/tabs/tabs') {
        uni.navigateBack({
          delta: 1,
          success: () => setTimeout(selectTab, 220),
          fail: () => { uni.reLaunch({ url: '/pages/tabs/tabs?tab=' + tab }) }
        })
        return
      }
      uni.reLaunch({ url: '/pages/tabs/tabs?tab=' + tab })
    },
  },
}
</script>
