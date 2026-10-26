import { describe, expect, it } from 'vitest'
import { wgs84ToGcj02, gcj02ToWgs84 } from '../../../../shared/coordinates.js'
import locations from '../../../../data/summer_palace_locations.json'

describe('景点坐标与底图', () => {
  it('仁寿殿 WGS84 在高德底图展示时只转换一次', () => {
    const spot = locations.spots['仁寿殿']
    const [lat, lng] = wgs84ToGcj02(spot.latitude, spot.longitude)
    expect(lat).toBeCloseTo(39.997750, 8)
    expect(lng).toBeCloseTo(116.280059, 8)
    expect(lng - spot.longitude).toBeGreaterThan(0.006)
  })
  it.each(Object.entries(locations.spots))('%s 的移动端定位还原为 GPS 后无坐标系距离偏差', (_name, spot) => {
    const gcj = wgs84ToGcj02(spot.latitude, spot.longitude)
    const gps = gcj02ToWgs84(...gcj)
    expect(gps[0]).toBeCloseTo(spot.latitude, 8)
    expect(gps[1]).toBeCloseTo(spot.longitude, 8)
  })
  it('境外坐标保持原值', () => {
    expect(wgs84ToGcj02(51.5, -0.12)).toEqual([51.5, -0.12])
    expect(gcj02ToWgs84(51.5, -0.12)).toEqual([51.5, -0.12])
  })
  it.each(Object.entries(locations.spots))('%s 转换后对应已核对的底图位置，缩放不改变地理坐标', (_name, spot) => {
    const [lat, lng] = wgs84ToGcj02(spot.latitude, spot.longitude)
    expect(lat).toBeCloseTo(spot.map_reference.latitude, 9)
    expect(lng).toBeCloseTo(spot.map_reference.longitude, 9)
    const { tile, pixel } = spot.map_reference
    const worldX = (lng + 180) / 360 * 2 ** tile.z * 256
    const worldY = (1 - Math.asinh(Math.tan(lat * Math.PI / 180)) / Math.PI) / 2 * 2 ** tile.z * 256
    expect(worldX - tile.x * 256).toBeCloseTo(pixel.x, 4)
    expect(worldY - tile.y * 256).toBeCloseTo(pixel.y, 4)
  })
  it('区域景点使用明确的步行节点，桥的锚点在桥面两端之间', () => {
    expect(locations.spots['昆明湖'].location).toContain('知春亭')
    expect(locations.spots['谐趣园'].location).toContain('宫门入口')
    expect(locations.spots['长廊'].location).toContain('廊道')
    const bridge = locations.spots['十七孔桥']
    expect(bridge.latitude).toBeCloseTo((39.9892614 + 39.989717) / 2, 8)
    expect(bridge.longitude).toBeCloseTo((116.2721945 + 116.2707389) / 2, 8)
  })
  it.each([
    ['仁寿殿', 39.997750, 116.280059],
    ['佛香阁', 39.999089, 116.273946],
    ['德和园', 39.998627, 116.279751],
    ['文昌阁', 39.996559, 116.280024],
  ] as const)('%s 对齐高德公开 POI 而非区域平均坐标', (name, latitude, longitude) => {
    const spot = locations.spots[name]
    const [lat,lng] = wgs84ToGcj02(spot.latitude,spot.longitude)
    expect(lat).toBeCloseTo(latitude, 8)
    expect(lng).toBeCloseTo(longitude, 8)
    expect(spot.source_url).toContain('amap.com/place/')
  })
})
