<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Close, Headphones, House, More, Pause, Picture, Plus, User, VideoPlay } from '@/icons'
import { createScenicMotion } from '@/utils/scenicMotion'
import { readScenicCatalog, writeScenicCatalog } from '@/utils/scenicCatalogCache'
import RouteStopList from '@/components/scenic-detail/RouteStopList.vue'
import ScenicKnowledgeSections from '@/components/ScenicKnowledgeSections.vue'
import TourJourney from '@/components/scenic-detail/TourJourney.vue'
import ScenicGalleryPanel from '@/components/scenic-detail/ScenicGalleryPanel.vue'
import covers from '@/data/scenicCoverImages.json'
import { getScenicDetail } from '@/data/scenicDetail'

import { request_handler } from '@/api/base'
import { getRouteOverview, type RouteOverviewData } from '@/api/tourExperience'

const motion=createScenicMotion()
let cardNavigation=false
const endpoint = '/tour-experience/scenic-selection'
type Place = {id:number; name:string; description:string; location:string; history:string; tip:string;history_detail?:string;service_facilities?:string;photo_tips?:string;tour_tips?:string;best_season?:string;park?:string}
const catalog = ref<Place[]>(readScenicCatalog<Place>())
const coverMap:Record<string,{url:string}> = covers
const stops = ref<{id:number; name:string}[]>([])
const ready = ref(false)
const catalogError = ref('')
const loadingHintVisible = ref(false)
const loadingHintTimer = setTimeout(() => { loadingHintVisible.value = true }, 180)
const busy = ref(false)
const panel = computed({
  get: () => ['list','plan','catalog','journey'].includes(String(route.query.view)) ? route.query.view as 'list'|'plan'|'catalog'|'journey' : null,
  set: value => { void router.push({query:{...route.query,view:value || undefined}}) }
})
const overview = ref<RouteOverviewData|null>(null)
const endArea = ref<'auto'|'east'|'north'|'south'>('auto')
const startArea = ref<'auto'|'east'|'north'|'south'>('auto')
const fewSteps = ref(false)
const exitPickerOpen = ref(false)
const exits = [{value:'auto',label:'任意'},{value:'east',label:'东宫门'},{value:'north',label:'北宫门'},{value:'south',label:'新建宫门'}] as const
function chooseExit(value:typeof endArea.value) {if(busy.value)return;exitPickerOpen.value=false;void saveSettings({end_area:value})}
const routeHasMore = ref(false)
function onRouteScroll(event: Event) {
  const el = event.target as HTMLElement
  routeHasMore.value = el.scrollHeight - el.scrollTop - el.clientHeight > 24
}
function scrollRouteMore() {
  const el = document.querySelector('.route-body') as HTMLElement | null
  el?.scrollBy({ top: el.clientHeight * 0.7, behavior: 'smooth' })
}
function updateRouteMore() {
  void nextTick(() => {
    const el = document.querySelector('.route-body') as HTMLElement | null
    if (el) routeHasMore.value = el.scrollHeight - el.scrollTop - el.clientHeight > 24
  })
}
const routeIssues = computed(() => {
  const data = overview.value as any
  if (!data) return [] as string[]
  const issues: string[] = []
  for (const leg of data.legs || []) {
    if (leg.available === false) issues.push(leg.from_name + ' → ' + leg.to_name + '：没有可用的无台阶步行路线')
  }
  if (data.exit_leg && data.exit_leg.available === false) {
    issues.push(data.exit_leg.from_name + ' → ' + (data.exit_anchor?.label || '离园出口') + '：出园段没有可用的无台阶路线')
  }
  if (data.entry_leg && data.entry_leg.available === false) {
    issues.push((data.entry_anchor?.label || '入口') + ' → ' + data.entry_leg.to_name + '：入园段没有可用的无台阶路线')
  }
  return issues
})
const elderly=ref(false), children=ref(false)
const accessibility=computed(()=>fewSteps.value||elderly.value||children.value)
async function saveSettings(value:{spot_ids?:number[];elderly?:boolean;children?:boolean;end_area?:typeof endArea.value}){
  if(busy.value)return
  busy.value=true
  try{
    const data=(await request_handler.put('/tour-experience/scenic-settings',value)).data
    elderly.value=data.elderly;children.value=data.children
    fewSteps.value=!!data.few_steps
    startArea.value=data.start_area || 'auto';endArea.value=data.end_area || 'auto'
    if(value.spot_ids){
      const byId=new Map(stops.value.map(s=>[s.id,s]))
      stops.value=value.spot_ids.map(id=>byId.get(id)).filter(Boolean) as {id:number;name:string}[]
    }
    // 拖动排序/勾选老人小孩只在本地更新，不重新拉清单，避免整页白一下
    await loadPlan(true)
  }catch{notify('设置保存失败，请重试')}
  finally{busy.value=false}
}
async function removePlannedStop(id:number){
  await changeStop(id)
  if(panel.value==='plan')await loadPlan()
}
const planError = ref('')
const planAttempted = ref(false)
async function applyRequestedSpots(currentList: {id:number}[]) {
  // The App hands a picked route over as spot ids. The draft lives in this
  // webview's session cookie, so sync the stops first (add/remove) and only then
  // save the order; saving settings alone fails when the selection is not there.
  const requested = String(route.query.spotIds || '')
  if (!requested || String(route.query.spotIdsApplied || '') === '1') return false
  const ids = requested.split(',').map(Number).filter(id => Number.isInteger(id) && id > 0).slice(0, 20)
  if (!ids.length || new Set(ids).size !== ids.length) return false
  {
    const currentIds = new Set(currentList.map(item => item.id))
    for (const id of ids) if (!currentIds.has(id)) await request_handler.put(endpoint, null, { params: { spot_id: id } })
    for (const id of currentIds) if (!ids.includes(id)) await request_handler.delete(endpoint + '/' + id)
    const area = (value: unknown) => ['auto','east','north','south'].includes(String(value)) ? String(value) : 'auto'
    await request_handler.put('/tour-experience/scenic-settings', {
      spot_ids: ids,
      ...(route.query.elderly !== undefined ? {elderly: route.query.elderly === '1'} : {}),
      ...(route.query.children !== undefined ? {children: route.query.children === '1'} : {}),
      ...(route.query.avoidSteps !== undefined ? {avoid_steps: route.query.avoidSteps === '1'} : {}),
      ...(route.query.startArea !== undefined ? {start_area: area(route.query.startArea)} : {}),
      ...(route.query.endArea !== undefined ? {end_area: area(route.query.endArea)} : {}),
    })
  }
  {
    // Apply the handoff only once; reloads keep this session's selection.
    void router.replace({ query: { ...route.query, spotIds: undefined, spotIdsApplied: '1' } })
  }
  return true
}
async function refresh() {
  catalogError.value = ''
  // Public scenery can render independently of the visitor's route draft.
  const catalogRequest = request_handler.get<Place[]>('/tour-experience/scenic-catalog').then(places => {
    if (!Array.isArray(places.data)) throw Error('景点接口不可用')
    catalog.value = places.data.filter((place: Place) => place.park === 'summer-palace')
    writeScenicCatalog(catalog.value)
    for (const place of catalog.value) {
      const cover = coverMap[place.name]?.url
      if (cover) { const image = new Image(); image.src = cover }
    }
  })
  const draftRequest = (async () => {
    // The first response establishes the HttpOnly draft cookie for settings.
    const list = await request_handler.get(endpoint)
    if (!Array.isArray(list.data)) throw Error('行程接口不可用')
    stops.value = list.data
    const applied = await applyRequestedSpots(list.data)
    if (applied) {
      const synced = await request_handler.get(endpoint)
      if (Array.isArray(synced.data)) stops.value = synced.data
    }
    const settings = (await request_handler.get<{elderly?:boolean;children?:boolean;few_steps?:boolean;start_area?:typeof startArea.value;end_area?:typeof endArea.value}>('/tour-experience/scenic-settings')).data
    elderly.value = !!settings.elderly; children.value = !!settings.children
    fewSteps.value = !!settings.few_steps
    startArea.value = settings.start_area || 'auto'; endArea.value = settings.end_area || 'auto'
  })()
  await Promise.all([catalogRequest, draftRequest])
  ready.value = true
}
async function changeStop(id?: number) {
  if (busy.value) return
  busy.value = true
  menuOpen.value = false
  try {
    if (!ready.value) await refresh()
    if (id === undefined) await request_handler.put(endpoint, null, {params:{spot_id:current.value?.id}})
    else await request_handler.delete(endpoint + '/' + id)
    await refresh()
    if(id===undefined){
      const selected=document.querySelector<HTMLElement>('.spot-strip button[aria-current=true]') || document.querySelector<HTMLElement>('.intro__title')
      motion.flight(selected,document.querySelector<HTMLElement>('.topbar__actions .tool'))
    }
  } catch { notify('景点清单更新失败，请重试') }
  finally { busy.value = false }
}
let planVersion=0
let planRetries=0
async function loadPlan(skipRefresh=false) {
  const own=++planVersion
  busy.value = true
  planAttempted.value = false
  planError.value = ''
  try {
    if(!skipRefresh) await refresh()
    if (!stops.value.length) {overview.value=null;return}
    const result = (await getRouteOverview(stops.value.map(s => s.id), accessibility.value?'relaxed':'standard', undefined, {
      start_area: startArea.value, end_area: endArea.value, avoid_steps:accessibility.value
    })).data.data
    if(own===planVersion){planRetries=0;overview.value=result;updateRouteMore()}
  } catch (error) {
    if(own!==planVersion)return
    // The App injects its auth token into the webview right after load; the
    // first plan request can race it, so retry once before showing the error.
    if(planRetries<3){planRetries++;overview.value=null;const delay=700*planRetries;setTimeout(()=>{if(panel.value==='plan')void loadPlan()},delay);return}
    overview.value=null
    planAttempted.value = true
    planError.value = error instanceof Error ? error.message : String(error)
    notify('路线加载失败，请重试')
  }
  finally { if(own===planVersion)busy.value = false }
}
const metersText = computed(() => {
  const meters = overview.value?.walking_meters
  if (meters == null) return '—'
  return meters >= 1000 ? (meters / 1000).toFixed(1) + ' km' : meters + ' m'
})
const mapData = computed(() => {
  const data = overview.value
  if (!data) return null
  const segments: Array<Array<[number, number]>> = []
  const all: Array<[number, number]> = []
  for (const leg of data.legs) {
    const points = (leg.geometry || []).map(([lat, lng]) => [lng, lat] as [number, number])
    if (points.length) { segments.push(points); all.push(...points) }
  }
  for (const stop of data.stops) {
    if (stop.latitude != null && stop.longitude != null) all.push([stop.longitude, stop.latitude])
  }
  if (!all.length) return null
  const width = 340, height = 190, pad = 26
  const xs = all.map(p => p[0]), ys = all.map(p => p[1])
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys)
  const scale = Math.min(
    (width - pad * 2) / Math.max(maxX - minX, 1e-6),
    (height - pad * 2) / Math.max(maxY - minY, 1e-6)
  )
  const offsetX = (width - (maxX - minX) * scale) / 2
  const offsetY = (height - (maxY - minY) * scale) / 2
  const px = (lng: number) => offsetX + (lng - minX) * scale
  const py = (lat: number) => height - offsetY - (lat - minY) * scale
  return {
    width,
    height,
    paths: segments.map(points => points.map(([lng, lat], index) =>
      (index ? 'L' : 'M') + px(lng).toFixed(1) + ' ' + py(lat).toFixed(1)
    ).join(' ')),
    stops: data.stops.filter(s => s.latitude != null && s.longitude != null)
      .map((s, index) => ({ id: s.spot_id, x: px(s.longitude!), y: py(s.latitude!), index: index + 1 }))
  }
})
const routeMapEl = ref<HTMLElement | null>(null)
let routeMap: any = null
let routeLayer: any = null
let routeMapSeq = 0
async function drawRouteMap() {
  const own = ++routeMapSeq
  await nextTick()
  const data = overview.value
  if (!routeMapEl.value || !data) return
  try {
    const leafletUtil = await import('@/utils/leaflet')
    const coordinates = await import('../../../../shared/coordinates.js')
    const L = await leafletUtil.loadScenicMap()
    const toGcj = (lat: number, lng: number) => { const [gLat, gLng] = coordinates.wgs84ToGcj02(lat, lng); return [gLat, gLng] as [number, number] }
    if (own !== routeMapSeq || !routeMapEl.value) return
    if (!routeMap || routeMap.getContainer() !== routeMapEl.value) {
      routeMap?.remove()
      routeMap = L.map(routeMapEl.value, { zoomControl: false, attributionControl: false, scrollWheelZoom: false })
      // 国内网络用高德瓦片；geometry 是 WGS84，显示前转 GCJ02 避免整体偏移
      L.tileLayer(leafletUtil.SCENIC_TILES, { maxZoom: 19 }).addTo(routeMap)
      routeLayer = L.layerGroup().addTo(routeMap)
    }
    routeLayer.clearLayers()
    const points: Array<[number, number]> = []
    for (const leg of data.legs) {
      const geometry = (leg.geometry || []).map(([lat, lng]: number[]) => toGcj(lat, lng))
      if (geometry.length) {
        L.polyline(geometry, { color: '#fff', weight: 9, opacity: 0.9 }).addTo(routeLayer)
        L.polyline(geometry, { color: '#5a78f0', weight: 5 }).addTo(routeLayer)
        points.push(...geometry)
      }
    }
    const boundsPoints: Array<[number, number]> = []
    data.stops.forEach((stop, index) => {
      const lat=stop.access_latitude ?? stop.latitude, lng=stop.access_longitude ?? stop.longitude
      if (lat == null || lng == null) return
      const position: [number, number] = toGcj(lat, lng)
      points.push(position)
      boundsPoints.push(position)
      const icon = L.divIcon({
        className: 'route-order-marker',
        html: '<span style="display:grid;place-items:center;width:30px;height:30px;border-radius:50%;border:3px solid white;background:#6652bd;color:white;font:600 18px var(--app-font-family)">' + (index + 1) + '</span>',
        iconSize: [36, 36],
        iconAnchor: [18, 18]
      })
      const label=document.createElement('span')
      label.textContent=stop.spot_name+' · 步行接入点'
      L.marker(position, { icon, title:stop.spot_name }).bindPopup(label).addTo(routeLayer)
    })
    for (const anchor of [data.entry_anchor, data.exit_anchor]) {
      if (anchor?.latitude != null && anchor?.longitude != null) boundsPoints.push(toGcj(anchor.latitude, anchor.longitude))
    }
    // 视野只按景点/出入口固定，不随无障碍路线是否缺失而缩放
    if (boundsPoints.length > 1) routeMap.fitBounds(L.latLngBounds(boundsPoints), { padding: [48, 48], maxZoom: 16 })
    else if (boundsPoints.length === 1) routeMap.setView(boundsPoints[0], 16)
    setTimeout(() => routeMap?.invalidateSize(), 80)
  } catch {
    /* 地图底图不可用时保持空白，不影响下方路线数据 */
  }
}
const journeyView = ref<InstanceType<typeof TourJourney>|null>(null)
const journeyTitle = ref('选择伴游')
function startTour() {
  if (!stops.value.length || !overview.value) return
  stopAudio()
  panel.value='journey'
}
onMounted(async () => {
  // Direct entry with view=plan (App 首页主题路线) never flips the panel watch.
  // Show the loading state from the first paint so the empty/error panel never flashes.
  if (panel.value === 'plan') busy.value = true
  try {
    await refresh()
    if (panel.value === 'plan') await loadPlan(true)
    else busy.value = false
  } catch {
    busy.value = false
    // 失败只显示错误入口，绝不显示与当前请求无关的默认景点。
    if (!catalog.value.length) catalogError.value = '景点加载失败，请重试'
    if (panel.value === 'plan') {
      planAttempted.value = true
      planError.value = '无法读取景点或行程条件，请重试'
    }
    notify('景点清单加载失败')
  }
})
type Scene = 'intro' | 'gallery'

