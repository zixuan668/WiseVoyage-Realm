import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import StationAdminView from '../StationAdminView.vue'
import { listStationAdmin, saveStationAdmin, type StationAdmin, type StationAdminData } from '@/api/serviceStation'

vi.mock('@/api/serviceStation', () => ({
  listStationAdmin: vi.fn(), saveStationAdmin: vi.fn(), stationError: () => '保存失败'
}))
const initial: StationAdmin = {
  station_id: 'test-east', name: '东门服务站', name_en: 'East gate station',
  location: '东宫门', location_en: 'East gate', anchor_key: 'gate:east', guide_id: 2,
  default_language: 'zh', welcome: '欢迎参观', welcome_en: 'Welcome.',
  idle_seconds: 120, volume: .7, enabled: true, demo: true, revision: 2,
  announcements: [{ text: '正常开放', text_en: 'Open as usual', expires_at: '' }],
  facilities: [{ key: 'water-east', name: '饮水点', name_en: 'Water', kind: 'water',
    anchor_key: 'gate:east', verified: true, status: 'open', source: '现场核实' }],
  last_seen: null, updated_at: ''
}
let state: StationAdminData
let wrapper: VueWrapper
const dialog = defineComponent({ props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' })
const field = (text: string) => wrapper.findAll('label').find(label => label.text().startsWith(text))!
const tab = async (key: string) => wrapper.get('#station-tab-' + key).trigger('click')
const submit = async () => { await wrapper.get('form.station-form').trigger('submit'); await flushPromises() }

beforeEach(async () => {
  vi.clearAllMocks()
  state = { stations: [structuredClone(initial)], anchors: [{ key: 'gate:east', label: '东宫门', latitude: 40, longitude: 116 }],
    guides: [{ guide_id: 2, name: '文轩', poster_image: '', render_mode: 'xingyun' }] }
  vi.mocked(listStationAdmin).mockImplementation(async () => structuredClone(state))
  vi.mocked(saveStationAdmin).mockImplementation(async (id, value) => {
    const saved = { ...JSON.parse(JSON.stringify(value)), station_id: id, revision: value.revision + 1 }
    state.stations = [...state.stations.filter(row => row.station_id !== id), saved]
    return saved
  })
  wrapper = mount(StationAdminView, { global: { stubs: { ElDialog: dialog } } })
  await flushPromises()
})
afterEach(() => wrapper.unmount())

describe('服务站管理配置', () => {
  it('切换分类保留草稿，保存时保留未修改的公告、设施和英文配置', async () => {
    await field('服务站名称').get('input').setValue('东门新名称')
    await tab('more')
    expect(field('英文名称').get('input').element.value).toBe(initial.name_en)
    await field('音量').get('input').setValue('0.5')
    await tab('basic')
    expect(field('服务站名称').get('input').element.value).toBe('东门新名称')
    await submit()
    expect(saveStationAdmin).toHaveBeenCalledOnce()
    expect(vi.mocked(saveStationAdmin).mock.calls[0][1]).toMatchObject({
      name: '东门新名称', volume: .5, name_en: initial.name_en, welcome_en: initial.welcome_en,
      guide_id: initial.guide_id, announcements: initial.announcements, facilities: initial.facilities
    })
    expect(wrapper.find('[role=status]').text()).toContain('已保存')
  })

  it('未填完的公告在切回基本信息后仍阻止保存并定位到公告页', async () => {
    await tab('notices')
    await wrapper.findAll('button').find(button => button.text().includes('添加公告'))!.trigger('click')
    await tab('basic')
    await submit()
    expect(saveStationAdmin).not.toHaveBeenCalled()
    expect(wrapper.get('#station-tab-notices').attributes('aria-selected')).toBe('true')
    expect(wrapper.get('[role=alert]').text()).toContain('请补全公告')
    expect(wrapper.findAll('.admin-entry')).toHaveLength(2)
  })

  it('新增服务站通过独立弹窗配置，保留服务站默认配置和发布流程', async () => {
    await wrapper.findAll('button').find(button => button.text().includes('新增服务站'))!.trigger('click')
    await wrapper.get('.station-create-form input').setValue('north-gate')
    await wrapper.get('.station-create-form').trigger('submit')
    await field('服务站名称').get('input').setValue('北门服务站')
    await field('设备位置').get('input').setValue('北宫门')
    await submit()
    expect(saveStationAdmin).toHaveBeenCalledWith('north-gate', expect.objectContaining({
      name: '北门服务站', location: '北宫门', default_language: 'zh', idle_seconds: 120,
      enabled: true, demo: true, revision: 0, announcements: [], facilities: []
    }))
    expect(wrapper.get('[role=status]').text()).toContain('已保存')
  })

  it('从示范点位切换为正式点位时保留位置核实校验', async () => {
    await field('示范点位').get('input').setValue(false)
    await submit()
    expect(saveStationAdmin).not.toHaveBeenCalled()
    expect(wrapper.get('[role=alert]').text()).toContain('核实设备位置')
    await field('已核实设备位置').get('input').setValue(true)
    await submit()
    expect(saveStationAdmin).toHaveBeenCalledWith(initial.station_id, expect.objectContaining({
      demo: false, location_checked: true
    }))
  })
})
