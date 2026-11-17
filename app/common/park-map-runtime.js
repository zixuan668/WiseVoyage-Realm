import { loadRouteLibrary } from './route-map-runtime.js'
import { wgs84ToGcj02 } from '../../shared/coordinates.js'

const CENTER = [39.9953, 116.2698]
const PARK_BOUNDS = [[39.980, 116.244], [40.008, 116.284]]
const DETAIL_ZOOM = 17
const OVERVIEW_ZOOM = 15

// AMap raster tiles load from the local network without a JS key. They are
// published in GCJ-02, so every WGS-84 point is shifted into that frame before
// it reaches Leaflet; map and data then share one coordinate space.
const AMAP_TILES = 'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}'
const AMAP_ATTRIBUTION = '&copy; 高德地图 AutoNavi'
const gcj = point => wgs84ToGcj02(point[0], point[1])
const gcjPath = path => path.map(gcj)

function toAmap([lat, lng]) {
  const [convertedLat, convertedLng] = wgs84ToGcj02(lat, lng)
  return [convertedLng, convertedLat]
}

function loadAmap(key, serviceHost) {
  if (window.AMap?.Map) return Promise.resolve(window.AMap)
  if (window.__parkAmapPending) return window.__parkAmapPending
  window._AMapSecurityConfig = { serviceHost }
  window.__parkAmapPending = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    const fail = () => {
      clearTimeout(timer)
      script.remove()
      reject(new Error('高德地图加载失败'))
    }
    const timer = setTimeout(fail, 9000)
    script.src = 'https://webapi.amap.com/maps?v=2.0&key=' + encodeURIComponent(key)
    script.onload = () => {
      if (!window.AMap?.Map) { fail(); return }
      clearTimeout(timer)
      resolve(window.AMap)
    }
    script.onerror = fail
    document.head.appendChild(script)
  }).catch(error => {
    window.__parkAmapPending = null
    throw error
  })
  return window.__parkAmapPending
}

function pathStyle(kind, casing = false) {
  if (kind === 'steps') return { color: '#a35138', weight: 4, opacity: .86, dashArray: '6 5' }
  if (kind === 'featured') return casing
    ? { color: '#f7f1ff', weight: 8, opacity: .95 }
    : { color: '#7655bb', weight: 4.5, opacity: .95 }
  return { color: '#2c8276', weight: 5, opacity: .9 }
}

function renderPaths(lines, add) {
  lines.forEach(line => {
    if (line.kind === 'featured') add(line.path, pathStyle(line.kind, true))
    add(line.path, pathStyle(line.kind))
  })
}

function amapAdapter(A, element, report, onView) {
  const map = new A.Map(element, {
    viewMode: '2D', zoom: OVERVIEW_ZOOM, center: toAmap(CENTER), zooms: [12, 19],
    showBuildingBlock: false, mapStyle: 'amap://styles/fresh', dragEnable: false,
    zoomEnable: false, rotateEnable: false,
  })
  let overlays = []
  let timeout
  const ready = new Promise((resolve, reject) => {
    timeout = setTimeout(() => reject(new Error('高德底图未就绪')), 8500)
    map.on('complete', () => { clearTimeout(timeout); report('amap'); resolve() })
  })
  for (const name of ['mapmove', 'moveend', 'zoomchange', 'zoomend']) map.on(name, onView)
  return {
    ready,
    resize: () => map.resize?.(),
    destroy() { clearTimeout(timeout); map.destroy() },
    setGestures(value) { map.setStatus({ dragEnable: value, zoomEnable: value, scrollWheel: value }) },
    project(point) {
      const pixel = map.lngLatToContainer(new A.LngLat(...toAmap(point)))
      return { x: pixel.getX(), y: pixel.getY() }
    },
    overview(points, pads) {
      if (!points.length) { map.setZoomAndCenter(OVERVIEW_ZOOM, toAmap(CENTER), true); return }
      const lats = points.map(point => point[0])
      const lngs = points.map(point => point[1])
      const sw = toAmap([Math.min(...lats), Math.min(...lngs)])
      const ne = toAmap([Math.max(...lats), Math.max(...lngs)])
      map.setBounds(new A.Bounds(sw, ne), true, pads, 16)
    },
    render(lines) {
      if (overlays.length) map.remove(overlays)
      overlays = []
      renderPaths(lines, (path, style) => overlays.push(new A.Polyline({
        path: path.map(toAmap), strokeColor: style.color, strokeWeight: style.weight,
        strokeOpacity: style.opacity, strokeStyle: style.dashArray ? 'dashed' : 'solid', bubble: true,
      })))
      if (overlays.length) map.add(overlays)
    },
    move(action) {
      if (action.type === 'zoom') map.setZoom(map.getZoom() + action.delta)
      if (action.position) map.setZoomAndCenter(DETAIL_ZOOM, toAmap(action.position), true)
    },
  }
}