const route = useRoute()
const router = useRouter()
// 进入本页时带的面板：App 用 view= 直接打开的，返回要回 App 上一页，而不是先退回景点介绍。
const entryView = String(route.query.view || '')
const bridge = getScenicDetail()
const current = computed(() => catalog.value.find(p => String(p.id) === String(route.params.spotId) || coverMap[p.name]?.url.split('/').pop()?.replace('.jpg','') === route.params.spotId) ?? catalog.value[0])
const spot = computed(() => {
  const p = current.value
  if (!p) return {spotId:'',name:'',nameEn:'',tagline:'',intro:[],facts:[],tip:'',hero:{src:'',position:'center'},gallery:[],audio:{title:'',seconds:0,script:''}}
  const src = coverMap[p.name]?.url || ''
  return {...bridge,name:p.name,tagline:p.location,intro:[p.description,p.history].filter(Boolean),facts:[],tip:p.tip,
    hero:{src,position:'center'},gallery: p.name===bridge.name ? bridge.gallery : src ? [{id:String(p.id),src,caption:p.name,note:p.location}] : [],
    audio:{...bridge.audio,title:p.name,script:p.description}}
})
const galleryPhotos = computed(() => {
  if (!catalog.value.length) return []
  return catalog.value.map(p => ({
    id: String(p.id),
    src: coverMap[p.name]?.url || '',
    caption: p.name,
    note: p.location || ''
  }))
})
function choosePlace(id:number,event?:MouseEvent) {
  const source=panel.value==='catalog' ? event?.currentTarget as HTMLElement|undefined : undefined
  if(source){cardNavigation=true;motion.photo(source,()=>document.querySelector<HTMLElement>('.intro__hero'))}
  const previous = currentIndex.value
  introOpen.value=false
  stopAudio()
  void router.replace({name:'AppScenicDetail',params:{spotId:String(id)}}).finally(()=>{cardNavigation=false})
  slideDirection.value = catalog.value.findIndex(p=>p.id===id) >= previous ? 'next' : 'previous'
}

const currentIndex = computed(() => catalog.value.findIndex(p => p.id === current.value?.id))
// 缩略条固定 4 个景点 + 1 个「全部景点」入口，5 个格子等宽；
// 取当前景点所在的 4 个连续景点，避免出现上一项被裁掉一半的残影。
const visibleSpots = computed(() => {
  const total = catalog.value.length
  if (!total) return []
  const index = currentIndex.value < 0 ? 0 : currentIndex.value
  const start = Math.max(0, Math.min(index - 3, total - 4))
  return catalog.value.slice(start, start + 4)
})
const added = computed(() => !!current.value && stops.value.some(s => s.id === current.value!.id))
// 底部固定 4 个点：前 4 个景点依次点亮，第 4 个之后选中态停在最后一个点不动；
// 往回滑到第 3 个景点时，选中态才从第 4 个切回第 3 个。
const DOT_COUNT = 4
const dotActive = computed(() => Math.min(Math.max(currentIndex.value, 0), DOT_COUNT - 1))
const slideDirection = ref('next')
const scene = ref<Scene>(route.query.page === '07' ? 'gallery' : 'intro')
const isAppWebview = ref(false)
watch(panel, async (value,previous) => {
  if(value==='plan' && previous!=='journey'){
    void loadPlan()
    void nextTick(()=>{const el=document.querySelector('.route-body') as HTMLElement|null;if(el)el.scrollTop=0})
  }
  // 规划页 ↔ 选择伴游：保留规划页在底层做视差，伴游页从右侧滑入/滑出，避免闪一下。
  if(value==='journey' || previous==='journey'){
    motion.cancel()
    if(value==='journey')void nextTick(()=>{const el=document.querySelector('.journey') as HTMLElement|null;if(el)el.scrollTop=0})
    return
  }
  if(cardNavigation)return
  const old=motion.snapshot(document.querySelector<HTMLElement>('.phone .selection-panel:not([data-motion-snapshot])'))
  await nextTick()
  const target=value?document.querySelector<HTMLElement>('.phone .selection-panel:not([data-motion-snapshot])'):document.querySelector<HTMLElement>('.intro__sheet')
  motion.enter(target,old,!value || previous==='list')
  if(!value)motion.play(document.querySelector<HTMLElement>('.intro__hero')!,[{transform:'translateX(-10px)'},{transform:'translateX(0)'}])
})
watch([panel, overview], () => {
  if (panel.value === 'plan' && overview.value) void drawRouteMap()
})
const viewerOpen = ref(false)
const introOpen = ref(false)
watch(introOpen, async () => {
  if(!cardNavigation)motion.cancel()
  await nextTick()
  contentEl.value?.scrollTo({top:0,behavior:'instant'})
})
const menuOpen = ref(false)
const contentEl = ref<HTMLElement | null>(null)

const toast = ref('')
let toastTimer: ReturnType<typeof setTimeout> | undefined
function notify(message: string) {
  toast.value = message
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2200)
}

// 06 / 07 两个设计页状态与 URL 保持同步，手机可直接分享 / 收藏某一页。
function syncScene(next: Scene) {
  scene.value = next
  const page = next === 'gallery' ? '07' : '06'
  if (route.query.page !== page) void router.replace({ query: { ...route.query, page } })
}
function openGallery() {
  menuOpen.value = false
  introOpen.value = true
  syncScene('gallery')
}

watch(scene, next => {
  if (next === 'intro') viewerOpen.value = false
})
watch(
  () => route.query.page,
  value => {
    const next: Scene = value === '07' ? 'gallery' : 'intro'
    if (scene.value !== next) scene.value = next
    // 回到正常景点页时保持“未展开的介绍”状态
    if (next === 'intro') introOpen.value = false
  }
)

/* ---------- 下拉收起 / 上滑展开介绍 ---------- */
let dragging = false
let dragStartY = 0
let dragStartX = 0
let dragDeltaX = 0
let dragDeltaY = 0
function onPointerDown(event: PointerEvent) {
  if (scene.value !== 'intro' || panel.value) return
  if ((event.target as HTMLElement | null)?.closest('button')) return
  if ((contentEl.value?.scrollTop ?? 0) > 0) return
  dragging = true
  dragStartY = event.clientY
  dragStartX = event.clientX
  dragDeltaX = 0
  dragDeltaY = 0
  ;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId)
}
function onPointerMove(event: PointerEvent) {
  if (!dragging) return
  dragDeltaX = event.clientX - dragStartX
  dragDeltaY = event.clientY - dragStartY
}
function onPointerEnd() {
  if (!dragging) return
  dragging = false
  if (Math.abs(dragDeltaX) > 50 && Math.abs(dragDeltaX) > Math.abs(dragDeltaY) * 1.3) {
    const index = catalog.value.findIndex(p => p.id === current.value?.id)
    const next = index + (dragDeltaX < 0 ? 1 : -1)
    if (index >= 0 && next >= 0 && next < catalog.value.length) choosePlace(catalog.value[next]!.id)
  }
  if (Math.abs(dragDeltaY) > Math.abs(dragDeltaX)) {
    if (dragDeltaY < -45) introOpen.value = true
    if (dragDeltaY > 84) introOpen.value = false
  }
}
function onWheel(event: WheelEvent) {
  if (!introOpen.value || scene.value !== 'intro') return
  if ((contentEl.value?.scrollTop ?? 0) > 0) return
  if (event.deltaY < -48) introOpen.value = false
}
/* 触摸上滑展开：pointer 事件在移动端会被浏览器滚动取消，改用 touch 事件判定 */
let touchStartX = 0
let touchStartY = 0
let touchLastY = 0
let touchStartScrollTop = 0
let touching = false
function onTouchStart(event: TouchEvent) {
  if (scene.value !== 'intro' || panel.value) return
  if ((event.target as HTMLElement | null)?.closest('.topbar, .menu, .audio, .selection-panel')) return
  const scrollTop = contentEl.value?.scrollTop ?? 0
  // 收起态：任意位置可上滑展开；展开态：只在介绍顶部时允许下滑收起
  if (introOpen.value && scrollTop > 0) return
  const t = event.touches[0]
  if (!t) return
  touching = true
  touchStartX = t.clientX
  touchStartY = t.clientY
  touchLastY = t.clientY
  touchStartScrollTop = scrollTop
}
function onTouchMove(event: TouchEvent) {
  if (!touching || !event.touches[0]) return
  const t = event.touches[0]
  touchLastY = t.clientY
  const dy = t.clientY - touchStartY
  const dx = t.clientX - touchStartX
  if (Math.abs(dy) <= Math.abs(dx) || Math.abs(dy) < 10) return
  if (!introOpen.value && dy < 0) event.preventDefault()
  if (introOpen.value && dy > 0 && touchStartScrollTop <= 0) event.preventDefault()
}
function cancelGesture() {
  dragging=false
  touching=false
}
function onTouchEnd() {
  if (!touching) return
  touching = false
  const dy = touchLastY - touchStartY
  if (!introOpen.value && dy < -44) introOpen.value = true
  else if (introOpen.value && dy > 60 && touchStartScrollTop <= 0) introOpen.value = false
}
function toggleIntro() {
  introOpen.value = !introOpen.value
  if (introOpen.value) contentEl.value?.scrollTo({ top: 0 })
}

