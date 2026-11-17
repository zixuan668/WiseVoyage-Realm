<template>
  <view class="welcome-page">
    <ParkWelcome :english="english" @continue="leave" />
  </view>
</template>

<script>
import ParkWelcome from '../../components/ParkWelcome.vue'
import { LOGIN_PROVIDER } from '../../common/config.js'
import { LANGUAGE_STORAGE_KEY } from '../../common/tour-language.js'
import { ONBOARDING_STORAGE_KEY, ONBOARDING_ROUTE, appEntry } from '../../common/onboarding.js'
import { CLAIM_ROUTE, pendingClaim } from '../../common/station-claim.js'

// 每次冷启动先展示「Hi 颐和园」欢迎页，用户上滑/点击后再进入首次引导或主页面。
export default {
  components: { ParkWelcome },
  data() {
    return { english: false, leaving: false }
  },
  onLoad() {
    this.english = uni.getStorageSync(LANGUAGE_STORAGE_KEY) === 'en'
  },
  methods: {
    leave() {
      if (this.leaving) return
      this.leaving = true
      let url
      if (!uni.getStorageSync(ONBOARDING_STORAGE_KEY)) {
        url = '/' + ONBOARDING_ROUTE
      } else if (pendingClaim()) {
        url = CLAIM_ROUTE
      } else {
        url = appEntry(uni, LOGIN_PROVIDER)
      }
      uni.reLaunch({ url })
    },
  },
}
</script>

<style>
.welcome-page { position: fixed; inset: 0; overflow: hidden; background: #182942; }
</style>
