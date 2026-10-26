import { reactive } from 'vue'
import { LANGUAGE_STORAGE_KEY, translateTour } from './tour-language.js'

export const appLanguage = reactive({ value: 'zh' })

export function syncAppLanguage() {
  appLanguage.value = uni.getStorageSync(LANGUAGE_STORAGE_KEY) === 'en' ? 'en' : 'zh'
}

export function setAppLanguage(value) {
  appLanguage.value = value === 'en' ? 'en' : 'zh'
  uni.setStorageSync(LANGUAGE_STORAGE_KEY, appLanguage.value)
}

// 全局翻译入口：模板里直接写 t('中文')，语言切换时依赖 appLanguage 触发重渲染。
export function tApp(value, params) {
  return translateTour(value, appLanguage.value, params || {})
}

export const appLanguageMixin = {
  computed: {
    tourLanguage: {
      get() { return appLanguage.value },
      set(value) { setAppLanguage(value) },
    },
  },
  onShow() { syncAppLanguage() },
  methods: {
    t(value, params) { return translateTour(value, appLanguage.value, params || {}) },
    setTourLanguage(value) { setAppLanguage(value) },
  },
}
