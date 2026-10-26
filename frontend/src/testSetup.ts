import { beforeEach } from 'vitest'
import { config } from '@vue/test-utils'
import { t, setLocale } from '@/i18n'
config.global.mocks.$t = t
beforeEach(() => setLocale('zh'))
