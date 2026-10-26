import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ScenicVisitContext from '../ScenicVisitContext.vue'

let wrapper: VueWrapper | undefined
const props = { latitude: 39.999, longitude: 116.273, spotCount: 6, routeCount: 3, guideCount: 3 }
const forecast = (temperature = 0, code = 0, isDay = 1) => ({
  ok: true,
  json: async () => ({
    current: {
      time: '2026-10-10T17:00',
      temperature_2m: temperature,
      weather_code: code,
      is_day: isDay,
      relative_humidity_2m: 35,
      wind_speed_10m: 8.7
    },
    daily: {
      temperature_2m_max: [27],
      temperature_2m_min: [15],
      precipitation_probability_max: [0]
    }
  })
})
const render = () => mount(ScenicVisitContext, { props, global: { stubs: { ElIcon: true } } })
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  vi.unstubAllGlobals()
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('scenic weather information', () => {
  it('shows the station weather without catalog counts and uses a moon at night', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(forecast(13, 0, 0)))
    wrapper = mount(ScenicVisitContext, {
      props: { latitude: 40, longitude: 116, weatherOnly: true },
      global: { stubs: { ElIcon: { template: '<span><slot /></span>' } } }
    })
    await flushPromises()
    expect(wrapper.find('.context-overview').exists()).toBe(false)
    expect(wrapper.get('.weather-current strong').text()).toBe('13°C')
    expect(wrapper.findComponent({ name: 'Moon' }).exists()).toBe(true)
  })

  it('refreshes the unattended station every 15 minutes and stops after leaving', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValueOnce(forecast(13)).mockResolvedValue(forecast(14))
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)
    wrapper = mount(ScenicVisitContext, {
      props: { latitude: 40, longitude: 116, weatherOnly: true },
      global: { stubs: { ElIcon: true } }
    })
    await flushPromises()
    await vi.advanceTimersByTimeAsync(15 * 60 * 1000)
    expect(wrapper.get('.weather-current strong').text()).toBe('14°C')
    expect(fetchMock).toHaveBeenCalledTimes(2)
    wrapper.unmount()
    wrapper = undefined
    await vi.advanceTimersByTimeAsync(15 * 60 * 1000)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('uses snow guidance rather than rain guidance for snowfall', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(forecast(-2, 73)))
    wrapper = render()
    await flushPromises()
    expect(wrapper.get('.context-tip').text()).toContain('有雪')
    expect(wrapper.get('.context-tip').text()).not.toContain('雨具')
  })
  it('displays zero values and sends only scenic coordinates without credentials', async () => {
    const fetchMock = vi.fn().mockResolvedValue(forecast())
    vi.stubGlobal('fetch', fetchMock)
    wrapper = render()
    await flushPromises()
    expect(wrapper.find('.weather-current strong').text()).toBe('0°C')
    expect(wrapper.find('.weather-details dd').text()).toBe('0%')
    expect(wrapper.find('.context-counts').text()).toContain('6景点')
    expect(fetchMock.mock.calls[0][1].credentials).toBe('omit')
    expect(new URL(fetchMock.mock.calls[0][0]).searchParams.get('latitude')).toBe('39.999')
  })

  it('shows an unavailable state for invalid data and supports retry', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ current: { temperature_2m: null } })
      })
      .mockResolvedValueOnce(forecast(25))
    vi.stubGlobal('fetch', fetchMock)
    wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('天气暂时不可用')
    expect(wrapper.find('.weather-current').exists()).toBe(false)
    await wrapper.find('.weather-empty button').trigger('click')
    await flushPromises()
    expect(wrapper.find('.weather-current strong').text()).toBe('25°C')
  })

  it('ignores a previous coordinate request that finishes later', async () => {
    let complete!: (value: unknown) => void
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            complete = resolve
          })
      )
      .mockResolvedValueOnce(forecast(22))
    vi.stubGlobal('fetch', fetchMock)
    wrapper = render()
    await wrapper.setProps({ latitude: 40.01 })
    await flushPromises()
    complete(forecast(99))
    await flushPromises()
    expect(wrapper.find('.weather-current strong').text()).toBe('22°C')
  })
})
