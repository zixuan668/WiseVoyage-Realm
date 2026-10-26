// 依据接口返回的景区归属及坐标排序，不改变路线内部的游览顺序。
export function prioritizeSummerPalace(spots, routes) {
  const belongs = s => /颐和园/.test((s.location || '') + (s.description || '') + (s.spot_name || ''))
  const located = s => Number(s.latitude) && Number(s.longitude)
  const anchors = spots.filter(s => belongs(s) && located(s))
  const center = anchors.length ? {
    latitude: anchors.reduce((n, s) => n + Number(s.latitude), 0) / anchors.length,
    longitude: anchors.reduce((n, s) => n + Number(s.longitude), 0) / anchors.length,
  } : null
  const distance = s => center && located(s)
    ? Math.hypot(Number(s.latitude) - center.latitude, (Number(s.longitude) - center.longitude) * Math.cos(center.latitude * Math.PI / 180))
    : Infinity
  const ordered = spots.slice().sort((a, b) => Number(belongs(b)) - Number(belongs(a)) || distance(a) - distance(b))
  const byId = new Map(spots.map(s => [s.spot_id, s]))
  const routeDistance = r => {
    const members = (r.spot_ids || []).map(id => byId.get(id)).filter(Boolean)
    return members.length ? members.reduce((n, s) => n + distance(s), 0) / members.length : Infinity
  }
  return { spots: ordered, routes: routes.slice().sort((a, b) => routeDistance(a) - routeDistance(b)) }
}
