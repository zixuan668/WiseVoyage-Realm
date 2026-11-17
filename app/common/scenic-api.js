import { SERVER_ORIGIN } from './config.js'

const MAX_AGE = 60000
const pendingCatalogs = new Map()
const cacheKey = () => 'native-scenic-catalog-v1:' + SERVER_ORIGIN
export function scenicContext() { return SERVER_ORIGIN + '|' + (uni.getStorageSync('token') || '') }

export function scenicRequest(path, options = {}) {
  const token = uni.getStorageSync('token') || '', context = scenicContext()
  return new Promise((resolve, reject) => {
    uni.request({url: SERVER_ORIGIN + '/tour-experience' + path, method: options.method || 'GET', data: options.data,
      timeout: 15000, header: {'Content-Type':'application/json', ...(token ? {Authorization:'Bearer '+token} : {})},
      success(response) {
        if (context !== scenicContext()) { reject(new Error('账号或服务已切换')); return }
        if (response.statusCode >= 200 && response.statusCode < 300 && response.data?.success !== false) { resolve(response.data); return }
        const body = response.data || {}, detail = body.detail || body.message
        const error = new Error(typeof detail === 'string' ? detail : '景点服务暂不可用，请重试')
        error.statusCode = response.statusCode
        reject(error)
      }, fail() { reject(new Error('网络连接失败，请重试')) },
    })
  })
}
export function readScenicCatalog() {
  try {
    const value = uni.getStorageSync(cacheKey()), age = Date.now() - value?.savedAt
    if (!Number.isFinite(age) || age < 0 || age > MAX_AGE || !Array.isArray(value?.places)) return []
    return value.places.filter(p => p && p.park === 'summer-palace' && Number.isInteger(p.id) && typeof p.name === 'string')
  } catch (_) { return [] }
}
export function loadScenicCatalog() {
  const origin = SERVER_ORIGIN, context = scenicContext()
  if (pendingCatalogs.has(context)) return pendingCatalogs.get(context)
  const promise = scenicRequest('/scenic-catalog').then(data => {
    if (!Array.isArray(data)) throw new Error('景点数据格式错误')
    const places = data.filter(p => p && p.park === 'summer-palace' && Number.isInteger(p.id) && typeof p.name === 'string')
    if (origin === SERVER_ORIGIN) try { uni.setStorageSync(cacheKey(), {savedAt:Date.now(),places}) } catch (_) {}
    return places
  }).finally(() => pendingCatalogs.delete(context))
  pendingCatalogs.set(context, promise)
  return promise
}

export async function loadScenicDraft() {
  const context = scenicContext()
  const stops = await scenicRequest('/scenic-selection')
  if (context !== scenicContext()) throw new Error('账号或服务已切换')
  const settings = await scenicRequest('/scenic-settings')
  if (!Array.isArray(stops) || !settings || !Array.isArray(settings.spot_ids)) throw new Error('行程数据格式错误')
  return {stops, settings}
}

export function nativeCompanionUrl(ids, plan = {}) {
  if (!Array.isArray(ids) || !ids.length || ids.length > 20 || new Set(ids).size !== ids.length || ids.some(id => !Number.isInteger(id) || id <= 0)) throw new Error('所选景点不可用')
  const areas = ['auto','east','north','south']
  return '/pages/tour-guide/tour-guide?nativePlan=1&spotIds=' + ids.join(',')
    + '&startArea=' + (areas.includes(plan.start_area) ? plan.start_area : 'auto')
    + '&endArea=' + (areas.includes(plan.end_area) ? plan.end_area : 'auto')
    + '&avoidSteps=' + (plan.avoid_steps ? '1' : '0') + '&pace=' + (plan.pace === 'relaxed' ? 'relaxed' : 'standard')
    + '&autoStart=1'
}
export function parseNativePlan(query) {
  if (query?.nativePlan !== '1') return null
  const ids = String(query.spotIds || '').split(',').map(Number)
  if (!ids.length || ids.length > 20 || new Set(ids).size !== ids.length || ids.some(id => !Number.isInteger(id) || id <= 0)) throw new Error('所选景点不可用')
  const areas = ['auto','east','north','south']
  return {spot_ids:ids, start_area:areas.includes(query.startArea)?query.startArea:'auto',
    end_area:areas.includes(query.endArea)?query.endArea:'auto', avoid_steps:query.avoidSteps === '1',pace:query.pace === 'relaxed'?'relaxed':'standard'}
}
export async function startTourSession(ids, planning = {}, pickedGuideId = 0) {
  const token = uni.getStorageSync('token') || ''
  if (!token) throw new Error('请先登录')
  const request = (path, options = {}) => new Promise((resolve, reject) => {
    uni.request({
      url: SERVER_ORIGIN + '/tour-session' + path,
      method: options.method || 'GET',
      data: options.data || {},
      timeout: 15000,
      header: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token, ...(options.headers || {}) },
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300) { resolve(response.data); return }
        const body = response.data || {}, detail = body.detail || body.message
        reject(new Error(typeof detail === 'string' ? detail : '服务暂不可用，请重试'))
      },
      fail() { reject(new Error('网络连接失败，请重试')) },
    })
  })
  const guides = await request('/guides?language=zh')
  const list = guides?.data?.guide_list || guides?.guide_list || []
  if (!list.length) throw new Error('暂无可用伴游')
  // 游客在「伴游选择」里挑的数字人优先，没挑时用默认第一位。
  const picked = list.find((guide) => Number(guide.guide_id) === Number(pickedGuideId))
  const guideId = (picked || list[0]).guide_id
  const payload = {
    preferences: ['comprehensive'],
    time_budget_minutes: Math.min(480, Math.max(15, Math.ceil(Number(planning.total_minutes) || 120))),
    pace: planning.pace === 'relaxed' ? 'relaxed' : 'standard',
    start_area: planning.start_area || 'auto',
    end_area: planning.end_area || 'auto',
    avoid_steps: !!planning.avoid_steps,
  }
  const created = await request('/visitor-create?name=' + encodeURIComponent('游客导览') + '&guide_id=' + guideId
    + '&visitor_preferences=' + encodeURIComponent('')
    + '&spot_ids=' + encodeURIComponent(JSON.stringify(ids || []))
    + '&planning=' + encodeURIComponent(JSON.stringify(payload)), { method: 'POST' })
  const body = created?.data || created || {}
  const sid = body.session_id
  if (!sid) throw new Error(body.message || '创建导览失败，请重试')
  const access = body.avatar_access_token || ''
  if (access) { try { uni.setStorageSync('xingyun-tour-' + sid, access) } catch (_) {} }
  await request('/start/' + sid, { method: 'PUT', headers: access ? { 'X-Tour-Access': access } : {} })
  return sid
}