import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import QRCode from 'qrcode'
import StationVisitorInfo from '../StationVisitorInfo.vue'
import { setLocale } from '@/i18n'
import { summerPalaceSeasonAt, summerPalaceVisitorInfo } from '@/data/parkVisitorInfo'

vi.mock('qrcode', () => ({
  default: { toDataURL: vi.fn().mockResolvedValue('data:image/png;base64,dGVzdA==') }
}))
let wrapper: VueWrapper
function render(now = Date.parse('2026-10-18T12:00:00+08:00')) {
  wrapper = mount(StationVisitorInfo, {
    props: { now, announcements: [] },
    global: { stubs: { ElDialog: { props: ['modelValue', 'title'], template: '<section v-if="modelValue" role="dialog"><h2>{{ title }}</h2><slot /><slot name="footer" /></section>' } } }
  })
  return wrapper
}
const button = (text: string) => wrapper.findAll('button').find((b) => b.text() === text)!
beforeEach(() => {
  setLocale('zh')
  vi.clearAllMocks()
})
afterEach(() => wrapper?.unmount())

describe('游园须知', () => {
  it.each([
    ['2026-03-31T15:59:59Z', 'quiet'],
    ['2026-03-31T16:00:00Z', 'peak'],
    ['2026-10-31T15:59:59Z', 'peak'],
    ['2026-10-31T16:00:00Z', 'quiet']
  ])('按北京时间选择季节：%s', (date, season) => {
    expect(summerPalaceSeasonAt(Date.parse(date))).toBe(season)
  })
  it('在季节边界更新参考时间，并区分闭园和停止入园', async () => {
    render(Date.parse('2026-10-31T15:59:59Z'))
    expect(wrapper.text()).toContain('06:00 — 20:00')
    expect(wrapper.text()).toContain('停止入园 19:00')
    await wrapper.setProps({ now: Date.parse('2026-10-31T16:00:00Z') })
    expect(wrapper.text()).toContain('06:30 — 19:00')
    expect(wrapper.text()).toContain('停止入园 18:00')
    expect(wrapper.text()).not.toContain('今日正常开放')
  })
  it('以游览准备和求助替换票务，并提供设施入口', async () => {
    render()
    expect(wrapper.text()).not.toContain('票务')
    await button('游览准备与求助').trigger('click')
    expect(wrapper.text()).toContain('身体不适或遇到困难')
    expect(wrapper.text()).toContain('记住出口与集合点')
    expect(wrapper.text()).not.toContain('¥')
    await button('查找设施与出口').trigger('click')
    expect(wrapper.emitted('facilities')).toHaveLength(1)
    await button('游园提醒').trigger('click')
    expect(wrapper.text()).not.toContain('购票')
  })
  it('展示后台公告，未发布公告时不宣称景区没有临时调整', async () => {
    render()
    await button('景区公告').trigger('click')
    expect(wrapper.text()).toContain('本站暂无已发布公告')
    await wrapper.setProps({
      announcements: [{ text: '西侧步道维护', text_en: 'West path maintenance', expires_at: '' }]
    })
    expect(wrapper.text()).toContain('西侧步道维护')
    setLocale('en')
    await flushPromises()
    expect(wrapper.text()).toContain('West path maintenance')
    expect(wrapper.text()).toContain('Park notices')
  })
  it('在本地生成官网二维码，中英文切换时保持官方目标地址', async () => {
    render()
    await button('手机查看官方信息').trigger('click')
    await flushPromises()
    expect(QRCode.toDataURL).toHaveBeenCalledWith(
      summerPalaceVisitorInfo.source,
      expect.any(Object)
    )
    expect(wrapper.find('img').attributes('src')).toContain('data:image/png')
    expect(wrapper.find('[role="dialog"] .visitor-info-official img').exists()).toBe(true)
    expect(wrapper.get('a').attributes('href')).toBe('https://summerpalace.net.cn/visit.html')
    setLocale('en')
    await flushPromises()
    expect(wrapper.text()).toContain('Visitor essentials')
    expect(wrapper.text()).toContain('Scan for official information')
    await button('Close').trigger('click')
    expect(wrapper.find('.visitor-info-official').exists()).toBe(false)
  })
})
