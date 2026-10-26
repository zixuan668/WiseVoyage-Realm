import { header_authorization } from './user'

export function saveAvatarToken(tourId: number, token?: string) {
  if (token) sessionStorage.setItem('xingyun-tour-' + tourId, token)
}

export function avatarHeaders(tourId: number): Record<string, string> {
  const token = sessionStorage.getItem('xingyun-tour-' + tourId)
  if (token) return { 'X-Tour-Access': token }
  const authorization = header_authorization.value
  return authorization && !/undefined|null/.test(authorization) ? { Authorization: authorization } : {}
}

export function receiveAvatarToken(tourId: number) {
  const fragment = new URLSearchParams(location.hash.slice(1))
  const token = fragment.get('avatarToken')
  if (token) {
    saveAvatarToken(tourId, token)
    // App 或领取页传来的短期导览凭证只在 fragment 中传递，不发送给网页服务器。
    history.replaceState(history.state, '', location.pathname + location.search)
  }
}
