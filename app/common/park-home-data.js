import { BASE_URL, assetUrl } from './config.js'
import stepSnapshot from '../static/park-home/step-segments.json'
import routeCovers from '../static/route-covers/manifest.json'

export const GUIDE_URL = 'https://www.summerpalace.net.cn/guide_map.html'
export const ACCESS_URL = 'https://summerpalace.net.cn/single/detail/508.html'
export const HOURS_URL = 'https://www.summerpalace.net.cn/visit.html'
export const CHECKED_AT = '2026-11-15'

export const ACCESS_ROUTES = [
  { title: '平缓环线', detail: '东宫门 → 仁寿殿 → 知春亭 → 东堤 → 南如意门 → 西门 → 北如意门 → 石舫 → 长廊 → 乐寿堂 → 东宫门', meters: 6962 },
  { title: '后山环线', detail: '东宫门 → 仁寿殿 → 乐寿堂 → 长廊 → 石舫 → 半壁新桥 → 后山中御路 → 紫气东来城关 → 德和园东夹道 → 东宫门', meters: 2565 },
]

export const FACILITIES = [
  {
    id: 'visitor-east', kind: 'facility', type: '游客服务中心', name: '东宫门游客服务中心',
    latitude: 39.9966755, longitude: 116.2755965, entrance: '东宫门',
    location: '定位到东宫门入口附近，中心位置请看门区指引。',
    hours: '官网未单列服务中心开放时间，可向景区咨询。',
    source: ACCESS_URL, checkedAt: CHECKED_AT,
  },
  {
    id: 'toilet-wenchang', kind: 'facility', type: '卫生间', name: '文昌阁码头附近卫生间',
    latitude: 39.99532853294191, longitude: 116.27397603587181,
    entrance: '东宫门或新建宫门', location: '地图定位到文昌阁地标。卫生间的具体入口请查看官方导览图或现场指引。',
    hours: '官网未单列设施开放时间。', source: GUIDE_URL, checkedAt: CHECKED_AT,
  },
  {
    id: 'third-east', kind: 'facility', type: '第三卫生间', name: '东宫门区域第三卫生间',
    latitude: 39.9966755, longitude: 116.2755965,
    entrance: '东宫门', location: '地图定位到东宫门入口。第三卫生间的具体位置请查看官方导览图或现场指引。',
    hours: '官网未单列设施开放时间。', source: GUIDE_URL, checkedAt: CHECKED_AT,
  },
]
export const STEP_SOURCE = { url: stepSnapshot.source, date: stepSnapshot.date }
export const STEP_LINES = stepSnapshot.lines

export function homeRoutes(routes, spots) {
  const priority = ['昆明湖摄影漫游线', '皇家园林经典文化线', '亲子湖山体验线']
  return [...routes]
    .sort((a, b) => (priority.includes(a.name) ? priority.indexOf(a.name) : priority.length) -
      (priority.includes(b.name) ? priority.indexOf(b.name) : priority.length))
    .slice(0, 3)
    .map(route => ({
      ...route,
      image: routeCovers.routes[route.name]?.asset || assetUrl(route.cover_image),
      stops: (route.spot_ids || []).map(id => spots.find(spot => spot.spot_id === id)?.spot_name).filter(Boolean),
    }))
}

export function scenicMarkers(spots) {
  return spots
    .filter(spot => Number.isFinite(spot.latitude) && Number.isFinite(spot.longitude))
    .map(spot => ({ id: 'spot-' + spot.spot_id, kind: 'scenic', name: spot.spot_name,
      latitude: spot.latitude, longitude: spot.longitude, spot }))
}

function request(url, options = {}) {
  return new Promise((resolve, reject) => uni.request({
    url, timeout: 8500, ...options,
    success: result => result.statusCode === 200 ? resolve(result.data) : reject(new Error('数据暂不可用')),
    fail: reject,
  }))
}

