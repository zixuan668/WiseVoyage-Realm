// 数据库存储 WGS-84 坐标，高德瓦片采用 GCJ-02；展示前转换，避免标记整体偏移。
const MAP_PI = Math.PI
const MAP_A = 6378245.0
const MAP_EE = 0.00669342162296594323
const outOfChina = (lat, lng) => lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
function transformLat(lng, lat) {
  let ret = -100 + 2 * lng + 3 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * Math.sqrt(Math.abs(lng))
  ret += (20 * Math.sin(6 * lng * MAP_PI) + 20 * Math.sin(2 * lng * MAP_PI)) * 2 / 3
  ret += (20 * Math.sin(lat * MAP_PI) + 40 * Math.sin(lat / 3 * MAP_PI)) * 2 / 3
  ret += (160 * Math.sin(lat / 12 * MAP_PI) + 320 * Math.sin(lat * MAP_PI / 30)) * 2 / 3
  return ret
}
function transformLng(lng, lat) {
  let ret = 300 + lng + 2 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * Math.sqrt(Math.abs(lng))
  ret += (20 * Math.sin(6 * lng * MAP_PI) + 20 * Math.sin(2 * lng * MAP_PI)) * 2 / 3
  ret += (20 * Math.sin(lng * MAP_PI) + 40 * Math.sin(lng / 3 * MAP_PI)) * 2 / 3
  ret += (150 * Math.sin(lng / 12 * MAP_PI) + 300 * Math.sin(lng / 30 * MAP_PI)) * 2 / 3
  return ret
}
export function wgs84ToGcj02(lat, lng) {
  if (outOfChina(lat, lng)) return [lat, lng]
  let dLat = transformLat(lng - 105, lat - 35)
  let dLng = transformLng(lng - 105, lat - 35)
  const radLat = lat / 180 * MAP_PI
  let magic = Math.sin(radLat)
  magic = 1 - MAP_EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180) / ((MAP_A * (1 - MAP_EE)) / (magic * sqrtMagic) * MAP_PI)
  dLng = (dLng * 180) / (MAP_A / sqrtMagic * Math.cos(radLat) * MAP_PI)
  return [lat + dLat, lng + dLng]
}

// 使用迭代逆变换，使 GCJ02 定位与后端 WGS84 距离计算保持一致。
export function gcj02ToWgs84(lat, lng) {
  if (outOfChina(lat, lng)) return [lat, lng]
  let wLat = lat, wLng = lng
  for (let i = 0; i < 8; i++) {
    const [projectedLat, projectedLng] = wgs84ToGcj02(wLat, wLng)
    const dLat = projectedLat - lat, dLng = projectedLng - lng
    wLat -= dLat; wLng -= dLng
    if (Math.max(Math.abs(dLat), Math.abs(dLng)) < 1e-9) break
  }
  return [wLat, wLng]
}
