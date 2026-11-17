<template>
  <view class="park-map" :map-payload="payload" :change:map-payload="renderer.update">
    <view :id="mapId" class="park-map-canvas" />
  </view>
</template>

<script>
// #ifdef H5
import { createParkMap } from '../common/park-map-runtime.js'
// #endif
export default {
  props: { points: Array, lines: Array, action: Object, expanded: Boolean, pulling: Boolean, heading: Number, obstructions: String },
  emits: ['status', 'marker'],
  data() {
    let leafletAssets = './static/vendor/leaflet/'
    // #ifdef H5
    leafletAssets = (import.meta.env.BASE_URL || '/') + 'static/vendor/leaflet/'
    // #endif
    return { leafletAssets, mapId: 'park-map-' + Math.random().toString(36).slice(2) }
  },
  computed: {
    payload() {
      return {
        mapId: this.mapId,
        leafletAssets: this.leafletAssets,
        key: import.meta.env.VITE_APP_AMAP_KEY || '',
        serviceHost: import.meta.env.VITE_APP_AMAP_SERVICE_HOST || '',
        points: (this.points || []).map(({ id, name, kind, latitude, longitude }) => ({ id, name, kind, latitude, longitude })),
        lines: this.lines || [],
        labelsKey: (this.points || []).map(point => [point.id, point.latitude, point.longitude, point.name].join(':')).join('|'),
        linesKey: JSON.stringify(this.lines),
        expanded: this.expanded,
        pulling: this.pulling,
        heading: this.heading,
        obstructions: this.obstructions,
        action: this.action,
      }
    },
  },
  watch: {
    payload(value) {
      // #ifdef H5
      this._map?.update(value)
      // #endif
    },
  },
  mounted() {
    // #ifdef H5
    this._map = createParkMap(document.getElementById(this.mapId), this.report)
    this._map.update(this.payload)
    // #endif
  },
  beforeUnmount() {
    // #ifdef H5
    this._map?.destroy()
    // #endif
  },
  methods: {
    report(event) {
      if (event.provider) this.$emit('status', event.provider)
      if (event.markerId) this.$emit('marker', event.markerId)
    },
  },
}
</script>

<script module="renderer" lang="renderjs">
import { createParkMap } from '../common/park-map-runtime.js'
export default {
  methods: {
    update(value, oldValue, owner) {
      // #ifdef APP-PLUS
      if (!value) return
      cancelAnimationFrame(this._frame)
      let retries = 0
      const apply = () => {
        const element = document.getElementById(value.mapId)
        if (!element) {
          if (++retries < 8) this._frame = requestAnimationFrame(apply)
          return
        }
        if (this._element !== element) {
          this._map?.destroy()
          this._element = element
          this._map = createParkMap(element, event => owner.callMethod('report', event))
        }
        this._map.update(value)
      }
      apply()
      // #endif
    },
  },
}
</script>

<style scoped>
.park-map, .park-map-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  touch-action: none;
}
.park-map-canvas { background: #e6eeeb; }
.park-map-canvas :deep(.park-label-layer) {
  position: absolute;
  inset: 0;
  z-index: 450;
  overflow: hidden;
  pointer-events: none;
}
.park-map-canvas :deep(.park-pin) {
  position: absolute;
  padding: 3px 6px;
  margin: 0;
  box-sizing: border-box;
  border: 0;
  border-radius: 10px;
  background: rgba(255,255,255,.96);
  box-shadow: 0 1px 6px #47387526;
  color: #372a50;
  font: 400 11px/1.25 'Source Han Park', sans-serif;
  white-space: nowrap;
  pointer-events: auto;
  cursor: pointer;
}
.park-map-canvas :deep(.park-pin-facility) { color: #226d62; }
.park-map-canvas :deep(.park-pin-location) { color: #286dbf; }
.park-map-canvas :deep(.park-anchor) {
  position: absolute;
  width: 8px; height: 8px;
  box-sizing: border-box;
  border-radius: 50%;
  border: 1px solid #fff;
  background: #795bc2;
  transform: translate(-50%,-50%);
}
.park-map-canvas :deep(.park-anchor-facility) { background: #398475; }
.park-map-canvas :deep(.park-anchor-location) {
  width: 14px; height: 14px; border: 2px solid white;
  background: #7055bd; box-shadow: 0 0 0 6px #8164c540;
}
.park-map-canvas :deep(.park-location-arrow) {
  width: 19px; height: 21px; border: 0;
  clip-path: polygon(50% 0%,100% 98%,50% 73%,0% 98%);
  transform: translate(-50%,-50%) rotate(var(--park-bearing));
}
</style>
