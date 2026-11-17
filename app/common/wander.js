export const WANDER_SESSION = 'app-wander'

export function routeLegs(route) {
  return [route?.entry_leg, ...(route?.legs || []), route?.exit_leg].filter(Boolean)
}

export function walkingDistance(meters, t) {
  if (!Number.isFinite(meters)) return '—'
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)} ${t('公里')}` : `${Math.round(meters)} ${t('米')}`
}

export function blindPreviewMap(map, overview) {
  const inboundCount = routeLegs({ ...overview, exit_leg: null }).length
  const lines = map.polyline.map((line, index) => ({ ...line, leg: map.legIndexes[index] }))
    .filter(line => line.leg < inboundCount)
  const distance = (a, b) => Math.hypot((a.latitude - b.latitude) * 111320,
    (a.longitude - b.longitude) * 111320 * Math.cos(a.latitude * Math.PI / 180))
  const total = lines.reduce((sum, line) => sum + line.points.slice(1)
    .reduce((meters, point, index) => meters + distance(line.points[index], point), 0), 0)
  // Leave the last part of the route out of the preview and its map bounds.
  let remaining = Math.max(0, Math.min(total * 0.7, total - 160))
  let reachedStops = overview?.entry_leg ? 0 : 1
  const polyline = [], legIndexes = []
  for (const line of lines) {
    if (remaining <= 0) break
    const shown = line.points.slice(0, 1)
    for (const point of line.points.slice(1)) {
      const previous = shown[shown.length - 1]
      const meters = distance(previous, point)
      if (meters > remaining) {
        const fraction = remaining / meters
        shown.push({ latitude: previous.latitude + (point.latitude - previous.latitude) * fraction,
          longitude: previous.longitude + (point.longitude - previous.longitude) * fraction })
        remaining = 0
        break
      }
      shown.push(point)
      remaining -= meters
    }
    if (remaining > 0) reachedStops = line.leg + (overview?.entry_leg ? 1 : 2)
    polyline.push({ points: shown })
    legIndexes.push(line.leg)
  }
  const markers = map.markers.filter(marker => marker.id === 1001 ||
    (marker.id <= reachedStops && marker.id < (overview?.stops?.length || 0)))
  const points = polyline.flatMap(line => line.points).concat(markers.map(({ latitude, longitude }) => ({ latitude, longitude })))
  const publicCenter = { latitude: 39.997, longitude: 116.269 }
  return { polyline, legIndexes, markers, points: points.length ? points : [publicCenter], center: points[0] || publicCenter }
}
