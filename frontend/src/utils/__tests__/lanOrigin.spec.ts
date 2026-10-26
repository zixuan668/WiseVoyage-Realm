import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { lanOrigin } from '../lanOrigin'

vi.mock('virtual:server-info', () => ({ serverIP: '192.0.2.15', serverPort: 5173 }))

const fetchInfo = vi.fn()
function openAt(hostname: string, origin: string) {
  vi.stubGlobal('window', { location: { hostname, origin } })
}
beforeEach(() => {
  vi.stubEnv('VITE_PUBLIC_SERVER_ORIGIN', '')
  vi.stubGlobal('fetch', fetchInfo)
  fetchInfo.mockReset()
  openAt('localhost', 'http://localhost:5173')
})
afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('LAN QR origin', () => {
  it.each([
    ['http://192.0.2.10:18000', 'http://192.0.2.10:18000'],
    ['https://guide.example.test', 'https://guide.example.test'],
    ['http://localhost:18000/', 'http://localhost:18000'],
    ['http://[2001:db8::1]:18000', 'http://[2001:db8::1]:18000'],
    [' HTTPS://GUIDE.EXAMPLE.TEST:443/ ', 'https://guide.example.test'],
  ])('prefers configured HTTP(S) origin %s', async (configured, expected) => {
    vi.stubEnv('VITE_PUBLIC_SERVER_ORIGIN', configured)
    openAt('guide.internal', 'http://guide.internal:8080')
    expect(await lanOrigin()).toBe(expected)
    expect(fetchInfo).not.toHaveBeenCalled()
  })

  it.each([
    'ftp://guide.example.test', 'javascript:alert(1)', '//guide.example.test',
    'http://user:password@guide.example.test', 'http://@guide.example.test',
    'http://guide.example.test/path', 'http://guide.example.test/./',
    'http://guide.example.test/%2e/', 'http://guide.example.test//',
    'http://guide.example.test?key=value', 'http://guide.example.test?',
    'http://guide.example.test#section', 'http://guide.example.test#',
    'http://guide.example.test\\path', 'http://guide.example.test:bad',
    'http://', 'not a URL',
  ])('ignores invalid origin %s and preserves the existing source', async (configured) => {
    vi.stubEnv('VITE_PUBLIC_SERVER_ORIGIN', configured)
    openAt('guide.internal', 'http://guide.internal:8080')
    expect(await lanOrigin()).toBe('http://guide.internal:8080')
    expect(fetchInfo).not.toHaveBeenCalled()
  })

  it.each(['localhost', '127.0.0.1'])('keeps live LAN lookup for %s when unconfigured', async hostname => {
    openAt(hostname, `http://${hostname}:5173`)
    fetchInfo.mockResolvedValue({ json: async () => ({ ip: '192.0.2.25', port: 5180 }) })
    expect(await lanOrigin()).toBe('http://192.0.2.25:5180')
    expect(fetchInfo).toHaveBeenCalledWith('/__lan-info', { cache: 'no-store' })
  })

  it('keeps the injected development port when LAN information has no port', async () => {
    fetchInfo.mockResolvedValue({ json: async () => ({ ip: '192.0.2.25' }) })
    expect(await lanOrigin()).toBe('http://192.0.2.25:5173')
  })

  it('keeps the build-time fallback after failed LAN lookup', async () => {
    fetchInfo.mockRejectedValue(new Error('unavailable'))
    expect(await lanOrigin()).toBe('http://192.0.2.15:5173')
  })

  it('keeps the build-time fallback after invalid LAN JSON', async () => {
    fetchInfo.mockResolvedValue({ json: async () => { throw new Error('invalid JSON') } })
    expect(await lanOrigin()).toBe('http://192.0.2.15:5173')
  })
})
