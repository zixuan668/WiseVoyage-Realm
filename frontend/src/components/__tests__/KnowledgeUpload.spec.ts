import { afterEach, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import KnowledgeBaseView from '@/views/knowledge/KnowledgeBaseView.vue'

vi.mock('@/api/knowledgeBase', () => ({
  getDocList: vi.fn().mockResolvedValue({ data: { code: 0, data: { doc_list: [], currentPage: 1, pageSize: 10, totalSize: 0 } } }),
  uploadDoc: vi.fn(), deleteDoc: vi.fn(), rebuildIndex: vi.fn(), testAccuracy: vi.fn(),
}))

afterEach(() => { vi.restoreAllMocks() })

it('clicking the upload text activates the native file chooser once', async () => {
  const wrapper = mount(KnowledgeBaseView, { global: { plugins: [ElementPlus] } })
  try {
    const input = wrapper.get('input[type="file"]').element as HTMLInputElement
    const click = vi.spyOn(input, 'click').mockImplementation(() => {})
    await wrapper.get('.el-upload__text em').trigger('click')
    expect(click).toHaveBeenCalledTimes(1)
    expect(input.disabled).toBe(false)
    expect(input.accept).toBe('.pdf,.docx,.doc,.txt,.md')
  } finally { wrapper.unmount() }
})
