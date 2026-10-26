/** Resolve legacy local file URLs through the same backend proxy as the admin API. */
export function adminAssetUrl(value: string | null | undefined): string {
  if (!value) return ''
  if (!/^(?:https?:)?\/\//i.test(value)) return value
  try {
    const url = new URL(value, window.location.origin)
    const host = url.hostname.toLowerCase()
    const local = /^(?:localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|\[::1\]|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)$/.test(host)
    if (local && /^\/(?:api\/v1\/)?files\//.test(url.pathname)) {
      return url.pathname + url.search + url.hash
    }
  } catch {
    // Keep non-URL values and genuine external image hosts unchanged.
  }
  return value
}
