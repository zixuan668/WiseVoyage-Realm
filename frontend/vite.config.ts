import { fileURLToPath, URL } from 'node:url'
import os from 'node:os'

import { defineConfig, loadEnv, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'

// 自动获取本机真实局域网IP（跳过所有虚拟网卡）
function getLocalIP(): string {
  const ifaces = os.networkInterfaces()
const virtualNames = ['VMware', 'VirtualBox', 'WSL', 'vEthernet', 'Docker', 'Loopback', '蓝牙', 'Bluetooth', 'tun', 'TAP', 'TUN']

  // 收集所有真实网卡IP
  const realIPs: string[] = []
  for (const [name, addrs] of Object.entries(ifaces)) {
    if (virtualNames.some(v => name.includes(v))) continue
    for (const addr of addrs || []) {
      if (addr.family === 'IPv4' && !addr.internal) {
        realIPs.push(addr.address)
      }
    }
  }

  // 优先级排序：热点常用段 > 家庭路由段 > 企业网段 > 其他
  const priority = (ip: string): number => {
    if (ip.startsWith('172.20.')) return 1  // iOS/Android 热点
    if (ip.startsWith('192.168.')) return 2 // 家庭路由器
    if (ip.startsWith('10.')) return 3      // 企业网/校园网/部分Android热点
    if (ip.startsWith('172.') && parseInt(ip.split('.')[1]) >= 16) return 4 // 172.16-31 私有段
    return 5
  }

  realIPs.sort((a, b) => priority(a) - priority(b))
  return realIPs[0] || 'localhost'
}

// Vite插件：把局域网IP注入到前端
// 注意：IP 只在服务启动时检测会过期（切 Wi-Fi/热点后二维码仍指向旧地址）。
// 因此额外提供 /__lan-info，在每次生成二维码时取当前真实 IP 和实际监听端口。
function serverInfoPlugin(): Plugin {
  const virtualModuleId = 'virtual:server-info'
  const resolvedVirtualModuleId = '\0' + virtualModuleId
  console.log(`\n🔗 检测到局域网IP: ${getLocalIP()}  → 前端二维码将使用此地址\n`)
  return {
    name: 'server-info-plugin',
    resolveId(id) {
      if (id === virtualModuleId) return resolvedVirtualModuleId
    },
    load(id) {
      if (id === resolvedVirtualModuleId) {
        return `export const serverIP = ${JSON.stringify(getLocalIP())}; export const serverPort = 5173;`
      }
    },
    configureServer(server) {
      server.middlewares.use('/__lan-info', (_req, res) => {
        const address = server.httpServer?.address()
        const port = address && typeof address === 'object' ? address.port : 5173
        res.setHeader('Content-Type', 'application/json')
        res.setHeader('Cache-Control', 'no-store')
        res.end(JSON.stringify({ ip: getLocalIP(), port }))
      })
    },
  }
}

// Browser navigation must reach the SPA even when its path shares an API prefix.
function spaNavigationBypass(req: { headers: { accept?: string }; url?: string }) {
  if (req.headers.accept?.includes('text/html')) return req.url
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BASE_SERVER_URL || 'http://127.0.0.1:18000'

  return {
  server: {
    host: '0.0.0.0',  // 监听所有网络接口
    port: 5173,
    // 隧道访问时禁用HMR WebSocket（localtunnel不支持WebSocket）
    hmr: {
      // 当通过隧道访问时，HMR WebSocket连接会失败导致页面卡住
      // overlay: false 防止错误遮罩挡住整个页面
      overlay: false,
    },
    // 允许来自任何host的请求（隧道会用随机域名）
    allowedHosts: true,
    proxy: {
      '/user': { target: backendUrl, bypass: spaNavigationBypass },
      '/upload': { target: backendUrl, bypass: spaNavigationBypass },
      '/llm': { target: backendUrl, bypass: spaNavigationBypass },
      '/dashboard': { target: backendUrl, bypass: spaNavigationBypass },
      '/digital-guide': { target: backendUrl, bypass: spaNavigationBypass },
      // 景区导览新增路由代理
      '/scenic-spots': { target: backendUrl, bypass: spaNavigationBypass },
      '/knowledge-base': { target: backendUrl, bypass: spaNavigationBypass },
      '/tour-routes': { target: backendUrl, bypass: spaNavigationBypass },
      '/tour-session': { target: backendUrl, bypass: spaNavigationBypass },
      '/tour-experience': { target: backendUrl, bypass: spaNavigationBypass },
      '/service-stations': { target: backendUrl, bypass: spaNavigationBypass },
      '/analytics': { target: backendUrl, bypass: spaNavigationBypass },
      '/system': { target: backendUrl, bypass: spaNavigationBypass },
      '/files': { target: backendUrl, bypass: spaNavigationBypass },
      '/api': { target: backendUrl, bypass: spaNavigationBypass },
      '/xingyun': { target: backendUrl, bypass: spaNavigationBypass },
      '/avatar': { target: backendUrl, bypass: spaNavigationBypass }
    }
  },
  plugins: [vue(), serverInfoPlugin()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
  }
})
