import { House, Reading, ServiceStation, Guide, DataAnalysis } from '@/icons'
import type { Component } from 'vue'

export interface AdminDestination {
  path: string
  label: string
  group?: string
  icon: Component
  prefixes: string[]
}

export const adminGroups = [
  { key: '/scenic-spot', label: '知识库管理', icon: Reading, caption: '管理模块' },
  { key: '/personalization', label: '个性化导览管理', icon: Guide },
  { key: '/analytics', label: '感受度分析', icon: DataAnalysis, caption: '洞察中心' },
]

// This is the existing administrator menu, not an inventory of all router records or business actions.
export const adminDestinations: AdminDestination[] = [
  { path: '/home', label: '综合看板', icon: House, prefixes: ['/home'] },
  { path: '/stations', label: '服务站管理', icon: ServiceStation, prefixes: ['/stations'] },
  { path: '/scenic-spot/list', label: '景点档案', group: '/scenic-spot', icon: Reading, prefixes: ['/scenic-spot'] },
  { path: '/knowledge/list', label: '景区知识', group: '/scenic-spot', icon: Reading, prefixes: ['/knowledge'] },
  { path: '/tour-route/list', label: '默认路线管理', group: '/personalization', icon: Guide, prefixes: ['/tour-route'] },
  { path: '/digital-guide/list', label: '数字人形象管理', group: '/personalization', icon: Guide, prefixes: ['/digital-guide'] },
  { path: '/tour-session/overview', label: '游览AI分析', group: '/analytics', icon: DataAnalysis, prefixes: ['/tour-session'] },
  { path: '/analytics/feedback', label: '游客反馈分析', group: '/analytics', icon: DataAnalysis, prefixes: ['/analytics/feedback'] },
]

export function activeAdminDestination(path: string) {
  return adminDestinations.find(item => item.prefixes.some(prefix => path === prefix || path.startsWith(prefix + '/')))
}

