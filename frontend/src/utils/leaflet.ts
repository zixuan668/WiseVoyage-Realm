let pending: Promise<any> | undefined
export function loadScenicMap(): Promise<any> {
  const win = window as any
  if (win.L) return Promise.resolve(win.L)
  if (pending) return pending
  pending = new Promise((resolve, reject) => {
    if (!document.querySelector('link[data-scenic-leaflet]')) {
      const css = document.createElement('link')
      css.rel = 'stylesheet'
      css.href = '/vendor/leaflet/leaflet.css'
      css.dataset.scenicLeaflet = 'true'
      document.head.appendChild(css)
    }
    const script = document.createElement('script')
    script.src = '/vendor/leaflet/leaflet.js'
    const timer = setTimeout(() => {
      script.remove()
      pending = undefined
      reject(new Error('Map load timeout'))
    }, 12000)
    script.onload = () => {
      clearTimeout(timer)
      if (win.L) resolve(win.L)
      else {
        pending = undefined
        reject(new Error('Map unavailable'))
      }
    }
    script.onerror = () => {
      clearTimeout(timer)
      script.remove()
      pending = undefined
      reject(new Error('Map unavailable'))
    }
    document.head.appendChild(script)
  })
  return pending
}
export const SCENIC_TILES =
  'https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}'
