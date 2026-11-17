<template>
  <!-- App 端内联 <svg> 不渲染，这里用 CSS mask 输出同一套 Lucide 线条图标 -->
  <view class="wander-icon" :style="iconStyle" aria-hidden="true"></view>
</template>

<script>
const paths = {
  route: 'M7 4a2 2 0 1 1-4 0 2 2 0 0 1 4 0Zm0 0h9a4 4 0 0 1 0 8H8a4 4 0 0 0 0 8h9m4 0a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z',
  compass: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0ZM16 8l-2 6-6 2 2-6 6-2Z',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 7v5l3 2',
  gift: 'M3 10h18V6H3v4Zm2 0v10h14V10M12 6v14M12 6H8a2 2 0 1 1 2-2l2 2Zm0 0h4a2 2 0 1 0-2-2l-2 2Z',
  back: 'm15 5-7 7 7 7', next: 'm9 5 7 7-7 7',
  plus: 'M12 5v14M5 12h14', minus: 'M5 12h14',
  up: 'm6 14 6-6 6 6', down: 'm6 10 6 6 6-6',
  sort: 'M5 8h14M5 12h14M5 16h14',
  spark: 'M12 2c0 6-4 10-10 10 6 0 10 4 10 10 0-6 4-10 10-10-6 0-10-4-10-10Z',
  arrow: 'm12 3 7 17-7-4-7 4 7-17Z',
  check: 'm5 12 5 5 9-10',
  flag: 'M5 21V4c5-4 8 4 14 0v10c-6 4-9-4-14 0',
  headphones: 'M3 14v-2a9 9 0 0 1 18 0v2M3 14h4v6H5a2 2 0 0 1-2-2v-4Zm18 0h-4v6h2a2 2 0 0 0 2-2v-4Z',
  pin: 'M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Zm-4 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  leaf: 'M5 20c2-5 6-9 10-12M6 16c-4-6 2-13 13-13 1 10-3 17-10 15',
  walk: 'M14 4a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0ZM8 12l4-5 3 4 4 1m-10 9 2-6 2-4m-1 4 4 2 1 4',
  people: 'M11 7a3 3 0 1 1-6 0 3 3 0 0 1 6 0ZM2 20v-2a5 5 0 0 1 5-5h2a5 5 0 0 1 5 5v2m2-16a3 3 0 0 1 0 6m6 10v-2a5 5 0 0 0-4-5',
  close: 'm6 6 12 12M18 6 6 18',
  cloud: 'M5 18a4 4 0 0 1 0-8 6 6 0 0 1 11-2 5 5 0 0 1 2 10Z',
  camera: 'M3 7h4l2-3h6l2 3h4v13H3V7Zm13 6a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  book: 'M12 6c-3-3-6-3-9-2v15c3-1 6-1 9 2 3-3 6-3 9-2V4c-3-1-6-1-9 2Zm0 0v15',
  heart: 'M12 20 4 12a5 5 0 0 1 8-6 5 5 0 0 1 8 6Z',
  layers: 'm12 3 10 6-10 6L2 9l10-6Zm-9 10 9 5 9-5m-18 4 9 5 9-5',
  pause: 'M9 5v14m6-14v14',
  play: 'm8 5 12 7-12 7Z',
}
export default {
  props: { name: String },
  data: () => ({ paths }),
  computed: {
    iconStyle() {
      const d = this.paths[this.name] || ''
      const svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='" + d + "'/></svg>"
      return { '--wander-icon': 'url("data:image/svg+xml,' + encodeURIComponent(svg) + '")' }
    },
  },
}
</script>

<style scoped>
.wander-icon {
  display: block;
  flex: none;
  width: 20px;
  height: 20px;
  pointer-events: none;
  background-color: currentColor;
  -webkit-mask-image: var(--wander-icon);
  mask-image: var(--wander-icon);
  -webkit-mask-size: contain;
  mask-size: contain;
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
}
</style>
