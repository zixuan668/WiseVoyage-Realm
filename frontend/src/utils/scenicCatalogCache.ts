type PublicScenicPlace = { id: number; name: string; park?: string }
const KEY = 'summer-palace-public-catalog-v1'
const MAX_AGE = 60_000

// Only the public backend catalog is cached. Personal stops/settings stay on the server.
export function readScenicCatalog<T extends PublicScenicPlace>(): T[] {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || 'null')
    const age = Date.now() - saved?.savedAt
    if (!Number.isFinite(age) || age < 0 || age > MAX_AGE || !Array.isArray(saved?.places)) return []
    return saved.places.filter((place: PublicScenicPlace) => place && Number.isInteger(place.id) && typeof place.name === 'string' && place.park === 'summer-palace')
  } catch { return [] }
}

export function writeScenicCatalog<T extends PublicScenicPlace>(places: T[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({savedAt: Date.now(), places: places.filter(place => place.park === 'summer-palace')}))
  } catch { /* Storage restrictions must never delay the page. */ }
}
