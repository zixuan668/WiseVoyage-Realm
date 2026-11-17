/**
 * Rewrite backend file URLs to same-origin paths.
 *
 * The backend stores and returns absolute image URLs (for example
 * http://192.168.1.20:18000/api/v1/files/...). Those hosts become stale when
 * the service moves or is reached from another device, so the browser falls
 * back to placeholder art even though the real file is available. Both the
 * Vite dev proxy and the production reverse proxy expose the same file route
 * on the page origin, so local/LAN file URLs can be requested relative.
 *
 * Genuine external image hosts are returned unchanged.
 */
const LOCAL_HOST = /^(?:localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|\[::1\]|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)$/
const FILE_PATH = /^\/(?:api\/v1\/)?files\//

export function backendAssetUrl(value: string | null | undefined): string {
  if (!value) return ''
  if (!/^(?:https?:)?\/\//i.test(value)) return value
  try {
    const url = new URL(value, window.location.origin)
    const host = url.hostname.toLowerCase()
    if (LOCAL_HOST.test(host) && FILE_PATH.test(url.pathname)) {
      return url.pathname + url.search + url.hash
    }
  } catch {
    // Keep non-URL values and genuine external image hosts unchanged.
  }
  return value
}
