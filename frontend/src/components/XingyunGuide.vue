<script setup lang="ts">import { t } from '@/i18n'

import { computed, ref, watch, onBeforeUnmount, nextTick } from 'vue'
import { request_handler } from '@/api/base'
import { avatarHeaders } from '@/api/xingyunTour'
const props = withDefaults(defineProps<{ guideId?: number; tourId?: number; stationVisit?:{visit_id:string;access_token:string}; stationMode?: boolean; framing?: 'full' | 'half'; posterImage?: string; volume?: number }>(), { volume: 1 })

type Avatar = {
  init(options: Record<string, unknown>): Promise<void>
  speak(text: string, start: boolean, end: boolean): void
  interactiveidle(): void
  setVolume(volume: number): void
  destroy(): void
}
type Constructor = new (options: Record<string, unknown>) => Avatar
const emit = defineEmits<{ playing: [value: boolean]; connected: [value: boolean] }>()
const containerId = 'xingyun-' + Math.random().toString(36).slice(2)
const configured = ref(false)
const provider = ref('')
const loading = ref(false)
const ready = ref(false)
const message = ref('数字人正在加载中')
const querying = ref(true)
const retryCount=ref(0),retryPending=ref(false),configRevision=ref(0)
let retryTimer:ReturnType<typeof setTimeout>|undefined
let cancelReady:(()=>void)|undefined
let wanted=true
const statusText = computed(() => message.value.startsWith('数字人服务异常') ? t("暂时无法连接，请重试") : message.value.replace(/SDK/g, '数字人资源').replace(/^Error:\s*/, ''))
// 星云 litesdk 初始化前会做能力检查，安全上下文（isSecureContext）是 fatal 项：
// 用局域网 http://IP 打开时 SDK 会直接拒绝，只提示“暂时无法连接”会让游客误判为网络故障。
const insecureContext = typeof window !== 'undefined' && window.isSecureContext === false
const insecureMessage = () => t('数字人需要 HTTPS 或 localhost 才能连接') + (typeof location !== 'undefined' ? '（' + location.origin + '）' : '')
let avatar: Avatar | undefined
let active = true
let generation = 0
let configPromise: Promise<void> = Promise.resolve()
function applyVolume() {
  if (active && ready.value && avatar) avatar.setVolume(props.volume)
}
watch(() => props.volume, applyVolume)
function restoreVolume() {
  // SDK restores full volume when the tab becomes visible; apply the visitor's
  // choice after its visibility handler, including an explicit mute (0).
  if (!document.hidden) queueMicrotask(applyVolume)
}
document.addEventListener('visibilitychange', restoreVolume)
watch(() => [props.guideId, props.tourId, props.stationVisit?.visit_id,configRevision.value], () => {
  wanted=true;retryCount.value=0
  release(); configured.value = false; provider.value = ''
  querying.value = true
  message.value = '数字人正在加载中'
  const current = generation
  configPromise = (async () => {
    if (!props.guideId) return
    try {
      const { data } = await request_handler.get('/xingyun/config/' + props.guideId,{timeout:12000})
      if (!active || current !== generation) return
      configured.value = data.configured
      provider.value = data.provider
      message.value = data.configured ? t("尚未连接实时数字人，请点击连接") : t("该数字人未上架或未完成应用绑定")
      if (configured.value && (props.tourId || props.stationVisit)) {
        if (insecureContext) message.value = insecureMessage()
        else void nextTick().then(() => {
          if (active && current === generation) void connect()
        })
      }
    } catch { if (active && current === generation) { provider.value = 'xingyun'; message.value = '数字人配置查询失败，请检查后端服务' } }
    finally { if (active && current === generation) querying.value = false }
  })()
}, { immediate: true })