export async function featuredRoads(ids) {
  if (ids.length < 2) return []
  const response = await request(BASE_URL + '/tour-experience/route-preview', {
    method: 'POST', data: { spot_ids: ids },
  })
  if (!response?.success) return []
  return (response.data?.legs || [])
    .filter(leg => leg.available !== false && leg.geometry?.length >= 2)
    .map(leg => ({ kind: 'featured', path: leg.geometry }))
}

export async function accessibleRoads(spots) {
  const names = ['仁寿殿', '乐寿堂', '长廊', '石舫']
  const ids = names.map(name => spots.find(spot => spot.spot_name === name)?.spot_id)
  if (ids.some(id => !id)) return []
  const response = await request(BASE_URL + '/tour-experience/route-preview', {
    method: 'POST', data: { spot_ids: ids, avoid_steps: true, start_area: 'east' },
  })
  const plan = response?.data
  if (!response?.success || !plan?.complete) return []
  return [plan.entry_leg, ...plan.legs]
    .filter(leg => leg?.available && !leg.has_steps && leg.geometry?.length >= 2)
    .map(leg => ({ kind: 'accessible', path: leg.geometry }))
}

export function weatherLabel(code) {
  if (code === 0) return { title: '晴', icon: '☀' }
  if (code < 3) return { title: '多云', icon: '⛅' }
  if (code === 3) return { title: '阴', icon: '☁' }
  if (code < 50) return { title: '雾', icon: '≋' }
  if (code >= 95) return { title: '雷雨', icon: 'ϟ' }
  if ((code >= 71 && code <= 77) || code >= 85) return { title: '雪', icon: '❄' }
  return { title: '有雨', icon: '☂' }
}

export const WEATHER_REFRESH_MS = 15 * 60 * 1000
const HOUR_MS = 60 * 60 * 1000
const parkTime = value => typeof value === 'string' ? Date.parse(value + '+08:00') : NaN

let weatherCache
export async function loadParkWeather() {
  const requestedAt = Date.now()
  if (weatherCache && requestedAt - weatherCache.at < WEATHER_REFRESH_MS) return weatherCache.value
  const location = 'latitude=39.996&longitude=116.270&timezone=Asia%2FShanghai'
  // A deployment may use a same-origin proxy for the weather feed.
  const proxy = (import.meta.env.VITE_APP_PARK_WEATHER_PROXY || '').replace(/\/$/, '')
  const forecastBase = proxy ? proxy + '/forecast' : 'https://api.open-meteo.com/v1/forecast'
  const forecastUrl = forecastBase + '?' + location +
    '&current=temperature_2m,weather_code&hourly=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min,sunset&forecast_days=2'
  const forecast = await request(forecastUrl)
  const current = forecast.current
  const now = Date.now()
  const observedAt = parkTime(current?.time)
  if (!Number.isFinite(current?.temperature_2m) || !Number.isFinite(observedAt) || Math.abs(now - observedAt) > 1.5 * HOUR_MS) {
    throw new Error('天气暂不可用')
  }
  const next = forecast.hourly?.time?.findIndex(time => time > current.time) ?? -1
  const hours = [{ time: '现在', temperature: current.temperature_2m, ...weatherLabel(current.weather_code) }]
  if (next >= 0) {
    forecast.hourly.time.slice(next, next + 3).forEach((time, index) => {
      hours.push({ time: time.slice(11, 13) + '时', temperature: forecast.hourly.temperature_2m[next + index],
        ...weatherLabel(forecast.hourly.weather_code[next + index]) })
    })
  }
  const value = {
    ...weatherLabel(current.weather_code), temperature: current.temperature_2m,
    high: forecast.daily?.temperature_2m_max?.[0], low: forecast.daily?.temperature_2m_min?.[0],
    sunset: forecast.daily?.sunset?.[0]?.slice(11, 16), hours, observedAt,
  }
  weatherCache = { at: requestedAt, value }
  return value
}
