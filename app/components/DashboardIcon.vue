<template>
  <view v-if="mask" class="wander-icon dashboard-icon" :style="{ '--dashboard-mask': mask }" aria-hidden="true"></view>
  <WanderIcon v-else :name="name" />
</template>

<script>
import WanderIcon from './WanderIcon.vue'

const paths = {
  pavilion: 'M12 2v2m-8 5c3-.6 5.4-2.2 8-5 2.6 2.8 5 4.4 8 5M6 9h12L20 13H4L6 9Zm0 4v7m4-7v7m4-7v7m4-7v7M3 20h18',
  itinerary: 'M8 14c0 2-3 5-3 5s-3-3-3-5a3 3 0 1 1 6 0Zm14-8c0 2-3 5-3 5s-3-3-3-5a3 3 0 1 1 6 0ZM8 20h2m2-1 1-1m1-2h2m2-1c1-1 1-2 1-2',
  megaphone: 'M4 9h5l9-5v15l-9-5H4a2 2 0 0 1-2-2v-1a2 2 0 0 1 2-2Zm2 5 2 5h3l-2-5m11-7 2-1m-2 5h3m-3 4 2 1',
  scan: 'M8 4H5a1 1 0 0 0-1 1v3m12-4h3a1 1 0 0 1 1 1v3M4 16v3a1 1 0 0 0 1 1h3m12-4v3a1 1 0 0 1-1 1h-3M4 12h16',
  bell: 'M5 17h14l-2-3v-3a5 5 0 0 0-10 0v3l-2 3Zm5 3a2 2 0 0 0 4 0',
}

export default {
  components: { WanderIcon },
  props: { name: String },
  computed: {
    mask() {
      const path = paths[this.name]
      if (!path) return ''
      const svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path fill='none' stroke='black' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round' d='" + path + "'/></svg>"
      return 'url("data:image/svg+xml,' + encodeURIComponent(svg) + '")'
    },
  },
}
</script>

<style scoped>
.dashboard-icon {
  display: block; flex: none; width: 20px; height: 20px;
  background: currentColor; pointer-events: none;
  -webkit-mask: var(--dashboard-mask) center / contain no-repeat;
  mask: var(--dashboard-mask) center / contain no-repeat;
}
</style>