async function loadSdk() {
  const win = window as Window & { XmovAvatar?: Constructor }
  if (win.XmovAvatar) return win.XmovAvatar
  await new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://media.xingyun3d.com/xingyun3d/general/litesdk/xmovAvatar@latest.js'
    const timer = setTimeout(() => { script.remove(); reject(new Error(t("SDK 下载超时"))) }, 30000)
    script.onload = () => { clearTimeout(timer); resolve() }
    script.onerror = () => { clearTimeout(timer); script.remove(); reject(new Error(t("SDK 下载失败"))) }
    document.head.appendChild(script)
  })
  if (!win.XmovAvatar) throw new Error(t("SDK 未正确加载"))
  return win.XmovAvatar
}
function release() {
  generation++
  if(retryTimer)clearTimeout(retryTimer)
  retryTimer=undefined;retryPending.value=false
  cancelReady?.();cancelReady=undefined
  loading.value=false
  ready.value = false
  emit('connected', false)
  emit('playing', false)
  try { avatar?.destroy() } catch { /* 已断开的实例 */ }
  avatar = undefined
}
function scheduleRetry(){
 if(!active||!wanted||retryCount.value>=2||navigator.onLine===false)return
 const current=generation;retryPending.value=true;retryCount.value++
 retryTimer=setTimeout(()=>{retryTimer=undefined;retryPending.value=false;if(active&&wanted&&current===generation)void connect()},retryCount.value===1?2000:6000)
}
function retry(){wanted=true;retryCount.value=0;if(!configured.value){configRevision.value++;return}void connect()}
function online(){if(wanted&&!ready.value&&!loading.value)retry()}
window.addEventListener('online',online)
async function connect() {
  await configPromise
  if (!active || !wanted || !configured.value || loading.value) return
  if (insecureContext) { message.value = insecureMessage(); return }
  release()
  const current = generation
  loading.value = true
  message.value = '正在加载数字人'
  try {
    const SDK = await loadSdk()
    if (!active || current !== generation) return
    await nextTick()
    let rejectReady!: (error: Error) => void
    const stopSignal = new Promise<never>((_, reject) => { rejectReady = reject })
    // stopSignal 可能比竞态先结束，先挂空 catch 避免未处理的 Promise 拒绝。
    void stopSignal.catch(() => {})
    cancelReady=()=>rejectReady(new Error('Connection cancelled'))
    const failed=(text:string)=>{
      if(current!==generation)return
      rejectReady(new Error(text))
      // init 已完成后 SDK 仍可能报错或断开，此时竞态已结束，需要在这里直接复位。
      if(ready.value){release();message.value=text;scheduleRetry()}
    }
    // SDK 的本地签名会被代理忽略；真实应用凭据保留在后端。
    const instance = new SDK({
      containerId: '#' + containerId,
      appId: 'server-proxy', appSecret: 'server-proxy',
      gatewayServer: new URL('/xingyun/session/' + props.guideId + '?tour_id=' + (props.tourId || 0) + (props.stationVisit?'&station_visit_id='+encodeURIComponent(props.stationVisit.visit_id):''), location.origin).href,
      headers: props.stationVisit ? {'X-Station-Token':props.stationVisit.access_token} : avatarHeaders(props.tourId || 0),
      proxyWidget: {
        subtitle_on: () => {},
        subtitle_off: () => {},
      },
      onMessage: (error: { code?: number; message?: string }) => {
        if (current === generation && error.code && error.code !== 4000) {
          failed(t("数字人服务异常，请重试"))
        }
      },
      onVoiceStateChange: (status: string) => {
        if (current !== generation) return
        if (status.includes('start')) { emit('playing', true); message.value = '数字人正在讲解' }
        if (status.includes('end')) { emit('playing', false); message.value = '数字人讲解结束' }
      },
      onStateChange: (state: string) => {
        if (current !== generation) return
        if (state === 'idle' || state === 'interactive_idle') {
          ready.value = true
          emit('connected', true)
          if (message.value !== '数字人正在讲解') message.value = '数字人已连接'
        }
      },
    })
    avatar = instance
    let initTimer: ReturnType<typeof setTimeout> | undefined
    try {
      // 新版 litesdk 以 init() 返回的 Promise 表示就绪；旧的 onInitEvent(4000) 已被移除，
      // 继续等待旧事件会导致页面一直停在“正在加载数字人”并在 90 秒后超时。
      await Promise.race([
        instance.init({
          onDownloadProgress: (progress: number) => {
            if (current === generation) message.value = t("正在加载数字人资源：") + Math.round(progress) + '%'
          },
          onClose: () => {
            if (current !== generation) return
            failed(t("数字人连接已关闭，可重新连接"))
          },
        }),
        stopSignal,
        new Promise<never>((_, reject) => { initTimer = setTimeout(() => reject(new Error(t("数字人初始化超时，请重新连接"))), 90000) }),
      ])
      if (!active || current !== generation) return
      ready.value = true
      applyVolume()
      emit('connected', true)
      message.value = '数字人已连接'
    } finally { if (initTimer) clearTimeout(initTimer) }
  } catch (error) {
    if (current === generation) { release(); message.value = error instanceof Error ? error.message : t("数字人连接失败");scheduleRetry() }
  } finally { if (active && current===generation) {loading.value = false;cancelReady=undefined} }
}
function stop() {
  try { if (ready.value) avatar?.interactiveidle() } catch { release(); message.value = '数字人连接异常，请重新连接' }
  emit('playing', false)
}
function speak(text?: string): boolean {
  if (!ready.value || !avatar || !text?.trim()) return false
  try {
    avatar.interactiveidle()
    applyVolume()
    avatar.speak(text, true, true)
    return true
  } catch { release(); message.value = '数字人播报失败，本轮使用原导览语音'; return false }
}
onBeforeUnmount(() => { active = false;wanted=false;window.removeEventListener('online',online);document.removeEventListener('visibilitychange',restoreVolume);release() })
defineExpose({ speak, stop, isReady: () => ready.value })
</script>
<template>
  <section v-show="provider === 'xingyun' || querying" class="xingyun-guide" :class="{ activated: ready || loading, connected: ready, half: framing === 'half', 'station-mode':stationMode }">
    <div class="xingyun-frame" :aria-busy="querying || loading">
      <div :id="containerId" class="xingyun-canvas" :style="{ visibility: ready ? 'visible' : 'hidden' }" :aria-hidden="!ready" />
      <p v-if="!ready" class="xingyun-loading" role="status">{{ $t(querying || loading ? '数字人正在加载中' : statusText) }}</p>
    </div>
    <div v-if="!stationMode || !ready" class="xingyun-controls">
      <span v-if="retryPending" role="status">{{ $t('正在准备自动重连') }}</span>
      <button v-if="!ready && !loading && !querying && provider==='xingyun' && !insecureContext" @click="retry">{{ $t("连接数字人") }}</button>
      <button v-if="ready" @click="wanted=false; release(); message='数字人连接已关闭'">{{ $t("断开连接") }}</button>
    </div>
  </section>
