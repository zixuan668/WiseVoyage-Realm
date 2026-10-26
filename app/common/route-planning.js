import { BASE_URL } from './config.js'
import { wgs84ToGcj02 } from '../../shared/coordinates.js'

export function selectedOrder(order, selected) {
  const available = new Set(Object.keys(selected).filter(id => selected[id]).map(Number))
  return [...new Set([...order, ...available])].filter(id => available.has(id))
}
export function moveStop(ids, id, direction) {
  const result = ids.slice(), index = result.indexOf(id), target = index + direction
  if (index >= 0 && target >= 0 && target < result.length) [result[index], result[target]] = [result[target], result[index]]
  return result
}
export function previewOptions(ids, plan, pace) {
  return { spot_ids: ids.slice(), pace: plan?.pace || pace || 'standard', start_area: plan?.start_area || 'auto',
    end_area: plan?.end_area || 'auto', avoid_steps: !!(plan?.avoid_steps ?? (pace === 'relaxed')),
    reserve: plan?.queue_reserve_minutes || 0 }
}
export function routeRequest(path, data, sid = 0, timeout = 20000) {
  let task
  const promise = new Promise((resolve, reject) => {
    const token = uni.getStorageSync('token'), access = sid && uni.getStorageSync('xingyun-tour-' + sid)
    const header = { 'Content-Type': 'application/json' }
    if (token) header.Authorization = 'Bearer ' + token
    if (access) header['X-Tour-Access'] = access
    task = uni.request({ url: BASE_URL + path, method: 'POST', data, header, timeout,
      success(response) {
        if (response.statusCode === 200 && response.data?.success) { resolve(response.data.data); return }
        const detail = response.data?.detail || response.data?.message
        const error = new Error(typeof detail === 'string' ? detail : '路线服务暂不可用，请稍后重试')
        error.status = response.statusCode
        reject(error)
      }, fail(error) { reject(new Error(/abort/i.test(error.errMsg || '') ? 'cancelled' : '路线请求失败，请检查网络')) },
    })
  })
  return { promise, abort() { task?.abort() } }
}
export function roadMap(overview) {
  const stops = overview?.stops || []
  const markers = stops.flatMap((stop, index) => {
    const lat = stop.access_latitude ?? stop.latitude, lng = stop.access_longitude ?? stop.longitude
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return []
    const point = wgs84ToGcj02(lat, lng)
    return [{ id: index + 1, latitude: point[0], longitude: point[1], width: 26, height: 26,
      iconPath: '/static/pin-blue.png', label: { content: String(index + 1), color: '#4338ca', fontSize: 12 } }]
  })
  const legs = [overview?.entry_leg, ...(overview?.legs || []), overview?.exit_leg].filter(Boolean)
  const legIndexes = []
  const polyline = legs.flatMap((leg, index) => {
    if (leg.available === false || !Array.isArray(leg.geometry) || leg.geometry.length < 2 ||
      !leg.geometry.every(p => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite) && Math.abs(p[0]) <= 90 && Math.abs(p[1]) <= 180)) return []
    legIndexes.push(index)
    return [{ points: leg.geometry.map(p => { const point = wgs84ToGcj02(p[0], p[1]); return { latitude: point[0], longitude: point[1] } }), color: '#6554b9', width: 5 }]
  })
  for (const [key, id] of [['entry_anchor', 1001], ['exit_anchor', 1002]]) {
    const gate = overview?.[key]
    if (Number.isFinite(gate?.latitude) && Number.isFinite(gate?.longitude)) {
      const point = wgs84ToGcj02(gate.latitude, gate.longitude)
      markers.push({ id, latitude: point[0], longitude: point[1], iconPath: '/static/pin-red.png', width: 26, height: 26,
        callout: { content: gate.label, display: 'BYCLICK' } })
    }
  }
  const points = polyline.flatMap(line => line.points).concat(markers.map(m => ({ latitude: m.latitude, longitude: m.longitude })))
  return { markers, polyline, points, legIndexes, center: points[0] || { latitude: 39.997, longitude: 116.269 } }
}
export function routeChangeText(message) {
  return String(message || '').replace(/(?:不要|不用|不想|别)\s*(?:跳过|离园|少走|避开)|(?:do not|don't|don’t)\s+(?:skip|leave|avoid)|not tired/gi, '')
}
export function isRouteChange(message) {
  return !/不(?:需要|用|要)调整|不用改|不累|not tired|do not replan/i.test(message) &&
    /只剩|还剩|剩下|提前离园|早点离园|准备离园|现在离园|我要离园|回出口|调整路线|改.*路线|少走|走不动|累了|跳过|不去|不想去|不想爬|避开|minutes? left|hours? left|tired|skip|replan|leave early|leave now|head to (?:an? )?exit|less walking|avoid stairs/i.test(routeChangeText(message))
}
export function repairDefaults(live, now = Date.now()) {
  let prefs = {}; try { prefs = JSON.parse(live.visitor_preferences || '{}') } catch (_) {}
  const plan = prefs.last_replan || prefs.planning || {}
  const started = prefs.last_replan?.applied_at ? prefs.last_replan.applied_at * 1000 : Date.parse(live.start_time || '')
  const initial = prefs.last_replan?.remaining_minutes ?? plan.time_budget_minutes
  return { minutes: initial ? Math.max(1, Math.floor(initial - (Number.isFinite(started) ? (now - started) / 60000 : 0))) : '',
    pace: plan.pace || 'standard', end: plan.end_area || 'auto',
    avoidSteps: plan.avoid_steps ?? plan.pace === 'relaxed', required: plan.required_spot_ids || [] }
}
