// 本地开发地址由 scripts/configure_app.ps1 更新；正式部署改为 HTTPS。
export const LAN_SERVER_ORIGIN = 'http://172.20.10.3:18000'

// 真机使用局域网地址。HBuilderX 重跑时会清理自定义 USB 转发，
// 不能让开发版固定依赖手机自己的 127.0.0.1:18000。
let usbDevelopment = false
// Local browser previews connect to the same backend as USB development.
// #ifdef H5
usbDevelopment = import.meta.env.MODE === 'development' &&
  typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)
// #endif
// Android USB debugging uses adb reverse; iPhone must reach the PC over the LAN.
let appUsbDevelopment = false
// #ifdef APP-PLUS
appUsbDevelopment = import.meta.env.MODE === 'development' && uni.getSystemInfoSync().platform === 'android'
// #endif
// A stable HTTPS endpoint can be supplied when building; local testing keeps its existing default.
const releaseOrigin = normalizeServiceOrigin(import.meta.env.VITE_APP_SERVER_ORIGIN || '')
export let SERVER_ORIGIN = normalizeServiceOrigin(uni.getStorageSync('station-server-origin')) || releaseOrigin || (usbDevelopment || appUsbDevelopment
  ? 'http://127.0.0.1:18000'
  : LAN_SERVER_ORIGIN)
export let BASE_URL = SERVER_ORIGIN + '/api/v1'

export function isLocalStationOrigin(value) {
  const match = /^http:\/\/(\d{1,3}(?:\.\d{1,3}){3}):18000$/.exec(value)
  if (!match) return false
  const ip = match[1].split('.').map(Number)
  if (ip.some(n => n > 255)) return false
  return ip[0] === 127 || ip[0] === 10 || (ip[0] === 192 && ip[1] === 168) || (ip[0] === 172 && ip[1] >= 16 && ip[1] <= 31)
}
export function setStationServerOrigin(value) {
  if (!isLocalStationOrigin(value)) throw new Error('只允许连接局域网电脑的18000端口')
  setServiceOrigin(value)
}

export function normalizeServiceOrigin(value) {
  const origin=String(value||'').trim().replace(/\/$/,'')
  if(isLocalStationOrigin(origin))return origin
  const match=/^https:\/\/(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?::(\d{1,5}))?$/i.exec(origin)
  if(!match || (match[1] && (Number(match[1])<1 || Number(match[1])>65535)))return ''
  return origin.toLowerCase()
}

export function setServiceOrigin(value) {
  const origin=normalizeServiceOrigin(value)
  if(!origin)throw new Error('请输入有效的 HTTPS 服务地址或局域网服务地址')
  if (origin !== SERVER_ORIGIN) {
    uni.removeStorageSync('token')
    uni.removeStorageSync('login_provider')
  }
  SERVER_ORIGIN = origin
  BASE_URL = origin + '/api/v1'
  uni.setStorageSync('station-server-origin', origin)
}

export function assetUrl(value) {
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) {
    return value.replace(/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/i, SERVER_ORIGIN)
  }
  if (value.indexOf('/static/') === 0) return value
  if (value.indexOf('/api/v1/') === 0) return SERVER_ORIGIN + value
  if (value.indexOf('/files/') === 0) return BASE_URL + value
  return BASE_URL + '/files/' + value.replace(/^\/+/, '')
}



// App 与网页预览均使用真实账号密码登录。
export const LOGIN_PROVIDER = 'password'

export function isBeijingCity(value) {
  return String(value || '').replace(/\s+/g, '') === '北京'
}