</template>
<style scoped>
.xingyun-guide:not(.half) .xingyun-frame{box-sizing:border-box;padding:44px 16px 62px}
.xingyun-guide:not(.half) .xingyun-canvas{position:absolute!important;inset:44px 16px 62px!important;width:calc(100% - 32px)!important;height:calc(100% - 106px)!important;transform:none!important}
/* SDK injects its own pixel size, scale and offsets. Fit the complete source frame
   into the available stage instead of cropping it or inheriting those offsets. */
.xingyun-guide:not(.half) .xingyun-canvas :deep(canvas){position:absolute!important;inset:0!important;width:100%!important;height:100%!important;max-width:100%!important;max-height:100%!important;min-width:0!important;min-height:0!important;margin:0!important;transform:none!important;object-fit:contain!important;object-position:50% 50%!important}
.xingyun-loading{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;margin:0;padding:24px;text-align:center;font-size:18px;line-height:1.6;color:var(--text-secondary)}
.xingyun-guide.station-mode:not(.half) .xingyun-frame{padding:8px 4px 6px}
.xingyun-guide.station-mode:not(.half) .xingyun-canvas{inset:8px 4px 6px!important;width:calc(100% - 8px)!important;height:calc(100% - 14px)!important}
/* Enlarge only the connected terminal figure, keeping the feet near the stage
   floor. Loading and error text keep their normal size. */
.xingyun-guide.station-mode.connected:not(.half) .xingyun-canvas{transform:scale(1.18)!important;transform-origin:50% 90%!important}
.station-mode .xingyun-controls:empty{display:none}
.xingyun-guide{width:100%;height:100%;min-height:0;display:flex;flex-direction:column;justify-content:center;flex:1}.xingyun-guide.activated{flex:1;min-height:180px}.xingyun-frame{flex:1;min-height:120px;width:100%;position:relative;overflow:hidden}.xingyun-canvas{position:absolute;inset:0;width:100%;height:100%}.half .xingyun-canvas{transform:scale(1.75);transform-origin:50% 0}.xingyun-controls{flex-shrink:0;text-align:center;padding:8px;font-size:18px;color: var(--text-secondary)}.xingyun-controls button{font:inherit;font-size:18px;line-height:1.5;min-height:44px;max-width:100%;padding:10px 16px;border: 1px solid var(--glass-line);border-radius:8px;color: var(--champagne-text);background: var(--glass);cursor:pointer}.xingyun-controls p{margin:6px 0}
</style>
