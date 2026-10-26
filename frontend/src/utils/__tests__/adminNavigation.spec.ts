import { describe, it, expect } from 'vitest'
import { adminDestinations, activeAdminDestination, adminGroups } from '../adminNavigation'

describe('administrator sidebar destinations', () => {
  it('preserves the existing eight unique menu destinations without station visitor pages', () => {
    expect(adminDestinations).toHaveLength(8)
    expect(new Set(adminDestinations.map(item => item.path)).size).toBe(8)
    expect(adminDestinations.every(item => !item.path.startsWith('/station/'))).toBe(true)
    expect(adminDestinations.filter(item => !item.group).map(item => item.path)).toEqual(['/home', '/stations'])
  })
  it('maps edit/create/detail routes back to their existing sidebar destination', () => {
    expect(activeAdminDestination('/scenic-spot/12/edit')?.path).toBe('/scenic-spot/list')
    expect(activeAdminDestination('/scenic-spot/create')?.group).toBe('/scenic-spot')
    expect(activeAdminDestination('/tour-session/77/detail')?.path).toBe('/tour-session/overview')
    expect(activeAdminDestination('/knowledge/list')?.group).toBe('/scenic-spot')
    expect(activeAdminDestination('/scenic-spotlight')).toBeUndefined()
  })
  it('retains the existing three two-child groups', () => {
    expect(adminGroups).toHaveLength(3)
    for (const group of adminGroups) expect(adminDestinations.filter(item => item.group === group.key)).toHaveLength(2)
  })
})
