import App from './App'
import { tabMotionMixin } from './common/tab-motion.js'
import { createSSRApp } from 'vue'
import { appLanguageMixin, syncAppLanguage, tApp } from './common/app-language.js'

export function createApp() {
  const app = createSSRApp(App)
  syncAppLanguage()
  app.mixin(appLanguageMixin)
  app.mixin(tabMotionMixin)
  // 模板里 t('中文') 即使拿不到 mixin 方法也能翻译（uni-app 各端模板解析差异的兜底）。
  app.config.globalProperties.t = tApp
  app.config.globalProperties.$t = tApp
  return { app }
}
