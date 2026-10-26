<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { loadScenicMap, SCENIC_TILES } from '@/utils/leaflet'
import { wgs84ToGcj02 } from '../../../shared/coordinates.js'
import type { StationDirections } from '@/api/serviceStation'
import { t, locale } from '@/i18n'
const props = defineProps<{ directions: StationDirections }>()
const host = ref<HTMLElement | null>(null),
  error = ref(false)
let map: any,
  group: any,
  version = 0,
  disposed = false,
  observer: ResizeObserver | undefined
async function draw() {
  const own = ++version
  await nextTick()
  try {
    const L = await loadScenicMap()
    if (disposed || own !== version || !host.value) return
    if (!map) {
      map = L.map(host.value, { attributionControl: false, scrollWheelZoom: false })
      L.tileLayer(SCENIC_TILES, { maxZoom: 18 }).addTo(map)
      group = L.layerGroup().addTo(map)
      observer = new ResizeObserver(() => map?.invalidateSize())
      observer.observe(host.value)
    }
    group.clearLayers()
    const points = props.directions.geometry.map((p) => wgs84ToGcj02(p[0], p[1]))
    if (points.length > 1) {
      L.polyline(points, { color: '#fff', weight: 10, opacity: 0.9 }).addTo(group)
      L.polyline(points, { color: '#4f46e5', weight: 6 }).addTo(group)
    }
    for (const [index, [anchor, label]] of (
      [
        [props.directions.origin, '本站'],
        [
          props.directions.destination,
          locale.value === 'en' && props.directions.destination.label_en
            ? props.directions.destination.label_en
            : props.directions.destination.label
        ]
      ] as const
    ).entries()) {
      const text = document.createElement('strong')
      text.textContent = t(label)
      const letter = index === 0 ? 'A' : 'B'
      const icon = L.divIcon({
        className: 'station-map-endpoint',
        html:
          '<span style="display:grid;place-items:center;width:34px;height:34px;background:' +
          (index === 0 ? '#6366f1' : '#4338ca') +
          ';border:3px solid white;border-radius:50%;box-shadow:0 3px 10px #1e293b33;color:white;font:600 18px var(--app-font-family)">' +
          letter +
          '</span>',
        iconSize: [34, 34],
        iconAnchor: [17, 17]
      })
      L.marker(wgs84ToGcj02(anchor.latitude, anchor.longitude), { icon })
        .bindTooltip(text, { permanent: true, direction: 'top' })
        .addTo(group)
    }
    if (points.length) map.fitBounds(L.latLngBounds(points), { padding: [50, 50], maxZoom: 17 })
    map.invalidateSize()
    error.value = false
  } catch {
    if (own === version) error.value = true
  }
}
watch(() => [props.directions, locale.value], draw, { immediate: true, deep: true })
onBeforeUnmount(() => {
  disposed = true
  version++
  observer?.disconnect()
  map?.remove()
})
</script>
<template>
  <div class="station-directions-map">
    <div ref="host" class="map"></div>
    <p v-if="error" role="alert">
      {{ $t('地图底图暂不可用，请查看下方路线说明') }}
      <button @click="draw">{{ $t('重试') }}</button>
    </p>
  </div>
</template>
<style scoped>
.map {
  height: 330px;
  border-radius: 22px;
  background: #e8eef1;
}
.station-directions-map p {
  font-size: 18px;
  color: #637381;
}
</style>
