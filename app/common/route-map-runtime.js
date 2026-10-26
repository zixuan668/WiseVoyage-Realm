// DOM-only map renderer shared by H5 and App renderjs. No native map view is
// inserted into scroll-view: the map, SVG paths and labels scroll together.
export const SCENIC_TILES = 'https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}'

export function routeLineStyle(original, active) {
  return { color: original ? '#8b96ac' : active ? '#513dbe' : '#a69acb', weight: active ? 6 : 4,
    opacity: active ? 1 : 0.7, lineCap: 'round', lineJoin: 'round' }
}

export function loadRouteLibrary(win = window, doc = document, assetBase = './static/vendor/leaflet/') {
  if (win.__zhiyouLeafletReady) return Promise.resolve(win.L)
  if (win.__zhiyouLeafletLoading) return win.__zhiyouLeafletLoading
  const pending = new Promise((resolve, reject) => {
    if (!doc.querySelector('link[data-zhiyou-leaflet]')) {
      const css = doc.createElement('link'); css.rel = 'stylesheet'; css.href = assetBase + 'leaflet.css'
      css.dataset.zhiyouLeaflet = 'true'; doc.head.appendChild(css)
    }
    const script = doc.createElement('script'); script.src = assetBase + 'leaflet.js'
    const fail = () => { clearTimeout(timer); script.remove(); reject(new Error('地图资源加载失败，请重试')) }
    const timer = setTimeout(fail, 12000)
    script.onerror = fail
    script.onload = () => {
      if (!win.L) { fail(); return }
      clearTimeout(timer); win.__zhiyouLeafletReady = true; resolve(win.L)
    }
    doc.head.appendChild(script)
  })
  win.__zhiyouLeafletLoading = pending.catch(error => { win.__zhiyouLeafletLoading = null; throw error })
  return win.__zhiyouLeafletLoading
}

export function createRouteMap(element, report = () => {}, win = window, doc = document) {
  let map, group, tiles, resize, removal, payload, boundsKey = '', fitCounter = -1, version = 0, disposed = false, frame = 0
  let tileLoaded = 0, tileErrors = 0, revision = 0
  // Keep map gestures inside the map while Leaflet receives the original events.
  const gestureStart = () => report({ state: 'gesture', active: true })
  const gestureMove = event => { if (event.cancelable) event.preventDefault() }
  const gestureEnd = event => { if (!event.touches?.length) report({ state: 'gesture', active: false }) }
  element.addEventListener('touchstart', gestureStart, { passive: true, capture: true })
  element.addEventListener('touchmove', gestureMove, { passive: false, capture: true })
  element.addEventListener('touchend', gestureEnd, true)
  element.addEventListener('touchcancel', gestureEnd, true)
  const fitAll = () => {
    if (!map || !payload || disposed || !element.isConnected) return
    const points = payload.data.points.map(p => [p.latitude, p.longitude])
    map.stop()
    map.closePopup()
    map.invalidateSize({ pan: false })
    if (points.length) map.fitBounds(win.L.latLngBounds(points), { padding: [28, 28], maxZoom: 17, animate: false })
  }
  const destroy = () => {
    if (disposed) return
    element.removeEventListener('touchstart', gestureStart, true)
    element.removeEventListener('touchmove', gestureMove, true)
    element.removeEventListener('touchend', gestureEnd, true)
    element.removeEventListener('touchcancel', gestureEnd, true)
    report({ state: 'gesture', active: false })
    disposed = true; version++; win.cancelAnimationFrame(frame); resize?.disconnect(); removal?.disconnect(); map?.remove()
    map = group = tiles = null
  }
  // App renderjs does not provide an unmount hook. Observe actual DOM removal
  // as well as explicit H5 teardown to release tile requests and map listeners.
  if (win.MutationObserver) {
    removal = new win.MutationObserver(() => { if (!element.isConnected) destroy() })
    removal.observe(doc.body, { childList: true, subtree: true })
  }
  async function update(next) {
    payload = next; const own = ++version
    if (disposed) return
    try {
      const L = await loadRouteLibrary(win, doc, next.assetBase)
      if (disposed || own !== version || !element.isConnected) return
      if (!map) {
        map = L.map(element, { zoomControl: false, attributionControl: false, scrollWheelZoom: false, zoomAnimation: false, dragging: true, touchZoom: true, bounceAtZoomLimits: false })
        tiles = L.tileLayer(SCENIC_TILES, { maxZoom: 18 }).addTo(map)
        tiles.on('tileload', () => { tileLoaded++; if (!disposed && tileLoaded === 1) report({ state: 'ready' }) })
        tiles.on('tileerror', () => { if (!disposed && ++tileErrors >= 3 && !tileLoaded) report({ state: 'tiles-error' }) })
        group = L.layerGroup().addTo(map)
        if (win.ResizeObserver) { resize = new win.ResizeObserver(() => { win.cancelAnimationFrame(frame); frame = win.requestAnimationFrame(fitAll) }); resize.observe(element) }
      }
      if ((next.revision || 0) !== revision) {
        revision = next.revision || 0; tileLoaded = tileErrors = 0; tiles.redraw()
      }
      group.clearLayers()
      // Render the selected leg last, including before Leaflet's first setView.
      // Shared footpaths must not be painted over by a later muted leg.
      const lines = next.data.polyline.map((line, index) => ({ line, leg: next.data.legIndexes?.[index] ?? index }))
      lines.sort((a, b) => Number(a.leg === next.activeLeg) - Number(b.leg === next.activeLeg))
      lines.forEach(({ line, leg }) => {
        L.polyline(line.points.map(p => [p.latitude, p.longitude]), routeLineStyle(next.original, leg === next.activeLeg))
          .on('click', () => report({ state: 'leg', index: leg })).addTo(group)
      })
      next.data.markers.forEach(marker => {
        const gate = marker.id >= 1000, active = marker.id === next.currentMarker
        const icon = L.divIcon({ className: gate ? 'route-gate-marker' : 'route-order-marker',
          html: '<span class="route-map-pin' + (active ? ' current' : '') + (gate ? ' gate' : '') + '">' + (gate ? '↗' : Number(marker.id)) + '</span>',
          iconSize: [36, 36], iconAnchor: [18, 18] })
        const label = doc.createElement('span'); label.textContent = next.markerLabels[marker.id] || ''
        L.marker([marker.latitude, marker.longitude], { icon, title: label.textContent }).bindPopup(label).addTo(group)
      })
      const key = JSON.stringify([next.data.points, next.data.markers.map(m => m.id), next.original])
      if (key !== boundsKey || next.fitCounter !== fitCounter) { boundsKey = key; fitCounter = next.fitCounter; fitAll() }
      report({ state: 'ready' })
    } catch (error) { if (!disposed && own === version) report({ state: 'error', message: error.message }) }
  }
  return { update, destroy, fitAll }
}
