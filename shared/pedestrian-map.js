// Pedestrian routes are computed from OSM WGS84 geometry. Use the same
// map source and coordinate frame for every route, access point and gate.
// Scenic POI browsing on AMap retains its separate GCJ02 conversion.
export const WALK_TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
export const WALK_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
export function walkingMapPoint(latitude, longitude) {
  return [latitude, longitude]
}
