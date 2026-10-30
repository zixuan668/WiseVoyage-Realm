import { it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import Sidebar from '../AslideComponent.vue'

it('closes the guide group when navigating from routes to station management', async () => {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
  ] })
  await router.push('/tour-route/list')
  await router.isReady()
  const wrapper = mount(Sidebar, { global: { plugins: [router, ElementPlus] } })
  try {
    await flushPromises()
    const group = wrapper.findAll('.el-sub-menu').find(item => item.text().includes('导览配置'))!
    expect(group.classes()).toContain('is-opened')
    await router.push('/stations')
    await flushPromises()
    expect(group.classes()).not.toContain('is-opened')
  } finally { wrapper.unmount() }
})
