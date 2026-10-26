import { serverIP, serverPort } from 'virtual:server-info'

function publicServerOrigin(value?: string): string | undefined {
  const configured = value?.trim()
  // Validate the original input before URL normalizes path segments or userinfo.
  if (!configured || !/^https?:\/\/[^\/?#\\@\s]+\/?$/i.test(configured)) return
  try {
    const url = new URL(configured)
    if (url.username || url.password || url.pathname !== '/' || url.search || url.hash) return
    return url.origin
  } catch {
    return
  }
}

/**
 * 返回手机可访问的网页来源地址。
 * 构建时配置的公开来源优先，避免生产容器网卡地址进入领取二维码。
 * 用 localhost/127.0.0.1 打开页面时，二维码不能写本机回环地址；
 * 每次生成时通过 /__lan-info 读取当前局域网 IP 与实际端口，避免切换网络后仍用旧地址。
 */
export async function lanOrigin(): Promise<string> {
  const configured = publicServerOrigin(import.meta.env.VITE_PUBLIC_SERVER_ORIGIN)
  if (configured) return configured
  const host = window.location.hostname
  if (!/^(localhost|127\.0\.0\.1)$/.test(host)) return window.location.origin
  try {
    const response = await fetch('/__lan-info', { cache: 'no-store' })
    const data = await res_json(response)
    if (data?.ip) return `http://${data.ip}:${Number(data.port) || serverPort}`
  } catch {
    // 开发服务器未提供该接口时退回构建时注入的地址。
  }
  return `http://${serverIP}:${serverPort}`
}

async function res_json(response: Response): Promise<any> {
  try {
    return await response.json()
  } catch {
    return null
  }
}