function leafletAdapter(L, element, report, onView) {
  const map = L.map(element, {
    zoomControl: false, attributionControl: true, scrollWheelZoom: false, dragging: false,
    touchZoom: false, doubleClickZoom: false, maxBounds: PARK_BOUNDS.map(gcj), minZoom: 12, maxZoom: 19,
  }).setView(gcj(CENTER), OVERVIEW_ZOOM)
  map.attributionControl.setPrefix(false)
  const tiles = L.tileLayer(AMAP_TILES, {
    subdomains: '1234', maxZoom: 19, attribution: AMAP_ATTRIBUTION,
  }).addTo(map)
  let loaded = false
  let errors = 0
  tiles.on('tileload', () => { if (!loaded) { loaded = true; report('osm') } })
  tiles.on('tileerror', () => { if (!loaded && ++errors === 3) report('offline') })
  const linesLayer = L.layerGroup().addTo(map)
  map.on('move zoom zoomend', onView)
  return {
    ready: Promise.resolve(),
    resize: () => map.invalidateSize({ pan: false }),
    destroy: () => map.remove(),
    setGestures(value) {
      const method = value ? 'enable' : 'disable'
      for (const mode of ['dragging', 'touchZoom', 'scrollWheelZoom', 'doubleClickZoom']) map[mode]?.[method]()
    },
    project: point => map.latLngToContainerPoint(gcj(point)),
    overview(points, [top, right, bottom, left]) {
      if (!points.length) { map.setView(gcj(CENTER), OVERVIEW_ZOOM); return }
      map.fitBounds(points.map(gcj), { paddingTopLeft: [left, top], paddingBottomRight: [right, bottom],
        animate: false, maxZoom: 16 })
    },
    render(lines) {
      linesLayer.clearLayers()
      renderPaths(lines, (path, style) => L.polyline(gcjPath(path), { ...style, interactive: false }).addTo(linesLayer))
    },
    move(action) {
      if (action.type === 'zoom') map.setZoom(map.getZoom() + action.delta)
      if (action.position) map.setView(gcj(action.position), DETAIL_ZOOM)
    },
  }
}

function overlaps(a, b) {
  return a.x < b.x + b.width + 3 && a.x + a.width + 3 > b.x &&
    a.y < b.y + b.height + 3 && a.y + a.height + 3 > b.y
}

export function placeParkLabels(labels, bounds, obstructions) {
  const used = [...obstructions]
  const placements = new Map()
  for (const label of labels) {
    const { id, x, y, width, height, preferRight } = label
    const right = [x + 7, y - height / 2]
    const left = [x - width - 7, y - height / 2]
    const above = [x - width / 2, y - height - 7]
    const below = [x - width / 2, y + 7]
    const positions = preferRight
      ? [right, [x + 7, y - height], [x + 7, y], above, below, left]
      : [right, left, above, below, [x + 7, y - height], [x - width - 7, y]]
    const box = positions.map(([x, y]) => ({ x, y, width, height })).find(rect =>
      rect.x >= bounds.x && rect.y >= bounds.y &&
      rect.x + width <= bounds.x + bounds.width && rect.y + height <= bounds.y + bounds.height &&
      !used.some(other => overlaps(rect, other)))
    if (box) {
      used.push(box)
      placements.set(id, box)
    }
  }
  return placements
}

