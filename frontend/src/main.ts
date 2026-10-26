import { createApp } from 'vue'

import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

import ElementPlus from 'element-plus'

import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'


import '@/style/index.scss'
import '@/style/soft-ui.scss'
import '@/style/soft-ui-charts'
import '@/style/tour-backdrop.scss'
import '@/style/admin-readability.scss'
import '@/style/station-shell.scss'
import '@/style/readability.scss'
import '@/style/icons.scss'

document.documentElement.dataset.uiTheme = 'soft-ui'

// Retire the previous browser-app cache so removed pages cannot remain active
// in browsers that opened an older release of this project.
if ('serviceWorker' in navigator) {
  void navigator.serviceWorker.getRegistrations().then(registrations =>
    Promise.all(registrations.filter(registration => registration.scope === location.origin + '/')
      .map(registration => registration.unregister()))
  ).catch(() => {})
}
if ('caches' in window) {
  void caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('tour-guide-station-'))
    .map(key => caches.delete(key)))).catch(() => {})
}

import App from './App.vue'
import router from './router'
import { installI18n } from './i18n'

const app = createApp(App)
installI18n(app)

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate) // 持久化储存插件

app.use(pinia)
app.use(router)

app.use(ElementPlus, {
  locale: zhCn
})
app.mount('#app')
