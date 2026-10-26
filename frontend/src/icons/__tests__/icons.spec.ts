import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { House, Delete, Guide } from '@/icons'

describe('shared functional icons', () => {
  it.each([House, Delete, Guide])('renders a currentColor vector with a stable grid', component => {
    const wrapper = mount(component)
    expect(wrapper.element.tagName.toLowerCase()).toBe('svg')
    expect(wrapper.attributes('viewBox')).toBe('0 0 24 24')
    expect(wrapper.attributes('stroke')).toBe('currentColor')
    expect(wrapper.attributes('fill')).toBe('none')
    expect(wrapper.attributes('aria-hidden')).toBe('true')
    expect(wrapper.findAll('path,rect,circle,line,polyline,polygon').length).toBeGreaterThan(0)
  })
  it('preserves an accessible name and explicit sizing when requested', () => {
    const wrapper = mount(Delete, { props: { size: 20, title: '删除景点' } })
    expect(wrapper.attributes('aria-hidden')).toBeUndefined()
    expect(wrapper.attributes('role')).toBe('img')
    expect(wrapper.find('title').text()).toBe('删除景点')
    expect(wrapper.attributes('width')).toBe('20')
  })
})
