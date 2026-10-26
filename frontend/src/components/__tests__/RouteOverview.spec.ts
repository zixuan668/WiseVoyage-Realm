import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RouteOverview from '../RouteOverview.vue'
import { loadScenicMap } from '@/utils/leaflet'
import { t, setLocale } from '@/i18n'
vi.mock('@/utils/leaflet', () => ({ loadScenicMap: vi.fn(), SCENIC_TILES: '/tiles/{z}/{x}/{y}' }))
let wrapper: ReturnType<typeof mount>
afterEach(() => { wrapper?.unmount(); setLocale('zh') })
function mockMap() {
  const map = { invalidateSize: vi.fn(), fitBounds: vi.fn(), setView: vi.fn(), remove: vi.fn() }
  const layer = { addTo: vi.fn().mockReturnThis(), bindPopup: vi.fn().mockReturnThis(), on: vi.fn().mockReturnThis() }
  const library = {
    map: vi.fn().mockReturnValue(map), layerGroup: vi.fn().mockReturnValue({ clearLayers: vi.fn(), addTo: vi.fn().mockReturnThis() }),
    tileLayer: vi.fn().mockReturnValue(layer), marker: vi.fn().mockReturnValue(layer),
    divIcon: vi.fn(), latLngBounds: vi.fn(), polyline: vi.fn().mockReturnValue(layer)
  }
  vi.mocked(loadScenicMap).mockResolvedValue(library)
  return library
}
function itinerary(): any {
  const leg = (from_name: string, to_name: string, meters: number, minutes: number) => ({
    from_name, to_name, meters, minutes, available: true, geometry: [[40, 116], [40.001, 116.001]],
    sections: [{ road_name: '园内步道', meters, steps: false, bridge: false }]
  })
  return {
    stops: ['仁寿殿', '长廊', '佛香阁'].map((spot_name, index) => ({ spot_id: index + 3, spot_name, order: index + 1 })),
    entry_leg: { ...leg('服务站', '仁寿殿', 186, 3), from_name_en: 'Service station', to_name_en: 'Renshou Hall' },
    legs: [leg('仁寿殿', '长廊', 420, 6), leg('长廊', '佛香阁', 800, 11)],
    exit_leg: leg('佛香阁', '东宫门', 150, 3), complete: true
  }
}
describe('Route map lifecycle', () => {
  it('keeps the complete walking list collapsed until requested without removing any legs', async () => {
    mockMap()
    wrapper = mount(RouteOverview, { attachTo: document.body, props: { overview: itinerary(), mapOnly: true }, global: { mocks: { $t: t } } })
    await flushPromises()
    const toggle = wrapper.get('.walking-legs-toggle')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    expect(wrapper.get('.walking-leg-list').isVisible()).toBe(false)
    await toggle.trigger('click')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(wrapper.get('.walking-leg-list').isVisible()).toBe(true)
    expect(wrapper.findAll('.walking-leg-list > li')).toHaveLength(4)
    await wrapper.findAll('.walking-leg-button')[2].trigger('click')
    await toggle.trigger('click')
    expect(wrapper.get('.walking-leg-list').isVisible()).toBe(false)
    expect(wrapper.find('.route-overview-map').exists()).toBe(true)
    expect(wrapper.findAll('.walking-leg-button')[2].attributes('aria-pressed')).toBe('true')
  })
  it('shows every walking leg in order, including the station approach and exit', async () => {
    const library = mockMap()
    wrapper = mount(RouteOverview, { props: { overview: itinerary(), mapOnly: true }, global: { mocks: { $t: t } } })
    await flushPromises()
    const rows = wrapper.findAll('.walking-leg-list > li')
    expect(rows).toHaveLength(4)
    expect(rows.map(row => row.get('strong').text())).toEqual(['服务站 → 仁寿殿', '仁寿殿 → 长廊', '长廊 → 佛香阁', '佛香阁 → 东宫门'])
    expect(rows.map(row => row.get('.walking-leg-content > span').text())).toEqual(['186 m · 3 分钟', '420 m · 6 分钟', '800 m · 11 分钟', '150 m · 3 分钟'])
    await rows[2].get('button').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.walking-leg-button[aria-pressed="true"]')).toHaveLength(1)
    expect(rows[2].get('button').attributes('aria-pressed')).toBe('true')
    expect(wrapper.findAll('.walking-leg-list > li')).toHaveLength(4)
    expect(library.polyline.mock.calls.slice(-4).map(call => call[1].color)).toEqual(['#a69acb', '#a69acb', '#513dbe', '#a69acb'])
    expect(rows[2].get('details').text()).toContain('园内步道')
  })
  it('refreshes all legs when a stop is removed and translates the complete route', async () => {
    mockMap()
    const route = itinerary()
    wrapper = mount(RouteOverview, { props: { overview: route, mapOnly: true }, global: { mocks: { $t: t } } })
    await flushPromises()
    await wrapper.findAll('.walking-leg-button')[2].trigger('click')
    await wrapper.setProps({ overview: { ...route, stops: route.stops.slice(0, 2), legs: route.legs.slice(0, 1), exit_leg: { ...route.exit_leg, from_name: '长廊' } } })
    await flushPromises()
    expect(wrapper.findAll('.walking-leg-list > li')).toHaveLength(3)
    expect(wrapper.get('.route-walking-legs').text()).not.toContain('佛香阁')
    expect(wrapper.findAll('.walking-leg-button')[0].attributes('aria-pressed')).toBe('true')
    setLocale('en')
    await flushPromises()
    expect(wrapper.get('.route-walking-legs h3').text()).toBe('Complete walking route')
    expect(wrapper.findAll('.walking-leg-content strong')[0].text()).toBe('Service station → Renshou Hall')
  })
  it('keeps an unconfirmed intermediate leg visible without inventing a distance', async () => {
    mockMap()
    const route = itinerary()
    route.legs[0] = { ...route.legs[0], available: false, meters: null, minutes: null, geometry: [] }
    route.complete = false
    wrapper = mount(RouteOverview, { props: { overview: route, mapOnly: true }, global: { mocks: { $t: t } } })
    await flushPromises()
    const row = wrapper.findAll('.walking-leg-list > li')[1]
    expect(row.text()).toContain('仁寿殿 → 长廊')
    expect(row.get('.route-error').text()).toBe('步行路径待确认')
    expect(row.text()).not.toMatch(/\b0 m\b/)
    expect(row.find('details').exists()).toBe(false)
  })
  it('initializes after the conditional map container mounts and removes it on exit', async () => {
    const map = { invalidateSize: vi.fn(), fitBounds: vi.fn(), setView: vi.fn(), remove: vi.fn() }
    const group = { clearLayers: vi.fn(), addTo: vi.fn().mockReturnThis() }
    const layer = {
      addTo: vi.fn().mockReturnThis(),
      bindPopup: vi.fn().mockReturnThis(),
      on: vi.fn().mockReturnThis()
    }
    const L = {
      map: vi.fn().mockReturnValue(map),
      layerGroup: vi.fn().mockReturnValue(group),
      tileLayer: vi.fn().mockReturnValue(layer),
      marker: vi.fn().mockReturnValue(layer),
      divIcon: vi.fn(),
      latLngBounds: vi.fn(),
      polyline: vi.fn().mockReturnValue(layer)
    }
    vi.mocked(loadScenicMap).mockResolvedValue(L)
    const overview: any = {
      stops: [{ spot_id: 1, spot_name: '长廊', order: 1, latitude: 40, longitude: 116 }],
      legs: [],
      complete: true
    }
    wrapper = mount(RouteOverview, {
      props: { overview, mapOnly: true },
      global: { mocks: { $t: t } }
    })
    await flushPromises()
    expect(L.map).toHaveBeenCalledTimes(1)
    expect(L.map.mock.calls[0][0]).toBe(wrapper.get('.route-overview-map').element)
    expect(L.marker).toHaveBeenCalled()
    wrapper.unmount()
    expect(map.remove).toHaveBeenCalledTimes(1)
  })
})
