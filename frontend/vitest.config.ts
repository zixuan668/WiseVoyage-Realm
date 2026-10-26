import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import type { UserConfig } from 'vite'
import viteConfig from './vite.config'

export default defineConfig((env) => {
  const baseConfig = typeof viteConfig === 'function' ? viteConfig(env) : viteConfig
  return mergeConfig(
    baseConfig as UserConfig,
    {
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/testSetup.ts'],
      exclude: [...configDefaults.exclude, 'e2e/**'],
      root: fileURLToPath(new URL('./', import.meta.url))
    }
    },
  )
})
