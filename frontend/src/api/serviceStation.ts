import { request_handler } from './base'
import type { RouteOverviewData, VisualContext } from './tourExperience'

export interface StationGuide {
  guide_id: number
  name: string
  poster_image: string
  render_mode: string
}
export interface StationFacility {
  key: string
  name: string
  name_en: string
  kind: string
  anchor_key: string
  verified: boolean
  status: string
  source: string
}
export interface StationInfo {
  station_id: string
  name: string
  name_en: string
  location: string
  location_en: string
  anchor: { node_id: number; latitude: number; longitude: number; label: string; label_en?: string }
  default_language: 'zh' | 'en'
  welcome: string
  welcome_en: string
  idle_seconds: number
  volume: number
  revision: number
  demo: boolean
  announcements: Array<{ text: string; text_en: string; expires_at: string }>
  facilities: StationFacility[]
}
export interface StationSpot {
  spot_id: number
  spot_name: string
  category: string
  description: string
  history_detail: string
  photo_tips: string
  tour_tips: string
  service_facilities: string
  image_path: string
  visit_duration: number
  location: string
}
export interface StationCatalog {
  station: StationInfo
  guide: StationGuide | null
  spots: StationSpot[]
  network_version: string
  catalog_version?: string
}
export interface StationVisit {
  visit_id: string
  access_token: string
  expires_at: string
}
export interface StationPlanningInput {
  budget: number
  end_area: 'east' | 'north' | 'south' | 'return'
  avoid_steps: boolean
  spot_ids: number[]
  language: 'zh' | 'en'
}
// Older saved itineraries and mobile handoffs retain these response fields.
export interface StationPreferences extends StationPlanningInput {
  pace: 'standard' | 'relaxed'
  interest: 'all' | 'history' | 'nature' | 'photo' | 'family'
}
export interface StationPlan {
  plan_id: string
  kind: string
  title: string
  title_en: string
  route: RouteOverviewData
  preferences: StationPreferences
  station: StationInfo
  guide: StationGuide | null
  generated_at: string
  network_version: string
  version: number
}
export interface StationReply {
  needs_end_area?: boolean
  end_area_confirmed?: boolean
  plans?: StationPlan[]
  answer: string
  actions: string[]
  visuals?: VisualContext | null
  spot_id?: number
  preferences: StationPreferences
  source: string
  destination_key?: string | null
}
export const defaultStationPlanningInput = (): StationPlanningInput => ({
  budget: 120,
  end_area: 'east',
  avoid_steps: false,
  spot_ids: [],
  language: 'zh'
})
export const defaultStationPreferences = (): StationPreferences => ({
  ...defaultStationPlanningInput(),
  pace: 'standard',
  interest: 'all'
})