/* ---------- 听景点：播放后端保存的真实录音 ---------- */
const audioOpen = ref(false)
const audioPlaying = ref(false)
const audioLoading = ref(false)
const elapsed = ref(0)
const duration = ref(0)
const audioPercent = computed(() => duration.value > 0 ? Math.min(100, elapsed.value / duration.value * 100) : 0)
let audio: HTMLAudioElement | null = null
let audioVersion = 0
async function playAudio() {
  if (!audio) return
  try { await audio.play() }
  catch { notify('音频播放失败，请点击重试') }
}
function pauseAudio() { audio?.pause() }
function stopAudio() {
  audioVersion++
  audioOpen.value = false
  audioLoading.value = false
  audioPlaying.value = false
  elapsed.value = 0
  duration.value = 0
  if (audio) {
    audio.onplay = audio.onpause = audio.onended = audio.ontimeupdate = audio.onloadedmetadata = audio.ondurationchange = audio.onerror = null
    audio.pause()
    audio.removeAttribute('src')
    audio.load()
    audio = null
  }
}
async function toggleAudio() {
  menuOpen.value = false
  if (audioOpen.value) { stopAudio(); return }
  const id = current.value?.id
  if (!id) return
  audioOpen.value = true
  audioLoading.value = true
  const own = ++audioVersion
  // Create the element during the user gesture for mobile WebViews.
  const player = new Audio()
  audio = player
  try {
    const { data } = await request_handler.get<{url:string;duration:number}>('/tour-experience/scenic-audio/' + id)
    if (own !== audioVersion) return
    player.onplay = () => { audioPlaying.value = true }
    player.onpause = player.onended = () => { audioPlaying.value = false }
    player.ontimeupdate = () => { elapsed.value = Math.floor(player.currentTime) }
    const updateDuration = () => { if (Number.isFinite(player.duration)) duration.value = player.duration }
    player.onloadedmetadata = player.ondurationchange = updateDuration
    player.onerror = () => { audioPlaying.value = false; notify('音频加载失败，请关闭后重试') }
    duration.value = data.duration
    player.src = data.url
    await playAudio()
  } catch (error: any) {
    if (own === audioVersion) {
      stopAudio()
      notify(error?.response?.data?.detail || '讲解加载失败，请稍后重试')
    }
  } finally { if (own === audioVersion) audioLoading.value = false }
}
function togglePlay() {
  if (audioLoading.value) return
  if (audioPlaying.value) pauseAudio()
  else void playAudio()
}
watch(() => current.value?.id, () => stopAudio())


// 退出景点 WebView：交给 App 统一回首页（App 的 scenic 页面把 scenic-back 处理为回首页）。
function exitToApp() {
  const app = window as unknown as {
    plus?: { webview?: { currentWebview?: () => { close?: () => void } } }
    uni?: {
      navigateBack?: (options: { delta: number }) => void
      postMessage?: (options: { data: unknown }) => void
    }
  }
  const inApp = !!app.plus || /Html5Plus/i.test(navigator.userAgent)
  if (inApp) {
    // 先请 App 处理（App 会把 scenic-back 统一落到首页）。
    try {
      if (typeof app.uni?.postMessage === 'function') app.uni.postMessage({ data: { type: 'scenic-back' } })
    } catch (error) {}
    // App 偶尔收不到 web-view 消息，返回键会像没反应：稍等仍停在本页就直接用 SDK 关掉页面。
    setTimeout(() => {
      if (document.visibilityState === 'hidden') return
      try {
        if (typeof app.uni?.navigateBack === 'function') { app.uni.navigateBack({ delta: 1 }); return }
      } catch (error) {}
      try {
        const child = app.plus?.webview?.currentWebview?.()
        if (child && typeof child.close === 'function') child.close()
      } catch (error) {}
    }, 400)
    // 两条通道都没生效时给个明确提示，不再出现点了没反应的返回键。
    setTimeout(() => {
      if (document.visibilityState !== 'hidden') notify('返回失败，请用手机返回键')
    }, 1500)
    return true
  }
  if (router.options.history.state.back) { void router.back(); return true }
  // A full-page entry has browser history but no Vue Router `back` state.
  if (window.history.length > 1) { window.history.back(); return true }
  return false
}

function goBack() {
  if (panel.value) {
    // App 带 view= 直接打开的面板（如首页主题路线 → 规划页）：返回打开它的 App 页面。
    if (panel.value === entryView) {
      if (exitToApp()) return
      panel.value = null
      return
    }
    // 站内自己点开的面板（如景点介绍 → 去规划）：退回上一视图。
    if (panel.value==='journey') {journeyView.value?.back();return}
    if (panel.value === 'list') { panel.value = stops.value.length ? 'plan' : null; return }
    panel.value = null
    return
  }
  if (scene.value === 'gallery') {
    syncScene('intro')
    return
  }
  if (exitToApp()) return
  notify('请从 App 首页进入景点详情')
}
// 部分旧版移动端浏览器不支持 :has()，用显式类名兜底手机页的最小宽度设置。
onMounted(() => {
  window.scrollTo(0, 0)
  document.documentElement.classList.add('is-scenic-app-page')
  document.body.classList.add('is-scenic-app-page')
  const appHost = window as unknown as { plus?: unknown }
  if (route.query.app === '1' || appHost.plus || /Html5Plus/i.test(navigator.userAgent)) {
    isAppWebview.value = true
    document.documentElement.classList.add('is-app-webview')
  }
})
function openAppTab(tab: 'home' | 'ai' | 'mine') {
  try {
    const host = window as any
    if (typeof host.uni?.postMessage === 'function') { host.uni.postMessage({ data: { type: 'app-tab', tab } }); return }
    host.plus?.webview?.postMessageToUniNView?.({ type: 'app-tab', tab }, 'app')
  } catch {}
}
onBeforeUnmount(() => {
  clearTimeout(loadingHintTimer)
  motion.cancel()
  document.documentElement.classList.remove('is-scenic-app-page')
  document.body.classList.remove('is-scenic-app-page')
  document.documentElement.classList.remove('is-app-webview')
  stopAudio()
  if (toastTimer) clearTimeout(toastTimer)
  routeMap?.remove()
  routeMap = null
})
</script>