function makeLabels(host, choose) {
  let entries = []
  return {
    update(points) {
      host.replaceChildren()
      entries = points.map(point => {
        const label = document.createElement('button')
        label.type = 'button'
        label.className = 'park-pin park-pin-' + point.kind
        label.textContent = point.name
        label.onclick = event => { event.stopPropagation(); choose(point.id) }
        const anchor = document.createElement('span')
        anchor.className = 'park-anchor park-anchor-' + point.kind
        host.append(anchor, label)
        return { point, label, anchor, preferRight: point.name === '德和园' || /^Dehe Garden$/i.test(point.name) }
      })
    },
    layout(project, heading, bounds, blockers) {
      const visible = []
      const parent = host.parentElement
      entries.forEach(({ point, label, anchor, preferRight }) => {
        const { x, y } = project([point.latitude, point.longitude])
        const shown = x >= 0 && y >= 0 && x <= parent.clientWidth && y <= parent.clientHeight
        anchor.style.display = shown ? '' : 'none'
        label.style.visibility = 'hidden'
        if (!shown) return
        anchor.style.left = x + 'px'
        anchor.style.top = y + 'px'
        const isHeading = point.kind === 'location' && Number.isFinite(heading)
        anchor.classList.toggle('park-location-arrow', isHeading)
        anchor.style.setProperty('--park-bearing', (isHeading ? heading : 0) + 'deg')
        visible.push({ id: point.id, x, y, width: label.offsetWidth, height: label.offsetHeight,
          label, preferRight })
      })
      visible.sort((a, b) => Number(b.preferRight) - Number(a.preferRight))
      const anchors = visible.map(({ x, y }) => ({ x: x - 3, y: y - 3, width: 6, height: 6 }))
      const placed = placeParkLabels(visible, bounds, [...blockers, ...anchors])
      visible.forEach(({ id, label }) => {
        const box = placed.get(id)
        if (!box) return
        label.style.left = box.x + 'px'
        label.style.top = box.y + 'px'
        label.style.visibility = 'visible'
      })
    },
  }
}

