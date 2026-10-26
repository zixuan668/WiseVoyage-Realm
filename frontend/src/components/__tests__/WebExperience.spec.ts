import { describe, it, expect, vi, afterEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import RouteOverview from '../RouteOverview.vue'
import TourVisualContext from '../TourVisualContext.vue'
const api = vi.hoisted(() => ({ route: vi.fn() }))
vi.mock('@/api/tourExperience', () => ({
  getRouteOverview: api.route
}))
const overview = (name = '长廊') => ({
  stops: [
    { spot_id: 1, spot_name: name, order: 1, latitude: 39.99, longitude: 116.26, visit_minutes: 20 }
  ],
  legs: [],
  pace: 'standard',
  complete: true,
  walking_meters: 0,
  walking_minutes: 0,
  visit_minutes: 20,
  rest_minutes: 2,
  total_minutes: 22,
  distance_version: '2026-10-10',
  note: ''
})
const ok = (data: any) => ({ data: { success: true, data } })
let wrapper: VueWrapper
afterEach(() => {
  wrapper?.unmount()
  vi.clearAllMocks()
})
describe('网页讲解与路线呈现', () => {
  it('切换路线后迟到的旧请求不能覆盖新路线', async () => {
    let old!: (value: any) => void
    api.route
      .mockReturnValueOnce(new Promise((r) => (old = r)))
      .mockResolvedValueOnce(ok(overview('昆明湖')))
    wrapper = mount(RouteOverview, { props: { spotIds: [1], showMap: false } })
    await wrapper.setProps({ spotIds: [2] })
    await flushPromises()
    old(ok(overview('过时景点')))
    await flushPromises()
    expect(wrapper.text()).toContain('昆明湖')
    expect(wrapper.text()).not.toContain('过时景点')
    expect(api.route.mock.calls[0][2].aborted).toBe(true)
  })
  it('路线加载失败可重试，不显示伪造的零距离', async () => {
    api.route.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(ok(overview()))
    wrapper = mount(RouteOverview, { props: { spotIds: [1], showMap: false } })
    await flushPromises()
    expect(wrapper.find('[role=alert]').exists()).toBe(true)
    expect(wrapper.find('.route-statistics').exists()).toBe(false)
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role=alert]').exists()).toBe(false)
    expect(wrapper.text()).toContain('长廊')
  })
  it('参考图片拒绝外部任意地址，时间线文本转义', () => {
    wrapper = mount(TourVisualContext, {
      props: {
        expanded: true,
        context: {
          spot_name: '长廊',
          images: [{ url: 'javascript:alert(1)', source: '', label: 'bad' }],
          timeline: [{ year: 1750, text: '<img src=x onerror=alert(1)>' }],
          note: ''
        }
      },
      global: { stubs: { ElImage: true } }
    })
    expect(wrapper.find('.visual-images').exists()).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('<img')
  })
  it('图片失败保留来源，允许游客查看原始资料', async () => {
    const image = defineComponent({
      emits: ['error'],
      setup: (_, ctx) => () => h('button', { onClick: () => ctx.emit('error') }, 'fail image')
    })
    wrapper = mount(TourVisualContext, {
      props: {
        context: {
          spot_name: '长廊',
          images: [
            {
              url: 'https://www.summerpalace.net.cn/Uploads/a.jpg',
              source: 'https://www.summerpalace.net.cn/gallery.html',
              label: '长廊'
            }
          ],
          timeline: [],
          note: ''
        }
      },
      global: { stubs: { ElImage: image } }
    })
    await wrapper.find('button').trigger('click')
    expect(wrapper.text()).toContain('图片暂时无法加载')
    expect(wrapper.find('a').attributes('href')).toContain('gallery.html')
  })
})
