import type { RouteOverviewData, WalkingLeg } from '@/api/tourExperience'
import { wgs84ToGcj02 } from '../../../shared/coordinates.js'

/** Never manufacture a straight connector when a road geometry is unavailable. */
export function roadPoints(leg?: WalkingLeg | null): number[][] {
  if (!leg || leg.available === false || !leg.geometry || leg.geometry.length < 2) return []
  if (!leg.geometry.every(p => p.length === 2 && p.every(Number.isFinite) && Math.abs(p[0]) <= 90 && Math.abs(p[1]) <= 180)) return []
  return leg.geometry.map(p => wgs84ToGcj02(p[0], p[1]))
}
export function routeLegs(route?: RouteOverviewData | null): WalkingLeg[] {
  return route ? [...(route.entry_leg ? [route.entry_leg] : []), ...route.legs, ...(route.exit_leg ? [route.exit_leg] : [])] : []
}
export function roadPaths(route?: RouteOverviewData | null): number[][][] {
  return routeLegs(route).map(roadPoints).filter(points => points.length > 1)
}
