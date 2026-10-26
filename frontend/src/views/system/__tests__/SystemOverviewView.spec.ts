import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import SystemOverviewView from '../SystemOverviewView.vue'
import { request_handler } from '@/api/base'
import { setLocale } from '@/i18n'

vi.mock('@/api/base', () => ({ request_handler: vi.fn() }))
vi.mock('@/api/user', () => ({ header_authorization: { value: 'Bearer test' } }))

let wrapper: VueWrapper
afterEach(() => wrapper?.unmount())

async function render(xingyunConfigured: boolean, musetalkAvailable: boolean, language: 'zh' | 'en' = 'zh') {
  setLocale(language)
  vi.mocked(request_handler).mockResolvedValueOnce({ data: {
    database: { status: 'connected' },
    llm: { status: 'local_fallback', api_base: 'example.test', model: 'test-model', key_configured: false },
    tts: { status: 'configured', engine: 'Edge TTS' },
    asr: { status: 'configured', engine: 'qwen3-asr-flash（阿里云百炼）' },
    rag: { status: 'available' },
    digital_human: { status: musetalkAvailable ? 'available' : xingyunConfigured ? 'configured' : 'unavailable', xingyun_configured: xingyunConfigured, musetalk_available: musetalkAvailable },
    python_version: '3.10.0'
  } } as any)
  wrapper = mount(SystemOverviewView, { global: {
    stubs: ['el-button', 'el-row', 'el-col', 'el-card', 'el-tag', 'el-descriptions', 'el-descriptions-item', 'el-alert'],
    directives: { loading: {} },
    renderStubDefaultSlot: true
  } })
  await flushPromises()
  return wrapper
}

describe('system service status', () => {
  it('shows returned speech engines, local LLM fallback, lexical RAG, and configured Xingyun separately from optional MuseTalk', async () => {
    const page = await render(true, false)
    expect(page.text()).toContain('Edge TTS')
    expect(page.text()).toContain('qwen3-asr-flash（阿里云百炼）')
    expect(page.text()).toContain('BM25 + TF-IDF 景区知识检索')
    expect(page.text()).toContain('本地回退')
    expect(page.text()).toContain('星云应用：已配置；MuseTalk：未启用')
    expect(page.text()).not.toMatch(/GPT-SoVITS|FunASR|向量数据库/)
  })

  it('shows an available optional MuseTalk worker without claiming Xingyun is configured', async () => {
    expect((await render(false, true)).text()).toContain('星云应用：未配置；MuseTalk：正常')
  })

  it('translates service states and retrieval details in English', async () => {
    const page = await render(false, false, 'en')
    expect(page.text()).toContain('Xingyun app: Not configured; MuseTalk: Not enabled')
    expect(page.text()).toContain('BM25 + TF-IDF scenic knowledge retrieval')
    expect(page.text()).toContain('Local fallback')
    expect(page.text()).toContain('qwen3-asr-flash (Alibaba Cloud Bailian)')
  })
})