<template>
  <div class="scenic-app" :class="{ 'has-app-dock': isAppWebview }">
    <div class="stage">


      <section class="phone" :class="{ 'is-viewing': viewerOpen, 'is-ready': !!current }" aria-label="智游知境 App · 景点详情模块">
        <div v-if="!current && loadingHintVisible && !panel && !catalogError" class="scenic-skeleton" aria-busy="true" aria-label="景点加载中">
          <div class="sk sk-hero"></div>
          <div class="sk-strip"><div v-for="n in 4" :key="n" class="sk sk-thumb"></div></div>
          <div class="sk sk-title"></div>
          <div class="sk sk-line w90"></div>
          <div class="sk sk-line w80"></div>
          <div class="sk sk-line w60"></div>
        </div>
        <div v-if="catalogError && !panel" class="scenic-load-error" role="alert">
          <p>{{ catalogError }}</p><button @click="refresh().catch(() => { catalogError = '景点加载失败，请重试' })">重新加载</button>
        </div>
        <!-- ===== 06 景点介绍展开 ===== -->
        <div
          class="intro"
          :class="{
            'is-expanded': introOpen,
            'is-collapsed': !introOpen
          }"
          @pointerdown="onPointerDown"
          @pointermove="onPointerMove"
          @pointerup="onPointerEnd"
          @pointercancel="cancelGesture"
          @wheel="onWheel"
          @touchstart="onTouchStart"
          @touchmove="onTouchMove"
          @touchend="onTouchEnd"
          @touchcancel="cancelGesture"
        >
          <div v-if="current" class="intro__hero" role="img" :aria-label="spot.name">
            <Transition name="hero-fade">
              <div :key="current?.id" class="intro__hero__media" :style="{ backgroundImage: 'url(' + spot.hero.src + ')', backgroundPosition: spot.hero.position }"></div>
            </Transition>
          </div>
          <div v-if="current" class="intro__veil"></div>

          <header class="topbar">
            <button class="topbar__back" aria-label="返回" @click="goBack">
              <ArrowLeft :size="20" />
            </button>
            <span v-if="panel==='journey'" class="journey-nav-title">{{journeyTitle}}</span>
            <button v-if="panel==='plan' && overview" class="topbar-start" :disabled="busy || !overview.complete" @click="startTour">
              <VideoPlay :size="17" aria-hidden="true" />
              <span>开始导览</span>
            </button>
            <div v-if="panel!=='journey' && panel!=='plan'" class="topbar__actions">
              <button class="tool" :class="{ 'is-on': menuOpen }" aria-label="更多操作" :aria-expanded="menuOpen" @click="menuOpen = !menuOpen">
                <More :size="21" />
              </button>
            </div>
          </header>

          <Transition name="pop">
            <div v-if="menuOpen" class="menu">
              <button class="menu__item" :disabled="!current || busy" @click="changeStop(added ? current?.id : undefined)">
                <Plus :size="20" />
                <span>{{ added ? '已加入路线' : '加入路线' }}</span>
              </button>
              <button class="menu__item" @click="toggleAudio"><Headphones :size="20" /><span>听景点</span></button>
            </div>
          </Transition>
          <div v-if="menuOpen" class="menu__scrim" @click="menuOpen = false"></div>

          <div v-if="current" class="intro__sheet">
            <div v-if="introOpen" class="intro-expand-surface" aria-hidden="true"></div>
            <div ref="contentEl" class="intro__scroll">
              <div class="intro__stack">
                <nav v-if="ready && !introOpen" class="spot-strip" aria-label="切换景点">
                  <button v-for="p in visibleSpots" :key="p.id" :aria-label="p.name" :aria-current="p.id===current?.id" @click="choosePlace(p.id,$event)">
                    <img v-if="coverMap[p.name]" :src="coverMap[p.name].url" alt=""><span>{{ p.name }}</span>
                  </button>
                  <button class="all-spots" aria-label="全部景点" @click="panel='catalog'"><More :size="20"/></button>
                </nav>
                
                <h1 class="intro__title">{{ spot.name }}</h1>
                <p v-if="!introOpen" class="intro__tagline">{{ spot.intro[0] }}</p>

                
                  <div v-if="introOpen" class="intro__body">
                    <ScenicKnowledgeSections v-if="current" :spot="current" :park="current.park"/>
                  </div>
                

              </div>
            </div>

            <div class="intro__foot">
              <button class="grip" :aria-label="introOpen ? '收起介绍' : '展开介绍'" @click="toggleIntro">
                
                <span class="page-dots" aria-hidden="true"><i v-for="n in DOT_COUNT" :key="n" :class="{ 'is-current': n - 1 === dotActive }"></i></span>
                
              </button>
            </div>
          </div>

          <Transition name="audio">
            <div v-if="audioOpen" class="audio">
              <button class="audio__play" :disabled="audioLoading" :aria-label="audioPlaying ? '暂停讲解' : '播放讲解'" @click="togglePlay">
                <Pause v-if="audioPlaying" :size="22" />
                <VideoPlay v-else :size="22" />
              </button>
              <div class="audio__meta">
                <div class="audio__row">
                  <span class="audio__title">{{ audioLoading ? '正在加载讲解…' : current?.name }}</span>
                  <span class="audio__time">{{ Math.floor(elapsed / 60) }}:{{ String(elapsed % 60).padStart(2, '0') }}</span>
                </div>
                <div class="audio__track"><i :style="{ width: audioPercent + '%' }"></i></div>
              </div>
              <button class="audio__close" aria-label="关闭讲解" @click="stopAudio"><Close :size="20" /></button>
            </div>
          </Transition>

          <Transition name="toast">
            <p v-if="toast" class="toast" role="status" aria-live="polite">{{ toast }}</p>
          </Transition>
        </div>

        <!-- ===== 07 景点图库展开 ===== -->
        <ScenicGalleryPanel
          v-if="scene === 'gallery' && current"
          :spot="spot"
          :photos="galleryPhotos"
          @close="viewerOpen = false; syncScene('intro')"
        />

        <Transition name="journey-slide">
          <aside v-if="panel==='journey'" class="selection-panel journey-panel">
            <TourJourney ref="journeyView" :spot-ids="stops.map(s=>s.id)" @title="journeyTitle=$event"/>
          </aside>
        </Transition>
        <aside v-if="panel==='catalog'" class="selection-panel catalog-panel" aria-label="全部景点">
          
          <div class="catalog-grid"><button v-for="p in catalog" :key="p.id" @click="choosePlace(p.id,$event)">
            <img v-if="coverMap[p.name]" :src="coverMap[p.name].url" alt=""><span>{{ p.name }}</span>
          </button></div>
        </aside>
        <aside v-else-if="panel==='list'" class="selection-panel route-list-panel" aria-label="已选景点">
          <div class="route-list">
            <div v-for="(stop,i) in stops" :key="stop.id" class="route-list__item">
              <i>{{ i+1 }}</i><b>{{ stop.name }}</b>
              <button :disabled="busy" @click="changeStop(stop.id)">移除</button>
            </div>
            <p v-if="!stops.length" class="route-empty-text">还没有选择景点</p>
          </div>
          <footer class="route-foot">
            <button class="route-primary" :disabled="!stops.length" @click="panel='plan'">规划路线</button>
          </footer>
        </aside>

        <aside v-if="panel==='plan' || panel==='journey'" v-show="panel!=='journey'" class="selection-panel route-plan-panel" :class="{ 'is-under': panel==='journey' }" aria-label="规划路线">
          <div class="route-body" @scroll.passive="onRouteScroll">
            <template v-if="overview">
              <div ref="routeMapEl" class="route-map" aria-label="路线地图"></div>
              <div class="route-facts">
                <div><span>全程步行</span><b>{{ overview.walking_minutes == null ? '待确认' : overview.walking_minutes+' 分钟' }}</b></div>
                <div><span>路线距离</span><b>{{ metersText }}</b></div>
                <div><span>总时长</span><b>{{ overview.total_minutes == null ? '待确认' : overview.total_minutes+' 分钟' }}</b></div>
              </div>
              <RouteStopList :stops="overview.stops" :disabled="busy" @reorder="ids=>saveSettings({spot_ids:ids})" @remove="removePlannedStop"/>
              <div class="route-row family-row"><span>同行成员</span><div>
                <label><input type="checkbox" :checked="elderly" :disabled="busy" @change="saveSettings({elderly:!elderly})">老人</label>
                <label><input type="checkbox" :checked="children" :disabled="busy" @change="saveSettings({children:!children})">小孩</label>
              </div></div>
              <p v-if="accessibility" class="accessibility-status">无障碍模式 · 优先无台阶步道</p>
              <div v-if="!overview.complete" class="route-warning">
                <p>这段路线无法确认通行：</p>
                <ul>
                  <li v-for="issue in routeIssues" :key="issue">{{ issue }}</li>
                </ul>
                <p class="hint">原因：当前步行路网里找不到这一段的无台阶路线，可能该段有台阶，也可能是无障碍数据还没覆盖；不代表现场一定不能走。建议删掉其中一个景点、关闭老人/小孩的无障碍模式，或换一个离园出口。</p>
              </div>
              <div class="route-row"><span>离园出口</span><button class="exit-trigger" :aria-expanded="exitPickerOpen" @click="exitPickerOpen=true">{{exits.find(e=>e.value===endArea)?.label}} <ArrowRight :size="16"/></button></div>
            </template>
            <div v-else-if="busy" class="plan-skeleton" aria-busy="true" aria-label="路线加载中">
              <div class="sk sk-map"></div>
              <div class="sk-facts">
                <div class="sk sk-fact"></div><div class="sk sk-fact"></div><div class="sk sk-fact"></div>
              </div>
              <div v-for="n in 3" :key="n" class="sk-stop">
                <div class="sk sk-dot"></div>
                <div class="sk-lines"><div class="sk sk-line w60"></div><div class="sk sk-line w30"></div></div>
              </div>
            </div>
            <div v-else class="route-empty">
              <template v-if="stops.length && planAttempted">
                <p>路线加载失败</p>
                <p v-if="planError" class="route-error">{{ planError }}</p>
                <button class="route-primary" @click="loadPlan()">重试</button>
              </template>

              <template v-else>
                <p>还没有选择景点</p>
                <button class="route-primary" @click="panel='catalog'">去选景点</button>
              </template>
            </div>
          </div>
        </aside>

        <Transition name="exit-popup"><div v-if="exitPickerOpen" class="exit-scrim" @click.self="exitPickerOpen=false">
          <section class="exit-picker" role="dialog" aria-modal="true" aria-label="选择离园出口" @keydown.esc="exitPickerOpen=false">
            <button v-for="item in exits" :key="item.value" :aria-pressed="endArea===item.value" @click="chooseExit(item.value)">{{item.label}}<span v-if="endArea===item.value" aria-hidden="true">✓</span></button>
          </section>
        </div></Transition>
      </section>
    </div>
    <nav v-if="isAppWebview" class="app-dock" aria-label="底部导航">
      <button class="on" @click="openAppTab('home')"><House :size="24" aria-hidden="true" /><span>首页</span></button>
      <button @click="openAppTab('ai')"><Headphones :size="24" aria-hidden="true" /><span>AI导游</span></button>
      <button @click="openAppTab('mine')"><User :size="24" aria-hidden="true" /><span>我的</span></button>
    </nav>
  </div>
</template>

<style scoped lang="scss">
// 站点全局样式给 html/body/#app 设了 1180px 最小宽度（管理端桌面版需要），
// 这个模块是手机页，必须让容器跟随视口收缩，否则手机会被挤到右侧。
:global(html.is-scenic-app-page),
:global(body.is-scenic-app-page),
:global(#app:has(.scenic-app)) {
  min-width: 0;
  overflow-x: hidden;
  background: #f1ecfd;
}

.scenic-app {
  --sd-accent: #6a5ae0;
  --sd-accent-soft: #ece7ff;
  --sd-ink: #241c36;
  --sd-muted: #6f6685;
  --sd-paper: #faf8ff;
  min-height: 100dvh;
  background:
    radial-gradient(ellipse at 12% 8%, rgba(150, 130, 235, 0.22), transparent 52%),
    radial-gradient(ellipse at 92% 88%, rgba(176, 205, 235, 0.28), transparent 48%),
    linear-gradient(140deg, #f1ecfd 0%, #f7f5ff 45%, #eef4fb 100%);
  color: var(--sd-ink);
  --app-font-family: "Source Han Sans SC", "Source Han Sans CN", "Noto Sans SC", "Noto Sans CJK SC", "思源黑体", "PingFang SC", "Microsoft YaHei", sans-serif;
  --el-font-family: var(--app-font-family);
  font-family: var(--app-font-family);
}

.stage {
  position: relative;
  min-height: 100dvh;
  display: grid;
  place-items: center;
}

.stage__note {
  display: none;
}

.phone {
  position: relative;
  width: min(100vw, 412px);
  height: 100dvh;
  overflow: hidden;
  background: #0d0a16;
  isolation: isolate;
}

.selection-bar,.selection-panel {position:absolute;z-index:35;left:12px;right:12px;background:white;border-radius:18px;padding:12px;color:#241c36}
.selection-bar {bottom:8px;display:flex;justify-content:space-between}
.selection-panel {bottom:12px;max-height:55%;overflow:auto;box-shadow:0 5px 24px #241c3633}
.selection-panel label {display:block;margin:12px 0}
.selection-bar button,.selection-panel button {border:0;padding:8px 12px;border-radius:12px;cursor:pointer}
.selection-bar button:last-child {background:#6352cc;color:white}
.selection-bar button:disabled {opacity:.5}
.phone .intro__sheet {bottom:0}
/* ===================== 06 介绍展开 ===================== */
.intro {
  position: absolute;
  inset: 0;
  overflow: hidden;
  touch-action: pan-y;
  user-select: none;
}

.intro__hero {
  border-radius: 24px 24px 0 0;
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.intro__hero img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: scale(1.04);
  transition: transform 1.1s cubic-bezier(0.22, 0.68, 0.28, 1);
  will-change: transform;
}

.intro.is-expanded .intro__hero img {
  transform: scale(1.1);
}

.intro__veil {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(12, 9, 22, 0.6) 0%,
    rgba(12, 9, 22, 0.3) 18%,
    rgba(12, 9, 22, 0.34) 40%,
    rgba(12, 9, 22, 0.66) 60%,
    rgba(9, 7, 16, 0.95) 100%
  );
  transition: background 0.5s ease, transform 0.2s linear;
}

.intro.is-collapsed .intro__veil {
  background: linear-gradient(
    180deg,
    rgba(12, 9, 22, 0.46) 0%,
    rgba(12, 9, 22, 0.08) 38%,
    rgba(9, 7, 16, 0.62) 74%,
    rgba(9, 7, 16, 0.9) 100%
  );
}

.topbar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: calc(env(safe-area-inset-top, 0px) + 10px) 16px 18px;
  background: linear-gradient(
    180deg,
    rgba(247, 243, 255, 0.97) 0%,
    rgba(247, 243, 255, 0.9) 52%,
    rgba(247, 243, 255, 0.34) 82%,
    rgba(247, 243, 255, 0) 100%
  );
}

/* 全系统统一返回键：白底 + 浅紫描边 + 深色细箭头（与 App 端一致） */
.topbar__back {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  padding: 0;
  box-sizing: border-box;
  border: 1px solid rgba(139, 120, 230, 0.45);
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 6px 18px rgba(90, 70, 180, 0.12);
  color: #282332;
  font-size: 18px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  flex: none;
}

.topbar__back:hover {
  background: #fbf9ff;
}

.topbar__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tool {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(122, 107, 196, 0.12);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.86);
  color: #4b4166;
  cursor: pointer;
  box-shadow: 0 4px 14px -6px rgba(80, 60, 150, 0.32);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: background 0.2s ease, transform 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.tool:hover,
.tool.is-on {
  background: var(--sd-accent);
  border-color: rgba(106, 90, 224, 0.4);
  color: #fff;
  transform: translateY(-1px);
}

.menu {
  position: absolute;
  top: calc(env(safe-area-inset-top, 0px) + 64px);
  right: 16px;
  z-index: 8;
  width: 258px;
  padding: 8px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 24px 60px -18px rgba(20, 14, 40, 0.6);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.menu__scrim {
  position: absolute;
  inset: 0;
  z-index: 7;
}

.menu__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 12px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: var(--sd-ink);
  font-size: 18px;
  font-family: inherit;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
}

.menu__item:hover {
  background: var(--sd-accent-soft);
}

.menu__item--flag {
  color: #8a5a8f;
}

.intro__sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 4;
  display: flex;
  flex-direction: column;
  max-height: 80%;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  transition: transform 0.18s ease-out;
}

.intro.is-collapsed .intro__sheet {
  max-height: 42%;
}

.intro__scroll {
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 18px 22px 4px;
  scrollbar-width: none;
  -webkit-mask-image: linear-gradient(180deg, #000 0, #000 calc(100% - 40px), transparent 100%);
  mask-image: linear-gradient(180deg, #000 0, #000 calc(100% - 40px), transparent 100%);
}

.intro__scroll::-webkit-scrollbar {
  display: none;
}

.intro__stack {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 520px;
}

.intro__eyebrow {
  margin: 0;
  color: rgba(255, 255, 255, 0.86);
  font-size: 18px;
  letter-spacing: 0.08em;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.55), 0 1px 14px rgba(0, 0, 0, 0.5);
}

.intro__title {
  margin: 0;
  color: #fff;
  font-size: clamp(38px, 11vw, 46px);
  font-weight: 650;
  letter-spacing: 0.02em;
  line-height: 1.12;
  text-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
}

.intro__tagline {
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 20px;
  line-height: 1.6;
  text-shadow: 0 1px 14px rgba(0, 0, 0, 0.42);
}

.intro__body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 10px;
}

.intro__paragraph {
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 18px;
  line-height: 1.9;
  letter-spacing: 0.01em;
  text-shadow: 0 1px 14px rgba(0, 0, 0, 0.42);
}

.facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin: 2px 0 0;
  padding: 0;
  list-style: none;
}

