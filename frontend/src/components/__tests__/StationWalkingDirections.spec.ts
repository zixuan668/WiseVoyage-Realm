import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import StationWalkingDirections from '../StationWalkingDirections.vue'
import { namedWalkingPassages } from '@/utils/stationDirections'
import { setLocale } from '@/i18n'
import type { StationDirections } from '@/api/serviceStation'

vi.mock('../StationDirectionsMap.vue', () => ({
  default: { props: ['directions'], template: '<div class="actual-route-map" />' }
}))
const raw = [
  ['园内步道', 35, false],
  ['长廊', 59, false],
  ['园内步道', 74, false],
  ['园内步道', 5, false],
  ['园内步道', 45, false],
  ['园内步道', 203, false],
  ['园内步道', 28, false],
  ['东堤', 540, false],
  ['园内步道', 74, false],
  ['园内步道', 26, false],
  ['十七孔桥', 134, false],
  ['园内步道', 147, false],
  ['园内步道', 4, true]
] as const
const directions: StationDirections = {
  meters: 1374,
  minutes: 19,
  has_steps: true,
  geometry: [
    [40, 116],
    [40.001, 116.001]
  ],
  origin: { label: '东宫门接待站', latitude: 40, longitude: 116, node_id: 1 },
  destination: {
    label: '十七孔桥',
    label_en: 'Seventeen-Arch Bridge',
    latitude: 40.001,
    longitude: 116.001,
    node_id: 2
  },
  sections: raw.map(([road_name, meters, steps]) => ({ road_name, meters, steps }))
}
let wrapper: VueWrapper | undefined
beforeEach(() => setLocale('zh'))
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
})
const render = (route = directions) =>
  (wrapper = mount(StationWalkingDirections, {
    props: { directions: route, originName: '东宫门接待站', destinationName: '十七孔桥' }
  }))

describe('Service station walking route presentation', () => {
  it('reduces fragmented path records to named passages while retaining real route totals and geometry', () => {
    render()
    expect(wrapper!.findAll('.walking-route-passages li').map((el) => el.text())).toEqual([
      '长廊',
      '东堤'
    ])
    expect(wrapper!.text()).toContain('1.37 km')
    expect(wrapper!.text()).toContain('19')
    expect(wrapper!.text()).not.toContain('35 m')
    expect(wrapper!.text()).not.toContain('5 m')
    expect(wrapper!.find('.walking-route-steps').text()).toContain('含台阶')
    expect(wrapper!.findComponent({ name: 'StationDirectionsMap' }).props('directions').geometry).toEqual(directions.geometry)
    expect(wrapper!.find('.actual-route-map').exists()).toBe(true)
  })
  it('merges duplicate passage labels without erasing a later return to a previously named road', () => {
    const sections = ['长廊', '园内步道', '长廊', '东堤', '长廊'].map((road_name) => ({
      road_name,
      meters: 10,
      steps: false
    }))
    expect(namedWalkingPassages(sections, '出口')).toEqual(['长廊', '东堤', '长廊'])
    expect(namedWalkingPassages(sections, '长廊')).toEqual(['长廊', '东堤'])
  })
  it('shows one path passage for an unnamed route and retains a tiny stepped section warning', () => {
    render({
      ...directions,
      has_steps: false,
      sections: [
        { road_name: '', meters: 40, steps: false },
        { road_name: '园内步道', meters: 4, steps: true }
      ]
    })
    expect(wrapper!.findAll('.walking-route-passages li')).toHaveLength(1)
    expect(wrapper!.text()).toContain('沿园内步道')
    expect(wrapper!.find('.walking-route-steps').exists()).toBe(true)
  })
  it('keeps long passage lists compact and allows expansion without exposing raw fragments', async () => {
    render({
      ...directions,
      sections: ['长廊', '东堤', '玉带桥', '石舫', '苏州街'].map((road_name) => ({
        road_name,
        meters: 100,
        steps: false
      }))
    })
    expect(wrapper!.findAll('.walking-route-passages li')).toHaveLength(3)
    await wrapper!.get('.walking-route-expand').trigger('click')
    expect(wrapper!.findAll('.walking-route-passages li')).toHaveLength(5)
    setLocale('en')
    await flushPromises()
    expect(wrapper!.text()).toContain('Route outline')
    expect(wrapper!.find('.walking-route-steps').text()).toContain('includes steps')
  })
})
