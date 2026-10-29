import { House, ServiceStation, Guide, Gauge, DataAnalysis, ChatDotRound, MapLocation, Location, Notebook, RouteIcon, User } from '@/icons'
import type { Component } from 'vue'

export interface AdminDestination {
  path: string
  label: string
  group?: string
  icon: Component
  prefixes: string[]
}

export const adminGroups = [
  { key: '/analytics', label: '感受度分析', icon: Gauge },
  { key: '/scenic-spot', label: '景点管理', icon: MapLocation },
  { key: '/personalization', label: '导览配置', icon: Guide },
]

// This is the existing administrator menu, not an inventory of all router records or business actions.
export const adminDestinations: AdminDestination[] = [
  { path: '/home', label: '综合看板', icon: House, prefixes: ['/home'] },
  { path: '/tour-session/overview', label: '游览AI分析', group: '/analytics', icon: DataAnalysis, prefixes: ['/tour-session'] },
  { path: '/analytics/feedback', label: '游客反馈分析', group: '/analytics', icon: ChatDotRound, prefixes: ['/analytics/feedback'] },
  { path: '/stations', label: '服务站管理', icon: ServiceStation, prefixes: ['/stations'] },
  { path: '/scenic-spot/list', label: '景点档案', group: '/scenic-spot', icon: Location, prefixes: ['/scenic-spot'] },
  { path: '/knowledge/list', label: '景区知识', group: '/scenic-spot', icon: Notebook, prefixes: ['/knowledge'] },
  { path: '/tour-route/list', label: '默认路线管理', group: '/personalization', icon: RouteIcon, prefixes: ['/tour-route'] },
  { path: '/digital-guide/list', label: '数字人形象管理', group: '/personalization', icon: User, prefixes: ['/digital-guide'] },
]

export function activeAdminDestination(path: string) {
  return adminDestinations.find(item => item.prefixes.some(prefix => path === prefix || path.startsWith(prefix + '/')))
}