.facts li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.facts span {
  color: rgba(255, 255, 255, 0.58);
  font-size: 18px;
}

.facts strong {
  color: #fff;
  font-size: 20px;
  font-weight: 600;
}

.tip {
  margin: 0;
  padding: 12px 14px 12px 16px;
  border-left: 3px solid var(--sd-accent);
  border-radius: 6px 16px 16px 6px;
  background: rgba(106, 90, 224, 0.22);
  color: rgba(255, 255, 255, 0.86);
  font-size: 18px;
  line-height: 1.75;
}

.tip__label {
  display: inline-block;
  margin-right: 8px;
  color: #cbc2ff;
  font-weight: 600;
}

.gallery-cta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  min-height: 56px;
  margin-top: 2px;
  border: 0;
  border-radius: 18px;
  background: #fff;
  color: var(--sd-ink);
  font-size: 19px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 18px 40px -20px rgba(0, 0, 0, 0.7);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.gallery-cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 22px 46px -18px rgba(0, 0, 0, 0.7);
}

.gallery-cta:active {
  transform: scale(0.985);
}

.intro__foot {
  display: flex;
  justify-content: center;
  padding: 6px 0 14px;
}

.grip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  padding: 6px 16px;
  border: 0;
  background: transparent;
  color: rgba(255, 255, 255, 0.66);
  font-size: 18px;
  font-family: inherit;
  cursor: pointer;
}

.grip__bar {
  width: 42px;
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.42);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.08);
}

.grip__text {
  letter-spacing: 0.04em;
}

.audio {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: calc(env(safe-area-inset-bottom, 0px) + 74px);
  z-index: 6;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 20px;
  background: rgba(20, 15, 36, 0.78);
  color: #fff;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 20px 44px -20px rgba(0, 0, 0, 0.7);
}

.audio__play {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 50%;
  background: #fff;
  color: var(--sd-ink);
  cursor: pointer;
}

.audio__meta {
  flex: 1;
  min-width: 0;
}

.audio__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 7px;
}