export function stationError(error: unknown): string {
  const detail = (error as any)?.response?.data?.detail
  return typeof detail === 'string' ? detail : '服务暂不可用，请重试'
}
export function getStation(id: string, signal?: AbortSignal) {
  return request_handler
    .get<StationCatalog>('/service-stations/public/' + id, { signal, timeout: 12000 })
    .then((r) => r.data)
}
export function heartbeatStation(id: string) {
  return request_handler
    .post<{
      revision: number
      network_version: string
      catalog_version?: string
    }>('/service-stations/public/' + id + '/heartbeat', {}, { timeout: 8000 })
    .then((r) => r.data)
}
export function beginStationVisit(id: string, language: string, signal?: AbortSignal) {
  return request_handler
    .post<StationVisit>(
      '/service-stations/public/' + id + '/visits',
      { language },
      { signal, timeout: 10000 }
    )
    .then((r) => r.data)
}
function headers(visit: StationVisit) {
  return { 'X-Station-Token': visit.access_token }
}
export function endStationVisit(visit: StationVisit) {
  return request_handler.post(
    '/service-stations/visits/' + visit.visit_id + '/end',
    {},
    { headers: headers(visit), timeout: 8000 }
  )
}
export function extendStationVisit(visit: StationVisit) {
  return request_handler.post(
    '/service-stations/visits/' + visit.visit_id + '/extend',
    {},
    { headers: headers(visit), timeout: 8000 }
  )
}
export function planAtStation(
  visit: StationVisit,
  prefs: StationPlanningInput,
  signal?: AbortSignal
) {
  return request_handler
    .post<{
      plans: StationPlan[]
    }>('/service-stations/visits/' + visit.visit_id + '/plans', prefs, {
      headers: headers(visit),
      signal,
      timeout: 20000
    })
    .then((r) => r.data)
}
export function consultStation(
  visit: StationVisit,
  data: {
    question: string
    language: string
    preferences: StationPlanningInput
    end_area_confirmed?: boolean
    awaiting_end_area?: boolean
    spot_id?: number
    plan_id?: string
  },
  signal?: AbortSignal
) {
  return request_handler
    .post<StationReply>('/service-stations/visits/' + visit.visit_id + '/chat', data, {
      headers: headers(visit),
      signal,
      timeout: 22000
    })
    .then((r) => r.data)
}
export function speakAtStation(visit: StationVisit, language: string, signal?: AbortSignal) {
  return request_handler
    .post<Blob>(
      '/service-stations/visits/' + visit.visit_id + '/speech',
      { language },
      { headers: headers(visit), signal, timeout: 20000, responseType: 'blob' }
    )
    .then((r) => r.data)
}
export function shareStationPlan(visit: StationVisit, plan_id: string, signal?: AbortSignal) {
  return request_handler
    .post<{
      token: string
      pickup_code: string
      expires_at: string
    }>(
      '/service-stations/visits/' + visit.visit_id + '/share',
      { plan_id },
      { headers: headers(visit), signal, timeout: 10000 }
    )
    .then((r) => r.data)
}
export interface StationDirections {
  meters: number
  minutes: number
  geometry: number[][]
  origin: StationInfo['anchor']
  destination: StationInfo['anchor']
  has_steps: boolean
  sections: Array<{ road_name: string; meters: number; steps: boolean }>
}
export function stationDirections(id: string, key: string, signal?: AbortSignal) {
  return request_handler
    .post<StationDirections>(
      '/service-stations/public/' + id + '/directions',
      { key },
      { signal, timeout: 10000 }
    )
    .then((r) => r.data)
}
export function previewStationClaim(token: string, receipt: string) {
  return request_handler
    .post<{
      snapshot: StationPlan
      session_id: number | null
      expires_at: string
    }>('/service-stations/claim/preview', { token, receipt }, { timeout: 10000 })
    .then((r) => r.data)
}
export function receiveStationClaim(token: string, receipt: string) {
  return request_handler
    .post<{
      session_id: number
      avatar_access_token?: string
    }>('/service-stations/claim/receive', { token, receipt }, { timeout: 15000 })
    .then((r) => r.data)
}

export interface StationAdmin extends Omit<StationInfo, 'anchor'> {
  anchor_key: string
  guide_id: number
  enabled: boolean
  last_seen: string | null
  updated_at: string
}
export interface StationAdminData {
  stations: StationAdmin[]
  anchors: Array<{ key: string; label: string; latitude: number; longitude: number }>
  guides: StationGuide[]
}
export async function listStationAdmin() {
  const { header_authorization } = await import('./user')
  return request_handler
    .get<StationAdminData>('/service-stations/admin', {
      headers: { Authorization: header_authorization.value }
    })
    .then((r) => r.data)
}
export async function saveStationAdmin(
  id: string,
  data: StationAdmin & { location_checked?: boolean }
) {
  const { header_authorization } = await import('./user')
  return request_handler
    .put<StationAdmin>('/service-stations/admin/' + id, data, {
      headers: { Authorization: header_authorization.value },
      timeout: 10000
    })
    .then((r) => r.data)
}

export function stationShareStatus(visit: StationVisit, token: string) {
  return request_handler
    .post<{
      status: 'waiting' | 'received' | 'expired'
    }>('/service-stations/visits/' + visit.visit_id + '/share-status', { token }, { headers: headers(visit), timeout: 8000 })
    .then((r) => r.data)
}
