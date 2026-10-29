import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import BaseLayout from '../BaseLayout.vue'

// NavbarComponent 在模块顶层会读取 pinia store，这里按组件桩的方式绕开真实接口模块。
vi.mock('@/api/user', () => ({
  getUserInfoRequest: vi.fn().mockResolvedValue({ data: { code: 0, data: {} } })
}))

const setScrollTop = vi.fn()

// 只暴露 setScrollTop，用于断言路由切换时内容区回到顶部。
const ScrollbarStub = defineComponent({
  name: 'ElScrollbar',
  setup(_props, { slots, expose }) {
    expose({ setScrollTop })
    return () => (slots.default ? slots.default() : null)
  }
})

const Page = { template: '<div class="page" />' }

const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/analytics/dashboard', component: Page },
      { path: '/analytics/feedback', component: Page }
    ]
  })

beforeEach(() => {
  setScrollTop.mockClear()
  window.matchMedia = vi.fn().mockReturnValue({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn()
  }) as unknown as typeof window.matchMedia
})

afterEach(() => {
  vi.restoreAllMocks()
})

it('resets the content scrollbar to the top when the route changes', async () => {
  const router = makeRouter()
  await router.push('/analytics/dashboard')
  await router.isReady()

  const wrapper = mount(BaseLayout, {
    global: {
      plugins: [router, createPinia(), ElementPlus],
      stubs: {
        ElScrollbar: ScrollbarStub,
        AslideComponent: true,
        NavbarComponent: true
      }
    }
  })

  try {
    await flushPromises()
    setScrollTop.mockClear()

    await router.push('/analytics/feedback')
    await flushPromises()

    expect(setScrollTop).toHaveBeenCalledWith(0)
  } finally {
    wrapper.unmount()
  }
})

it('does not touch the scroll position when the route stays the same', async () => {
  const router = makeRouter()
  await router.push('/analytics/dashboard')
  await router.isReady()

  const wrapper = mount(BaseLayout, {
    global: {
      plugins: [router, createPinia(), ElementPlus],
      stubs: {
        ElScrollbar: ScrollbarStub,
        AslideComponent: true,
        NavbarComponent: true
      }
    }
  })

  try {
    await flushPromises()
    setScrollTop.mockClear()

    await router.push('/analytics/dashboard')
    await flushPromises()

    expect(setScrollTop).not.toHaveBeenCalled()
  } finally {
    wrapper.unmount()
  }
})