.audio__title {
  overflow: hidden;
  color: rgba(255, 255, 255, 0.92);
  font-size: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.audio__time {
  color: rgba(255, 255, 255, 0.58);
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.audio__track {
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
}

.audio__track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #a99bff, #fff);
  transition: width 0.6s linear;
}

.audio__close {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  cursor: pointer;
}

.toast {
  position: absolute;
  top: calc(env(safe-area-inset-top, 0px) + 66px);
  left: 50%;
  z-index: 9;
  width: max-content;
  max-width: calc(100% - 40px);
  margin: 0;
  padding: 10px 18px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  background: rgba(20, 15, 36, 0.82);
  color: #fff;
  font-size: 18px;
  line-height: 1.5;
  text-align: center;
  transform: translateX(-50%);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

/* ===================== 设计页切换（预览用） ===================== */
.page-switch {
  position: absolute;
  top: calc(env(safe-area-inset-top, 0px) + 16px);
  left: 50%;
  z-index: 40;
  display: flex;
  gap: 2px;
  padding: 3px;
  border: 1px solid rgba(122, 107, 196, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 6px 20px -10px rgba(66, 50, 120, 0.4);
  transform: translateX(-50%);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.phone.is-viewing .page-switch {
  opacity: 0;
  pointer-events: none;
}

.page-switch {
  transition: opacity 0.2s ease;
}

.page-switch button {
  padding: 5px 11px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #6f6685;
  font-size: 18px;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.page-switch button.is-on {
  background: var(--sd-accent);
  color: #fff;
  font-weight: 600;
  box-shadow: 0 4px 12px -4px rgba(106, 90, 224, 0.6);
}

/* ===================== 过渡 ===================== */
.reveal-enter-active,
.reveal-leave-active {
  transition: opacity 0.32s ease, transform 0.32s ease;
}

.reveal-enter-from,
.reveal-leave-to {
  opacity: 0;
  transform: translateY(14px);
}

.pop-enter-active,
.pop-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}

.audio-enter-active,
.audio-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.audio-enter-from,
.audio-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -8px);
}

@media (min-width: 560px) {
  .stage {
    padding: 36px 0;
  }

  .stage__note {
    position: absolute;
    top: 34px;
    left: 40px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    color: #3d3357;
  }

  .stage__note strong {
    font-size: 20px;
    font-weight: 650;
  }

  .stage__sub {
    color: #6f6685;
    font-size: 18px;
  }

  .stage__badge {
    width: max-content;
    margin-bottom: 4px;
    padding: 3px 10px;
    border-radius: 999px;
    background: rgba(106, 90, 224, 0.14);
    color: #5b49cf;
    font-size: 18px;
    font-weight: 600;
  }

  .phone {
    height: min(100dvh - 72px, 880px);
    border-radius: 46px;
    box-shadow:
      0 0 0 10px rgba(255, 255, 255, 0.55),
      0 0 0 11px rgba(106, 90, 224, 0.14),
      0 44px 100px -32px rgba(36, 28, 54, 0.6);
  }
}

@media (prefers-reduced-motion: reduce) {
  .intro__hero img,
  .intro__sheet,
  .intro__veil,
  .reveal-enter-active,
  .reveal-leave-active,
  .audio-enter-active,
  .audio-leave-active,
  .toast-enter-active,
  .toast-leave-active {
    transition: none;
  }
}

.phone {width:min(100vw,390px);background:#fff}
@media(min-width:560px){.stage{padding:8px 0;box-sizing:border-box}.phone{height:min(844px,calc(100dvh - 16px));border-radius:32px}}
.phone .intro__hero,.phone .intro__veil {top:64px;border-radius:44px 44px 0 0;overflow:hidden}
.phone .intro__veil {background:linear-gradient(0deg,#120e19 0%,rgba(18,14,25,.86) 25%,transparent 78%)}
.phone .intro__scroll {mask-image:none}
.intro__tagline {display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:15px}
.spot-strip {display:flex;gap:6px;overflow-x:auto;scrollbar-width:thin}
.spot-strip button {position:relative;flex:none;width:84px;height:58px;padding:0;overflow:hidden;border:2px solid transparent;border-radius:9px;background:#fff}
.spot-strip button[aria-current=true] {border-color:#b9aaff}
.spot-strip span {position:absolute;inset:auto 0 0;padding:7px 2px 3px;background:linear-gradient(transparent,rgba(15,12,22,.9));color:white;font-family:inherit;font-size:14px;line-height:1.4;font-weight:600;text-align:center}
.spot-strip img {width:100%;height:100%;object-fit:cover}

.intro__sheet {isolation:isolate}
.intro__sheet::before {content:"";position:absolute;inset:-28px 0 -70px;z-index:-1;pointer-events:none;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);mask-image:linear-gradient(transparent,#000 32%);background:rgba(20,15,30,.25)}
.spot-strip {display:grid;grid-template-columns:repeat(4,minmax(0,1fr)) 36px;align-items:center}
.spot-strip button {width:100%}
.spot-strip button:last-child {height:36px;border-radius:50%}
.phone .catalog-panel {top:60px;bottom:12px;max-height:none;background:#faf8ff}
.catalog-panel header {display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.catalog-grid {display:grid;grid-template-columns:1fr 1fr;gap:8px}
.catalog-grid button {position:relative;min-height:85px;padding:0;overflow:hidden}
.catalog-grid img {display:block;width:100%;aspect-ratio:1.45;object-fit:cover}
.catalog-grid span {position:absolute;inset:auto 0 0;padding:10px 5px 5px;color:white;background:linear-gradient(transparent,#211a2ddb)}

.plan-tool {position:relative}
.plan-count {position:absolute;right:-3px;top:-3px;background:var(--sd-accent);color:white;border-radius:12px;min-width:17px;padding:1px 3px;font:600 11px/15px system-ui}
.topbar__actions .tool {width:44px;height:44px}
.topbar__actions .tool:active {transform:scale(.96)}
.phone .menu {width:max-content;max-width:calc(100% - 32px);padding:4px;border-radius:15px;right:16px;top:calc(env(safe-area-inset-top,0px) + 58px);transform-origin:calc(100% - 22px) top}
.phone .menu__item {min-height:44px;padding:6px 12px;gap:8px;border-radius:11px;font-size:16px}
.pop-enter-active {transition:transform 175ms cubic-bezier(.2,.85,.3,1.15),opacity 120ms ease-out}
.pop-leave-active {transition:transform 110ms ease-out,opacity 100ms ease-out}
.pop-enter-from,.pop-leave-to {opacity:0;transform:translateY(-4px) scale(.96)}
@media(prefers-reduced-motion:reduce){.pop-enter-active,.pop-leave-active,.topbar__actions .tool {transition:none}}

.phone .spot-strip {width:max-content;max-width:100%;box-sizing:border-box;padding:5px;gap:4px;grid-template-columns:repeat(4,48px) 38px;border-radius:12px;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.2);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.phone .spot-strip button {height:44px;background:transparent;border:1px solid rgba(255,255,255,.15);border-radius:7px}
.phone .spot-strip button:last-child {height:44px;border-radius:7px;background:rgba(255,255,255,.1);color:white;display:grid;place-items:center}
.phone .spot-strip button[aria-current=true] {border-color:rgba(255,255,255,.85)}
.phone .spot-strip span {font-size:10px;line-height:1.2;padding:8px 1px 2px}

.phone button {-webkit-tap-highlight-color:transparent;touch-action:manipulation}
.phone button:focus:not(:focus-visible) {outline:none}
.phone .topbar {height:64px;box-sizing:border-box;padding:8px 16px;background:white;z-index:40}
.phone .tool {flex:none;position:relative;overflow:hidden}
.phone .tool:hover {transform:none}
.phone .tool:active {transform:scale(.96)}
.phone .intro__hero {clip-path:inset(0 round 44px 44px 0 0);isolation:isolate;background:#181322}
.phone .intro__hero img {position:absolute;inset:0}
.phone .intro__veil {clip-path:inset(0 round 44px 44px 0 0)}
.phone .selection-panel {inset:64px 0 0;max-height:none;border-radius:44px 44px 0 0;padding:28px 22px;box-sizing:border-box;background:#faf8ff;box-shadow:none}
.phone .spot-strip {display:flex;gap:4px}
.thumb-window {width:204px;overflow:hidden;border-radius:7px}
.thumb-track {display:flex;gap:4px;transition:transform 240ms cubic-bezier(.2,0,.2,1)}
.phone .thumb-track button {flex:0 0 48px;width:48px}
.phone .thumb-track button:last-child {display:block;border-radius:7px}
.phone .spot-strip .all-spots {width:38px;flex:0 0 38px}
.page-dots {display:flex;gap:5px;margin-top:5px}
.page-dots i {width:4px;height:4px;border-radius:50%;background:#ffffff55;transition:background 180ms,transform 180ms}
.page-dots .is-current {background:white;transform:scale(1.35)}
.next-enter-active,.next-leave-active,.previous-enter-active,.previous-leave-active {transition:transform 240ms cubic-bezier(.2,0,.2,1)}
.phone .intro__hero .next-enter-from {transform:translateX(100%)}
.phone .intro__hero .next-leave-to {transform:translateX(-100%)}
.phone .intro__hero .previous-enter-from {transform:translateX(-100%)}
.phone .intro__hero .previous-leave-to {transform:translateX(100%)}
@media(prefers-reduced-motion:reduce){.thumb-track,.next-enter-active,.next-leave-active,.previous-enter-active,.previous-leave-active{transition:none}}

:global(html.is-scenic-app-page),:global(body.is-scenic-app-page),:global(#app:has(.scenic-app)),.scenic-app {background:#fff}
.phone {--content-top:calc(64px + env(safe-area-inset-top,0px));background:white}
.phone .topbar {height:var(--content-top);padding-top:calc(8px + env(safe-area-inset-top,0px))}
.phone .intro__hero,.phone .intro__veil {inset:var(--content-top) 4px 4px;border-radius:36px;clip-path:inset(0 round 36px)}
.phone .intro__veil {background:linear-gradient(0deg,rgba(20,14,12,.52),transparent 55%)}
.phone .intro__sheet {left:4px;right:4px;bottom:4px;border-radius:0 0 36px 36px;overflow:hidden}
.phone .intro__sheet::before {inset:0;backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);mask-image:linear-gradient(transparent,#000 55%);background:rgba(40,25,15,.1)}
.phone .intro__scroll {padding:20px 16px 4px}
.phone .intro__stack {gap:9px}
.phone .intro__title {font-size:26px;line-height:1.25;font-weight:600;letter-spacing:0}
.phone .intro__tagline {font-size:13px;line-height:1.65;-webkit-line-clamp:3;color:rgba(255,255,255,.88)}
.phone .spot-strip {width:81.5%;max-width:100%;padding:4px;gap:3px;border-radius:8px;background:rgba(255,255,255,.18);margin-bottom:3px}
.phone .thumb-window {flex:1;width:0;border-radius:4px}
.phone .thumb-track {gap:0}
.phone .thumb-track button {flex:0 0 25%;width:25%;height:auto;aspect-ratio:1;box-sizing:border-box;border-radius:4px;border-width:1px}
.phone .thumb-track button:last-child {height:auto;border-radius:4px}
.phone .thumb-track img {display:block}
.phone .thumb-track span {font-size:9px}
.phone .spot-strip .all-spots {flex:0 0 17%;width:17%;height:auto;aspect-ratio:1;border-radius:4px}
.phone .intro__foot {padding:5px 0 12px}
.phone .grip {padding:5px 16px}
.phone .selection-panel {inset:var(--content-top) 4px 4px;border-radius:36px}
.phone .menu {top:calc(var(--content-top) - 6px)}
@media(min-width:560px){.phone{box-shadow:none}.stage{background:white}}
.sheet-blur {position:absolute;inset:-24px;z-index:-1;pointer-events:none;background-size:cover;background-position:center bottom;filter:blur(22px);mask-image:linear-gradient(transparent,#000 55%);-webkit-mask-image:linear-gradient(transparent,#000 55%)}

.phone {width:100%;max-width:430px}
.phone .plan-tool {overflow:visible}
.phone .plan-count {top:0;right:0;min-width:16px;height:16px;padding:0 2px;box-sizing:border-box;border:1px solid white;line-height:14px}
.phone {--content-top:52px}
.phone .topbar {height:52px;padding:4px 12px}
.phone .intro__hero,.phone .intro__veil {inset:52px 3px 3px}
.phone .intro__sheet {left:3px;right:3px;bottom:3px}
.phone .selection-panel {inset:52px 3px 3px;padding:12px;background:white}
.phone .catalog-panel {padding:8px}
.phone .catalog-grid {gap:6px}
.phone .catalog-grid button {border-radius:12px}
.phone .intro.is-expanded .intro__sheet {max-height:calc(100% - 64px)}
.phone .intro.is-expanded .sheet-blur {mask-image:linear-gradient(transparent,#000 18%);-webkit-mask-image:linear-gradient(transparent,#000 18%)}
.phone .intro.is-expanded .intro__scroll {touch-action:pan-y}
@media(min-width:560px){.phone{width:390px}}
/* ==== 2026-11-15 fix: 顶部只留返回箭头 / 缩略条五格等宽无残影 / 收紧底部留白 ==== */
/* 收起状态下允许上滑展开介绍：不要让浏览器把竖向手势当成滚动吃掉 */
.phone .intro.is-collapsed { touch-action: none; }
.phone .intro.is-collapsed .intro__scroll { touch-action: none; }
.phone .spot-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  align-items: stretch;
  width: 81.5%;
  max-width: 100%;
  box-sizing: border-box;
  padding: 4px;
  gap: 3px;
  border-radius: 10px;
}
.phone .spot-strip > button {
  width: 100%;
  height: auto;
  aspect-ratio: 1;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 6px;
  overflow: hidden;
}
.phone .spot-strip > button[aria-current='true'] {
  border-color: rgba(255, 255, 255, 0.95);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.55);
}
.phone .spot-strip > button.all-spots {
  display: grid;
  place-items: center;
  width: 100%;
  height: auto;
  aspect-ratio: 1;
  flex: initial;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}
.phone .spot-strip span { font-size: 9px; line-height: 1.2; padding: 6px 1px 2px; }
.phone .intro__foot { padding: 10px 0 calc(env(safe-area-inset-bottom, 0px) + 12px); }
.phone .intro__scroll { min-height: 0; }
/* 收起态由内容撑开，避免固定 42% 高度在底部留下大块空白 */
.phone .intro.is-collapsed .intro__sheet { max-height: none; }
.phone .grip { padding: 2px 16px 4px; gap: 0; }
.phone .page-dots { margin-top: 0; }
.phone .intro__scroll { padding-bottom: 0; }

/* 安卓 WebView 对带 scale/clip-path 的大图会画出竖向拼接线，去掉变换与裁剪 */
.phone .intro__hero,
.phone .intro__veil { clip-path: none; }
.intro__hero__media { position: absolute; inset: 0; background-size: cover; background-repeat: no-repeat; }
.hero-fade-enter-active, .hero-fade-leave-active { transition: opacity 0.3s ease; }
.hero-fade-enter-from, .hero-fade-leave-to { opacity: 0; }
.phone .intro__hero img { display: none; }
.phone .intro__hero { border-radius: 36px 36px 0 0; }

/* 触屏上 hover 会残留成填充色，限定只在真正支持 hover 的设备生效 */
@media (hover: none) {
  .phone .tool:hover { background: rgba(255, 255, 255, 0.86); color: #4b4166; border-color: rgba(122, 107, 196, 0.12); transform: none; }
  .phone .topbar__actions .tool.is-on:hover { background: var(--sd-accent); border-color: rgba(106, 90, 224, 0.4); color: #fff; }
}



/* 顶栏固定白底，按钮不被遮住 */
.phone .topbar {
  position: relative;
  top: auto;
  left: auto;
  right: auto;
  z-index: 200;
  margin-top: 50px;
  background: #ffffff;
  padding: 4px 16px 12px;
}
/* 图片上边界下放到按钮下方 */
.phone { --content-top: 106px; }
/* 文字和圆点整体上移，底部留白 */
.phone .page-dots { margin-bottom: 4px; }

/* 底部蒙版卡片：圆角、半透明深色渐变，文字在卡片内 */
.phone .intro__sheet {
  left: 12px;
  right: 12px;
  bottom: 18px;
  border-radius: 26px;
  padding: 10px 16px 6px;
  background: linear-gradient(180deg, rgba(18, 14, 24, 0.32) 0%, rgba(18, 14, 24, 0.72) 48%, rgba(18, 14, 24, 0.9) 100%);
  box-shadow: 0 20px 44px rgba(10, 8, 16, 0.32);
}
.phone .intro__sheet .intro__scroll { padding: 0 2px; }
.phone .intro__title {
  font-family: "Noto Serif SC", "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif;
  font-weight: 600;
  letter-spacing: 0.03em;
}
.phone .intro__tagline {
  color: rgba(255, 255, 255, 0.82);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}
.phone .intro__foot { padding-bottom: 8px; }

/* 底部景点缩略条：液态玻璃（大模糊 + 高饱和 + 10% 白 + 1px 亮边 + 边缘折射） */
.phone .spot-strip {
  position: relative;
  background: rgba(255, 255, 255, 0.10) !important;
  -webkit-backdrop-filter: blur(28px) saturate(180%);
  backdrop-filter: blur(28px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.32);
  box-shadow:
    inset 1px 1px 0 rgba(255, 255, 255, 0.62),
    inset -1px -1px 0 rgba(255, 255, 255, 0.18),
    0 10px 30px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}
.phone .spot-strip::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 2;
  border-radius: inherit;
  pointer-events: none;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.38) 0%, rgba(255, 255, 255, 0.06) 22%, transparent 46%, transparent 72%, rgba(255, 255, 255, 0.16) 100%);
  mix-blend-mode: screen;
  opacity: 0.9;
}
.phone .spot-strip > button,
.phone .spot-strip .thumb-window { position: relative; z-index: 1; }

/* 底部景点缩略图不要阴影 */
.phone .spot-strip,
.phone .spot-strip > button,
.phone .spot-strip > button.all-spots,
.phone .thumb-track button { box-shadow: none !important; }



/* 页面由 .phone 内部滚动，禁止文档本身滚动，避免顶栏被卷走 */
:global(html.is-scenic-app-page),
:global(body.is-scenic-app-page) { height: 100%; overflow: hidden; }
.scenic-app { height: 100vh; height: 100dvh; overflow: hidden; }

/* 页面到底：避免底部露出白色（body/WebView 底色、3px 缝隙） */
:global(html.is-scenic-app-page),
:global(body.is-scenic-app-page),
:global(body.is-scenic-app-page #app) { background: #0d0a16; }
.scenic-app { min-height: 100vh; min-height: 100dvh; }
.phone { height: 100vh; height: 100dvh; }
.phone .intro__hero,
.phone .intro__veil { left: 0; right: 0; bottom: 0; }
.phone .intro__sheet { left: 0; right: 0; bottom: 0; border-radius: 0; }
.phone .gallery-card { bottom: 0; }

/* 返回按钮：统一为白底紫边圆形（触屏不保留 hover 底色） */
.phone .topbar__back,
.phone .topbar__back:hover,
.phone .topbar__back:active { background: #fff; border-radius: 50%; }
.phone .route-back,
.phone .route-back:hover,
.phone .route-back:active { background: #fff; border-radius: 50%; }

/* 右上角按钮：从圆形改成图二那种圆角方框 */
.phone .topbar__actions .tool { width: 50px; height: 40px; border-radius: 14px; }
.phone .topbar-start {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 44px;
  padding: 0 18px;
  border: 0;
  border-radius: 15px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.94) 0%, rgba(248, 246, 255, 0.82) 100%);
  -webkit-backdrop-filter: blur(14px) saturate(150%);
  backdrop-filter: blur(14px) saturate(150%);
  border: 1px solid rgba(139, 120, 230, 0.4);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.95), 0 8px 20px -12px rgba(90, 70, 180, 0.3);
  color: #2a2438;
  font-family: inherit;
  font-size: 15.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  transition: transform 160ms cubic-bezier(.2, .8, .2, 1), box-shadow 160ms, filter 160ms;
}
.phone .topbar-start span { line-height: 1; }
.phone .topbar-start:active { transform: scale(.965); background: linear-gradient(135deg, rgba(255, 255, 255, 1) 0%, rgba(240, 237, 250, 0.95) 100%); box-shadow: inset 0 1px 0 #fff, 0 3px 10px -10px rgba(40,30,70,.35); }
.phone .topbar-start:disabled { filter: grayscale(.15); opacity: .42; box-shadow: none; }

.phone .plan-tool { width: 50px; height: 40px; border-radius: 14px; }
.phone .plan-count { top: 2px; right: 4px; }

/* 隐藏页面滚动条（安卓 WebView 会画出一条竖向滚动条） */
.phone .intro__scroll,
.phone .route-body,
.phone .route-list { scrollbar-width: none; -ms-overflow-style: none; }
.phone .intro__scroll::-webkit-scrollbar,
.phone .route-body::-webkit-scrollbar,
.phone .route-list::-webkit-scrollbar { width: 0; height: 0; display: none; }

/* ===== 规划路线页（设计页 10 路线结果与人数设置） ===== */
.phone .selection-panel.route-list-panel,
.phone .selection-panel.route-plan-panel { display: flex; flex-direction: column; padding: 0; overflow: hidden; background: #fff; overscroll-behavior: none; }
.phone .selection-panel.route-plan-panel,
.phone .selection-panel.route-list-panel { inset: var(--content-top, 52px) 0 0; border-radius: 0; z-index: 45; }
.route-head { display: flex; align-items: center; gap: 8px; flex: none; padding: calc(env(safe-area-inset-top, 0px) + 6px) 12px 8px; }
.route-head h2 { font-size: 20px; font-weight: 600; }
.route-head h2 { flex: 1; margin: 0; font-size: 20px; font-weight: 600; color: #241c36; }
.route-count { flex: none; font-size: 18px; color: #6f6685; }
.route-back { display: grid; place-items: center; width: 44px; height: 44px; flex: none; box-sizing: border-box; border: 1px solid rgba(139, 120, 230, 0.45); border-radius: 50%; background: #fff; box-shadow: 0 6px 18px rgba(90, 70, 180, 0.12); color: #282332; cursor: pointer; }
.route-body { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; display: block; padding: 0 0 12px; overscroll-behavior: none; background: #fff; }
.route-map { height: 300px; margin: 0 3px; overflow: hidden; border-radius: 36px 36px 0 0; background: #e8eef1; }
:global(.route-stop-marker span) { display: grid; place-items: center; width: 30px; height: 30px; border: 2px solid #fff; border-radius: 50%; background: #5a78f0; color: #fff; font-family: var(--app-font-family); font-size: 18px; font-weight: 600; line-height: 1; box-shadow: 0 3px 8px rgba(0, 0, 0, 0.25); }
.route-facts { padding: 0 16px; }
.route-facts div { display: flex; align-items: center; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid #f0edf7; }
.route-facts span { font-size: 18px; color: #6f6685; }
.route-facts b { font-size: 18px; font-weight: 600; color: #241c36; }
.route-stops { display: flex; flex-direction: column; gap: 0; margin: 0; padding: 0 16px; list-style: none; }
.route-stops li { display: flex; align-items: center; gap: 10px; padding: 14px 0; border-bottom: 1px solid #f0edf7; }
.route-stops i { display: grid; place-items: center; width: 24px; height: 24px; flex: none; border-radius: 50%; background: #6a5ae0; color: #fff; font-style: normal; font-size: 18px; }
.route-stops b { flex: 1; font-size: 18px; font-weight: 500; color: #241c36; }
.route-stops span { font-size: 18px; color: #6f6685; }
.route-row { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid #f0edf7; font-size: 18px; color: #241c36; }
.route-stepper { display: flex; align-items: center; gap: 12px; }
.route-stepper button { width: 30px; height: 30px; border: 1px solid #ddd6f0; border-radius: 50%; background: #fff; color: #241c36; font-size: 18px; line-height: 1; cursor: pointer; }
.route-stepper b { min-width: 18px; text-align: center; font-size: 18px; }
.route-row select { border: 0; background: transparent; color: #241c36; font-family: inherit; font-size: 18px; }
.route-foot { display: flex; gap: 10px; flex: none; padding: 12px 16px calc(env(safe-area-inset-bottom, 0px) + 14px); border-top: 1px solid #f0edf7; }
.route-ghost, .route-primary { flex: 1; min-height: 48px; border: 0; border-radius: 14px; font-family: inherit; font-size: 18px; cursor: pointer; }
.route-ghost { background: #f4f1fb; color: #241c36; }
.route-primary { background: #6a5ae0; color: #fff; }
.route-primary:disabled { opacity: 0.5; }
.route-list { flex: 1; min-height: 0; overflow-y: auto; padding: 14px 16px calc(env(safe-area-inset-bottom, 0px) + 20px); display: flex; flex-direction: column; gap: 8px; }
.route-list__item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 14px; background: #f7f5fc; }
.route-list__item i { display: grid; place-items: center; width: 24px; height: 24px; flex: none; border-radius: 50%; background: #6a5ae0; color: #fff; font-style: normal; font-size: 18px; }
.route-list__item b { flex: 1; font-size: 18px; font-weight: 500; color: #241c36; }
.route-list__item button { border: 0; border-radius: 10px; padding: 6px 10px; background: #fff; color: #8a5a8f; font-family: inherit; font-size: 18px; cursor: pointer; }
.route-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; color: #6f6685; font-size: 18px; }
.route-empty p, .route-empty-text { margin: 0; font-size: 18px; color: #6f6685; }
.route-empty .route-primary { flex: 0 0 auto; width: auto; min-width: 160px; padding: 0 24px; }
.route-error { margin: 0; font-size: 18px; color: #b4465a; text-align: center; word-break: break-all; }
.route-loading { flex: 1; display: grid; place-items: center; color: #6f6685; font-size: 18px; }
.route-more-hint { position: absolute; left: 50%; bottom: calc(env(safe-area-inset-bottom, 0px) + 76px); transform: translateX(-50%); z-index: 6; display: grid; place-items: center; width: 34px; height: 34px; border: 0; border-radius: 50%; background: rgba(255,255,255,.96); color: #6957cd; font-size: 18px; line-height: 1; box-shadow: 0 4px 14px rgba(60,40,120,.18); animation: route-hint-bounce 1.4s ease-in-out infinite; }
@keyframes route-hint-bounce { 0%,100%{transform:translate(-50%,0)} 50%{transform:translate(-50%,4px)} }
.route-recalc { position: sticky; top: 8px; z-index: 5; width: fit-content; margin: 8px auto 0; padding: 6px 14px; border-radius: 999px; background: rgba(255,255,255,.94); color: #6957cd; font-size: 13px; box-shadow: 0 4px 14px rgba(60,40,120,.12); }

/* 安卓 WebView 在展开时 backdrop-filter 会画出白色块，这里改回半透明纯色 */
.phone .intro__sheet::before { display: none; }
.phone .intro.is-expanded .intro__sheet { background: transparent; }
/* 不要深色遮罩盖住照片 */
.phone .intro__veil { background: none; }
.phone .intro__title,
.phone .intro__tagline,
.phone .intro__body { text-shadow:none; }
.phone .intro.is-collapsed .intro__sheet { background:transparent;-webkit-backdrop-filter:blur(18px) saturate(1.1);backdrop-filter:blur(18px) saturate(1.1);box-shadow:none; }
.phone .intro.is-collapsed .intro__title,
.phone .intro.is-expanded .intro__title { color:#fff; }
.phone .intro.is-collapsed .intro__tagline,
.phone .intro.is-expanded .intro__tagline { color:rgba(255,255,255,.92); }
.phone .spot-strip { backdrop-filter: blur(14px) saturate(1.1); -webkit-backdrop-filter: blur(14px) saturate(1.1); background: transparent; }
/* 去掉底部叠的模糊照片渐变层 */
.phone .sheet-blur { display:none !important; }
.phone .intro__sheet::before { display:none !important; }
.phone .sheet-blur { filter: blur(18px); opacity: .6; }

.scenic-app {--app-font-family:system-ui,-apple-system,sans-serif;font-family:var(--app-font-family)}
.phone,.phone button,.phone input,.phone select,.phone .intro__title,.phone .intro__tagline,.phone .intro__paragraph,.phone .spot-strip span {font-family:system-ui,-apple-system,sans-serif}
.phone .journey-panel {padding:0;overflow:hidden;background:linear-gradient(160deg,#f8f5ff 0%,#f1edfe 52%,#edf3fb 100%)}
.phone .selection-panel.journey-panel {inset:var(--content-top,106px) 0 0;border-radius:28px 28px 0 0}
.phone .selection-panel.journey-panel .journey {border-radius:28px 28px 0 0}
.journey-nav-title {position:absolute;left:0;right:0;top:50%;transform:translateY(-50%);text-align:center;font-size:17px;font-weight:600;letter-spacing:.02em;color:#282332;pointer-events:none}

/* Keep the scenic image flush at the bottom, with only the upper corners rounded. */
.phone,.phone .intro,.phone .intro__hero,.phone .intro__hero__media,.phone .intro__veil,
.phone .intro__sheet,.phone .intro__sheet::before,.phone .topbar,.phone .tool,
.phone .spot-strip,.phone .intro__title,.phone .intro__tagline {box-shadow:none!important;text-shadow:none!important}
.phone {border-radius:0}
.phone .intro__hero,.phone .intro__veil {inset:var(--content-top,52px) 0 0;border-radius:30px 30px 0 0;clip-path:inset(0 round 30px 30px 0 0);overflow:hidden}
.phone .intro__hero__media {border-radius:inherit}
.phone .intro__sheet {left:0;right:0;bottom:0;border-radius:0}
.phone .intro__sheet::before {border-radius:0}

/* Expanded copy stays inside the photo viewport; only the copy area scrolls. */
.phone .intro.is-expanded .intro__sheet {
  top:var(--content-top,106px);bottom:0;height:auto;max-height:none;min-height:0;
  box-sizing:border-box;padding:24px 18px 8px;border-radius:30px 30px 0 0;
  display:flex;flex-direction:column;overflow:hidden;transition:none;
  background:transparent;
  -webkit-backdrop-filter:blur(18px) saturate(1.1);backdrop-filter:blur(18px) saturate(1.1);
  box-shadow:none;
}
.phone .intro.is-expanded .intro__scroll {
  flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;padding:0 0 16px;
  overscroll-behavior:contain;-webkit-mask-image:none;mask-image:none;
}
.phone .intro.is-expanded .intro__stack {min-height:0;margin:0}
.phone .intro.is-expanded .intro__body {opacity:1;transform:none;filter:none;color:#fff}
.phone .intro.is-expanded .intro__body,
.phone .intro.is-expanded .intro__body :deep(*) {text-shadow:none}
.phone .intro.is-expanded .intro__body :deep(h2) {color:#fff}
.phone .intro.is-expanded .intro__body :deep(h3) {color:#fff}
.phone .intro.is-expanded .intro__body :deep(p) {color:#fff}
.phone .intro.is-expanded .intro__body :deep(a) {color:#fff;text-decoration:underline}
.phone .intro.is-expanded .intro__paragraph {opacity:1;color:white;overflow-wrap:anywhere}
.phone .intro.is-expanded .intro__foot {flex:none}
.phone .intro.is-expanded .intro__sheet::before {display:none}
.phone .intro.is-expanded .sheet-blur {display:none}
.phone .intro__body {transition:none}

.phone .intro__hero,.phone .intro__veil {left:2px;right:2px}
.phone .intro__sheet {left:2px;right:2px;transform:none;transition:none}
.phone .intro__scroll {overscroll-behavior:none}
:global(html.is-scenic-app-page),:global(body.is-scenic-app-page) {overscroll-behavior:none}

.phone .intro__title {text-align:left}
.phone .catalog-panel {inset:var(--content-top,106px) 2px 0;border-radius:30px 30px 0 0;background:#fff;box-shadow:none;clip-path:inset(0 round 30px 30px 0 0);padding:10px 8px 16px;overscroll-behavior:none}
.phone:has(.catalog-panel) .intro__hero,.phone:has(.catalog-panel) .intro__veil,.phone:has(.catalog-panel) .intro__sheet {visibility:hidden}
.phone:has(.catalog-panel) {background:white}
/* 直接进入路线规划/选择伴游时，不再先露出景点图鉴页，避免闪一下 */
.phone:has(.route-plan-panel) .intro__hero,
.phone:has(.route-plan-panel) .intro__veil,
.phone:has(.route-plan-panel) .intro__sheet,
.phone:has(.journey-panel) .intro__hero,
.phone:has(.journey-panel) .intro__veil,
.phone:has(.journey-panel) .intro__sheet {visibility:hidden}
.phone:has(.route-plan-panel),.phone:has(.journey-panel) {background:white}
/* 景点数据返回前不要先画默认的十七孔桥，避免首屏闪一下再切到第一个景点 */
.phone:not(.is-ready) .intro__hero,
.phone:not(.is-ready) .intro__veil,
.phone:not(.is-ready) .intro__sheet {visibility:hidden}
.phone:not(.is-ready) {background:#fff}
.phone .route-plan-panel {left:2px;right:2px;background:#faf9fc}
.phone .route-map {height:clamp(240px,34dvh,320px);margin:0;border-radius:30px 30px 0 0}
.phone .route-facts {display:grid;grid-template-columns:repeat(3,1fr);gap:0;background:white;padding:8px 8px 6px;margin:0 0 6px;border-radius:0 0 14px 14px}
.phone .route-facts div {display:flex;flex-direction:column;gap:3px;padding:2px;border:0;text-align:center}
.phone .route-facts span {font-size:12px}
.phone .route-facts b {font-size:18px;font-variant-numeric:tabular-nums}
.phone .route-stops {background:white;border-radius:16px;margin:0 12px;padding:0 14px}
.phone .route-stops li {padding:14px 0}
.phone .route-stops b {font-size:16px}
.phone .route-stops span {font-size:14px}
.phone .route-row {margin:10px 12px 0;padding:12px 14px;background:#fff;border:0;border-radius:16px;font-size:15px}
.phone .route-stepper button {width:36px;height:36px}
.phone .route-foot {background:#fff;border:0;padding:12px 14px max(12px,env(safe-area-inset-bottom,0px));gap:10px}
.phone .route-foot button {font-size:16px}
.exit-trigger {display:flex;align-items:center;gap:7px;min-height:40px;border:0;background:transparent;color:#6652bd;font:inherit}
.exit-scrim {position:absolute;inset:0;z-index:300;background:#17132355;display:grid;place-items:center}
.exit-picker {width:calc(100% - 40px);max-width:350px;padding:8px;border-radius:22px;background:white;box-sizing:border-box}
.exit-picker button {width:100%;display:flex;align-items:center;justify-content:space-between;min-height:46px;padding:10px 16px;border:0;border-radius:14px;background:transparent;font:inherit;font-size:16px;color:#282332;-webkit-tap-highlight-color:transparent}
.exit-picker button[aria-pressed=true] {background:#f0ecfb;color:#6652bd}

.phone .intro.is-expanded .intro__sheet {background:transparent;backdrop-filter:none;-webkit-backdrop-filter:none}
.intro-expand-surface {position:absolute;inset:0;z-index:-1;pointer-events:none;background:linear-gradient(180deg,rgba(20,17,20,.24),rgba(20,17,20,.58));backdrop-filter:blur(5px);-webkit-backdrop-filter:blur(5px)}
.exit-popup-enter-active {transition:opacity 160ms ease-out}
.exit-popup-leave-active {transition:opacity 110ms ease-out}
.exit-popup-enter-active .exit-picker {transition:transform 160ms cubic-bezier(.23,1,.32,1)}
.exit-popup-leave-active .exit-picker {transition:transform 110ms ease-out}
.exit-popup-enter-from,.exit-popup-leave-to {opacity:0}
.exit-popup-enter-from .exit-picker,.exit-popup-leave-to .exit-picker {transform:translateY(6px) scale(.97)}
@media(prefers-reduced-motion:reduce){.exit-popup-enter-active,.exit-popup-leave-active,.exit-popup-enter-active .exit-picker,.exit-popup-leave-active .exit-picker{transition:none}}

/* One frame for photo, expanded copy and secondary pages, including device safe areas. */
.phone {
  --content-top:100px;
  --frame-left:max(3px,env(safe-area-inset-left,0px));
  --frame-right:max(3px,env(safe-area-inset-right,0px));
  --frame-bottom:max(6px,env(safe-area-inset-bottom,0px));
  background:#fff;
}
.phone .topbar {height:50px}
.phone .intro__hero,.phone .intro__veil {left:var(--frame-left);right:var(--frame-right);bottom:var(--frame-bottom)}
.phone .intro__sheet,.phone .intro.is-expanded .intro__sheet {left:var(--frame-left);right:var(--frame-right);bottom:var(--frame-bottom)}
.phone .selection-panel,.phone .selection-panel.route-list-panel,.phone .selection-panel.route-plan-panel,.phone .catalog-panel {
  left:var(--frame-left);right:var(--frame-right);bottom:var(--frame-bottom);
}

.phone .intro-expand-surface {clip-path:none;inset:0;background:linear-gradient(180deg,rgba(20,17,20,.35),rgba(20,17,20,.6))}
.phone .intro.is-expanded .intro__sheet {backdrop-filter:none;-webkit-backdrop-filter:none}
.family-row>div {display:flex;gap:16px}
.family-row label {display:flex;align-items:center;gap:7px;margin:0;min-height:40px}
.family-row input[type=checkbox]{-webkit-appearance:none;appearance:none;width:20px;height:20px;margin:0;border-radius:7px;border:1px solid rgba(120,100,190,.22);background:linear-gradient(135deg,rgba(255,255,255,.96),rgba(245,242,255,.9));box-shadow:inset 0 1px 0 #fff,0 3px 8px -6px rgba(40,30,70,.35);display:grid;place-items:center;transition:background .15s,border-color .15s,transform .12s}
.family-row input[type=checkbox]:checked{border-color:rgba(106,90,224,.5);background:#fff}
.family-row input[type=checkbox]:checked::after{content:"";width:10px;height:6px;margin-top:-2px;border-left:2px solid #6a5ae0;border-bottom:2px solid #6a5ae0;transform:rotate(-45deg)}
.family-row input[type=checkbox]:active{transform:scale(.92)}
.family-row input[type=checkbox]:disabled{opacity:.45}
.accessibility-status {font-size:13px;margin:10px 26px;color:#6957cd}
.route-warning {font-size:14px;line-height:1.6;margin:10px 26px;padding:12px 14px;border-radius:14px;background:#fff4f2;color:#9c403c}
.route-warning p {margin:0 0 4px}
.route-warning ul {margin:4px 0 6px;padding-left:18px}
.route-warning li {margin:2px 0}
.route-warning .hint {margin-top:8px;font-size:13px;color:#8a6d68}

/* 文字区直接叠在清晰照片上：不做毛玻璃，只用文字投影保证可读 */
.phone .intro.is-collapsed .intro__veil {
  background: linear-gradient(180deg, rgba(9, 7, 16, 0.42) 0%, rgba(9, 7, 16, 0.1) 34%, rgba(9, 7, 16, 0.02) 52%, rgba(9, 7, 16, 0) 100%);
}
.phone .intro.is-collapsed .intro__title,
.phone .intro.is-collapsed .intro__tagline { text-shadow: 0 1px 14px rgba(8, 5, 12, 0.45) !important; }
.phone .intro-expand-surface,
.phone .intro.is-expanded .intro-expand-surface {
  inset: 0;
  border-radius: 30px 30px 0 0;
  /* 只保留毛玻璃模糊，不再叠加黑色蒙层/阴影 */
  background: transparent;
  box-shadow: none;
  backdrop-filter: blur(6px) saturate(1.04);
  -webkit-backdrop-filter: blur(6px) saturate(1.04);
  mask-image: none;
  -webkit-mask-image: none;
}
.phone .intro.is-expanded .intro__body,
.phone .intro.is-expanded .intro__body :deep(*) { text-shadow: none; }
.phone .intro.is-collapsed .intro__sheet::before,
.phone .intro.is-expanded .intro__sheet::before { display: none !important; }

/* 规划页 → 选择伴游：伴游页从右侧滑入，规划页留在底层做视差；退出时原路滑回。 */
.phone .selection-panel.journey-panel { z-index: 60; }
.phone .selection-panel.route-plan-panel {
  transition: transform .34s cubic-bezier(.22,.75,.2,1), filter .34s ease, opacity .34s ease;
  transform-origin: 50% 78%;
  will-change: transform;
}
.phone .selection-panel.route-plan-panel.is-under {
  transform: translateX(-16%) scale(.965);
  filter: brightness(.93);
  opacity: .92;
  pointer-events: none;
  box-shadow: 10px 0 34px rgba(32,22,64,.16);
}
.journey-slide-enter-active,
.journey-slide-leave-active {
  transition: transform .34s cubic-bezier(.22,.75,.2,1), box-shadow .34s ease;
  will-change: transform;
}
.journey-slide-enter-from,
.journey-slide-leave-to {
  transform: translateX(100%);
  box-shadow: -22px 0 44px rgba(32,22,64,.26);
}
.journey-slide-enter-to,
.journey-slide-leave-from {
  transform: translateX(0);
  box-shadow: -12px 0 30px rgba(32,22,64,.14);
}
@media (prefers-reduced-motion: reduce) {
  .phone .selection-panel.route-plan-panel,
  .journey-slide-enter-active,
  .journey-slide-leave-active { transition: none; }
}

/* App 内嵌页常驻底部导航：所有景点详情/规划/选择伴游页都保留 App tab。 */
.scenic-app.has-app-dock {
  --app-dock-height: calc(64px + env(safe-area-inset-bottom, 0px));
}
.scenic-app.has-app-dock .stage { min-height: calc(100dvh - var(--app-dock-height)); }
.scenic-app.has-app-dock .phone { height: calc(100dvh - var(--app-dock-height)); }
.app-dock {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 900;
  display: flex;
  align-items: stretch;
  min-height: 64px;
  box-sizing: border-box;
  padding: 6px 6px env(safe-area-inset-bottom, 0px);
  background: #fff;
  border-top: 1px solid rgba(30, 41, 59, 0.08);
  font-family: var(--app-font-family);
}
.app-dock button {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  min-height: 50px;
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: #4b5563;
  font: inherit;
  font-size: 13px;
  line-height: 1.3;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.app-dock button:active { transform: scale(0.96); }
.app-dock button.on { color: #6547ad; font-weight: 700; }
.app-dock span { display: block; }
@media (prefers-reduced-motion: reduce) { .app-dock button:active { transform: none; } }

/* 加载骨架屏：景点/路线数据返回前不再白屏或闪旧内容 */
.sk {
  background: linear-gradient(90deg, #f0eef6 25%, #faf9fd 37%, #f0eef6 63%);
  background-size: 400% 100%;
  animation: sk-shimmer 1.4s ease infinite;
  border-radius: 12px;
}
@keyframes sk-shimmer { 0% { background-position: 100% 0; } 100% { background-position: 0 0; } }
.scenic-skeleton {
  position: absolute;
  inset: var(--content-top) var(--frame-right) var(--frame-bottom) var(--frame-left);
  z-index: 20;
  box-sizing: border-box;
  padding: 18px 16px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.sk-hero { height: 46%; min-height: 220px; border-radius: 26px; }
.sk-strip { display: flex; gap: 10px; }
.sk-thumb { width: 64px; height: 64px; border-radius: 14px; flex: none; }
.sk-title { height: 30px; width: 45%; }
.sk-line { height: 14px; }
.sk-line.w90 { width: 90%; }
.sk-line.w80 { width: 80%; }
.sk-line.w60 { width: 60%; }
.sk-line.w30 { width: 30%; }
.plan-skeleton { display: flex; flex-direction: column; gap: 12px; padding: 12px; }
.sk-map { height: clamp(220px, 34dvh, 320px); border-radius: 26px 26px 0 0; }
.sk-facts { display: flex; gap: 8px; padding: 10px; border-radius: 14px; background: #fff; }
.sk-fact { flex: 1; height: 42px; border-radius: 10px; }
.sk-stop { display: flex; align-items: center; gap: 12px; padding: 14px; border-radius: 16px; background: #fff; }
.sk-dot { width: 26px; height: 26px; border-radius: 50%; flex: none; }
.sk-lines { flex: 1; display: flex; flex-direction: column; gap: 8px; }
@media (prefers-reduced-motion: reduce) { .sk { animation: none; } }

</style>

<style scoped>
.scenic-load-error{position:absolute;inset:64px 0 0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;background:#fff;z-index:40}
.scenic-load-error button{border:0;border-radius:12px;padding:12px 24px;background:#eee8ff;color:#282332}
</style>