export function createParkMap(element, notify) {
  // AMap requires a native div. uni-app renders <view> as a custom element on H5.
  const surface = document.createElement('div')
  surface.className = 'park-map-surface'
  surface.style.width = surface.style.height = '100%'
  const labelLayer = document.createElement('div')
  labelLayer.className = 'park-label-layer'
  element.append(surface, labelLayer)
  const labels = makeLabels(labelLayer, id => { if (!disposed) notify({ markerId: id }) })
  let adapter
  let pending
  let latest
  let disposed = false
  let lastCommand
  let linesKey
  let labelsKey
  let interactive
  let overview = true
  let frame
  let resizeTimer
  const status = provider => { if (!disposed) notify({ provider }) }
  const frameElement = element.closest('.park-map-frame')
  const controlSelector = '.park-map-filter-row,.park-weather,.park-map-tools,.park-map-heading,.park-map-sheet,.park-map-footer'

  function layout() {
    if (disposed || !adapter || !latest || latest.pulling || !element.clientHeight) return
    const root = element.closest('.park-home')
    const rect = element.getBoundingClientRect()
    const viewportTop = Math.max(0, (frameElement?.getBoundingClientRect().top ?? rect.top) - rect.top)
    const previewBottom = root?.querySelector('.park-map-reveal')?.getBoundingClientRect().bottom
    const viewportBottom = !latest.expanded && Number.isFinite(previewBottom)
      ? Math.min(rect.height, previewBottom - rect.top) : rect.height
    const obstacles = [...(root?.querySelectorAll(controlSelector) || [])]
      .map(node => {
        const box = node.getBoundingClientRect()
        return { x: box.left - rect.left, y: box.top - rect.top, width: box.width, height: box.height }
      }).filter(box => box.width > 0 && box.height > 0)
    // Keep the lower-left attribution and survey number visible.
    obstacles.push({ x: 0, y: viewportBottom - 23, width: Math.min(220, rect.width), height: 23 })
    labels.layout(adapter.project, latest.heading, {
      x: 8, y: viewportTop + 9, width: Math.max(0, rect.width - 16), height: Math.max(0, viewportBottom - viewportTop - 17),
    }, obstacles)
  }

  function requestLayout() {
    if (!disposed && !frame) frame = requestAnimationFrame(() => { frame = null; layout() })
  }
  function afterMotion(event) {
    if (event.target === frameElement && event.propertyName === 'clip-path') requestLayout()
  }
  frameElement?.addEventListener('transitionend', afterMotion)

  function fitOverview() {
    if (!adapter || !latest || !element.clientHeight) return
    const points = latest.points.filter(point => point.kind === 'scenic')
      .map(point => [point.latitude, point.longitude])
    latest.lines.filter(line => line.kind === 'featured').forEach(line => points.push(...line.path))
    adapter.overview(points, [76, 35, 50, 29])
  }

  const resize = new ResizeObserver(() => {
    adapter?.resize()
    requestLayout()
    clearTimeout(resizeTimer)
    resizeTimer = setTimeout(() => { if (overview && !latest?.pulling) fitOverview(); requestLayout() }, 100)
  })
  resize.observe(element)
  const uiResize = new ResizeObserver(requestLayout)
  function observeControls() {
    uiResize.disconnect()
    element.closest('.park-home')?.querySelectorAll(controlSelector).forEach(node => uiResize.observe(node))
  }
  const removal = new MutationObserver(() => { if (!element.isConnected) destroy() })
  removal.observe(document.body, { childList: true, subtree: true })

  async function open(config) {
    if (config.key && config.serviceHost) {
      try {
        const A = await loadAmap(config.key, config.serviceHost)
        if (disposed) return
        adapter = amapAdapter(A, surface, status, requestLayout)
        await adapter.ready
        return
      } catch (error) {
        console.warn('[park map] Amap fallback', String(error?.message || '').replace(/https?:\/\/\S+/g, '[url]'))
        adapter?.destroy()
        adapter = null
        status('amap-failed')
      }
    }
    const L = await loadRouteLibrary(window, document, config.leafletAssets)
    if (disposed) return
    adapter = leafletAdapter(L, surface, status, requestLayout)
    status('osm-loading')
  }

  function destroy() {
    if (disposed) return
    disposed = true
    resize.disconnect()
    frameElement?.removeEventListener('transitionend', afterMotion)
    uiResize.disconnect()
    removal.disconnect()
    clearTimeout(resizeTimer)
    cancelAnimationFrame(frame)
    adapter?.destroy()
    adapter = null
    surface.remove()
    labelLayer.remove()
  }

  async function update(payload) {
    latest = payload
    if (!pending) pending = open(payload).catch(() => status('unavailable'))
    await pending
    if (disposed || !adapter || latest !== payload) return
    if (interactive !== (payload.expanded && !payload.pulling)) {
      interactive = payload.expanded && !payload.pulling
      adapter.setGestures(interactive)
    }
    if (linesKey !== payload.linesKey) {
      linesKey = payload.linesKey
      adapter.render(payload.lines)
      if (overview) fitOverview()
    }
    if (labelsKey !== payload.labelsKey) {
      labelsKey = payload.labelsKey
      labels.update(payload.points)
      if (overview) fitOverview()
    }
    if (payload.action && lastCommand !== payload.action.id) {
      lastCommand = payload.action.id
      overview = payload.action.type === 'overview'
      if (overview) fitOverview()
      else adapter.move(payload.action)
    }
    observeControls()
    requestLayout()
  }
  return { update, destroy }
}
