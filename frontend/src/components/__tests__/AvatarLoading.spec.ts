import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import XingyunGuide from '../XingyunGuide.vue'
import DigitalAvatarPlayer from '../DigitalAvatarPlayer.vue'

const http = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('@/api/base', () => ({ request_handler: http }))
vi.mock('@/api/xingyunTour', () => ({ avatarHeaders: () => ({}) }))
let wrapper: VueWrapper | undefined
let callbacks: Record<string, any>
let download: Record<string, any>
let initResolvers: Array<() => void> = []
const setVolume = vi.fn()

// 新版 litesdk 用 init() 的 Promise 表示就绪；测试用可控 Promise 模拟。
async function resolveInit(index = -1) {
  initResolvers.at(index)?.()
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  http.get.mockResolvedValue({ data: { configured: true, provider: 'xingyun' } })
  callbacks = {}
  download = {}
  initResolvers = []
  vi.stubGlobal('XmovAvatar', class {
    constructor(options: Record<string, any>) { callbacks = options }
    init(options: Record<string, any>) {
      download = options
      return new Promise<void>(resolve => { initResolvers.push(resolve) })
    }
    destroy() {}
    interactiveidle() {}
    speak() {}
    setVolume = setVolume
  })
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.unstubAllGlobals();vi.useRealTimers() })

describe('数字人加载呈现', () => {
  it('将音量传到实时播放器，在初始化、拖动和重新连接后保持游客的选择', async () => {
    http.get.mockImplementation((url: string) => Promise.resolve(url.startsWith('/avatar/')
      ? { data: { data: { preferredMode: 'xingyun', realistic: { ready: false } } } }
      : { data: { configured: true, provider: 'xingyun' } }))
    wrapper = mount(DigitalAvatarPlayer, { props: { guideId: 37, tourId: 90, volume: 0.7 } })
    await flushPromises()
    await wrapper.setProps({ volume: 0.25 })
    await resolveInit()
    expect(setVolume).toHaveBeenLastCalledWith(0.25)
    await wrapper.setProps({ volume: 0 })
    expect(setVolume).toHaveBeenLastCalledWith(0)
    setVolume.mockClear()
    document.dispatchEvent(new Event('visibilitychange'))
    await flushPromises()
    expect(setVolume).toHaveBeenLastCalledWith(0)
    await wrapper.setProps({ tourId: 91 })
    await flushPromises()
    await resolveInit()
    expect(setVolume).toHaveBeenLastCalledWith(0)
    await wrapper.setProps({ volume: 1 })
    expect(setVolume).toHaveBeenLastCalledWith(1)
    wrapper.unmount()
    wrapper = undefined
    setVolume.mockClear()
    document.dispatchEvent(new Event('visibilitychange'))
    await flushPromises()
    expect(setVolume).not.toHaveBeenCalled()
  })

  it('生成的讲解视频使用同一音量，并在播放中响应调整', async () => {
    http.get.mockImplementation((url: string) => Promise.resolve(url.startsWith('/avatar/jobs/')
      ? { data: { data: { status: 'completed', video_url: '/speech.mp4' } } }
      : { data: { data: { preferredMode: 'realistic', realistic: { ready: true } } } }))
    wrapper = mount(DigitalAvatarPlayer, { props: { guideId: 37, volume: 0.4 } })
    await flushPromises()
    ;(wrapper.vm as any).acceptJob({ job_id: 'speech-1' })
    await flushPromises()
    expect(wrapper.get<HTMLVideoElement>('video').element.volume).toBe(0.4)
    await wrapper.setProps({ volume: 0 })
    expect(wrapper.get<HTMLVideoElement>('video').element.volume).toBe(0)
  })

  it('服务站凭证到位后直接加载实体，始终不展示静态封面', async () => {
    http.get.mockImplementation((url: string) => Promise.resolve(url.startsWith('/avatar/')
      ? { data: { data: { preferredMode: 'xingyun', realistic: { ready: false }, cartoon: { ready: false } } } }
      : { data: { configured: true, provider: 'xingyun' } }))
    wrapper = mount(DigitalAvatarPlayer, { props: { guideId: 37, stationMode: true, posterImage: '/poster.png', width: 640 } })
    await flushPromises()
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.avatar-loading').text()).toBe('数字人正在加载中')
    expect(wrapper.find('.xingyun-guide').exists()).toBe(false)
    await wrapper.setProps({ stationVisit: { visit_id: 'station1', access_token: 'private-token' } })
    await flushPromises()
    expect(callbacks.headers).toEqual({ 'X-Station-Token': 'private-token' })
    expect(callbacks.gatewayServer).toContain('station_visit_id=station1')
    await resolveInit()
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.xingyun-canvas').attributes('style')).toContain('visibility: visible')
    expect(wrapper.find('.xingyun-controls').exists()).toBe(false)
  })
  it('断线后有限重连，旧实例迟到的就绪事件无效',async()=>{
    vi.useFakeTimers({toFake:['setTimeout','clearTimeout']})
    wrapper=mount(XingyunGuide,{props:{guideId:37,tourId:90}});await flushPromises()
    const oldResolve=initResolvers.at(-1)!
    download.onClose();await flushPromises()
    expect(wrapper.text()).toContain('自动重连')
    oldResolve();await flushPromises()
    expect(wrapper.find('.xingyun-canvas').attributes('style')).toContain('hidden')
    await vi.advanceTimersByTimeAsync(2000);await flushPromises()
    callbacks.onMessage({code:5000,message:'offline'});await flushPromises()
    await vi.advanceTimersByTimeAsync(6000);await flushPromises()
    callbacks.onMessage({code:5000,message:'offline'});await flushPromises()
    expect(wrapper.text()).not.toContain('自动重连')
    expect(wrapper.find('button').text()).toBe('连接数字人')
  })
  it('主动断开后不自动重新连接',async()=>{
    vi.useFakeTimers({toFake:['setTimeout','clearTimeout']})
    wrapper=mount(XingyunGuide,{props:{guideId:37,tourId:90}});await flushPromises()
    await resolveInit()
    await wrapper.find('button').trigger('click')
    window.dispatchEvent(new Event('online'))
    await vi.advanceTimersByTimeAsync(10000);await flushPromises()
    expect(wrapper.find('.xingyun-canvas').attributes('style')).toContain('hidden')
    expect(wrapper.text()).not.toContain('自动重连')
  })
  it('下载时只显示文字，隐藏头像和画布，准备好后展示画布', async () => {
    wrapper = mount(XingyunGuide, { props: { guideId: 37, tourId: 90, posterImage: '/head.png' } })
    await flushPromises()
    download.onDownloadProgress(42)
    await nextTick()
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('[role="status"]').text()).toBe('数字人正在加载中')
    expect(wrapper.find('.xingyun-canvas').attributes('style')).toContain('visibility: hidden')
    expect(wrapper.findAll('button')).toHaveLength(0)
    await resolveInit()
    expect(wrapper.find('[role="status"]').exists()).toBe(false)
    expect(wrapper.find('.xingyun-canvas').attributes('style')).toContain('visibility: visible')
    expect(wrapper.find('button').text()).toBe('断开连接')
    expect(wrapper.emitted('connected')?.at(-1)).toEqual([true])
  })

  it('连接失败显示重试入口，不用头像替代', async () => {
    wrapper = mount(XingyunGuide, { props: { guideId: 37, tourId: 90, posterImage: '/head.png' } })
    await flushPromises()
    await resolveInit()
    callbacks.onMessage({ code: 5000, message: '连接失败' })
    await flushPromises()
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('[role="status"]').text()).toContain('请重试')
    expect(wrapper.find('.xingyun-canvas').attributes('style')).toContain('visibility: hidden')
    expect(wrapper.find('button').text()).toBe('连接数字人')
  })

  it('查询数字人类型之前也不提前闪现头像', async () => {
    let resolve!: (value: unknown) => void
    http.get.mockImplementation((url: string) => url.startsWith('/avatar/')
      ? new Promise(r => { resolve = r })
      : Promise.resolve({ data: { configured: true, provider: 'xingyun' } }))
    wrapper = mount(DigitalAvatarPlayer, { props: { guideId: 37, tourId: 90, posterImage: '/head.png' } })
    await flushPromises()
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.avatar-loading').text()).toBe('数字人正在加载中')
    resolve({ data: { data: { preferredMode: 'xingyun', realistic: { ready: false } } } })
    await flushPromises()
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.avatar-loading').exists()).toBe(false)
    expect(wrapper.find('.xingyun-guide').isVisible()).toBe(true)
  })
})
