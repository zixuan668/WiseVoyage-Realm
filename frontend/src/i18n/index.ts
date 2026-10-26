import { computed, ref, watch, type App } from 'vue'
import en from './en.json'

export type AppLocale = 'zh' | 'en'
const storageKey = 'zhiyou.app-language'
function savedLocale(): AppLocale {
  try { return localStorage.getItem(storageKey) === 'en' ? 'en' : 'zh' } catch { return 'zh' }
}
export const locale = ref<AppLocale>(savedLocale())
export const localeTag = computed(() => locale.value === 'en' ? 'en-US' : 'zh-CN')
const messages: Record<string,string> = en
const compoundPrefixes=Object.entries(messages).filter(([key]) => key.length >= 20 && key.endsWith('。')).sort(([a],[b])=>b.length-a.length)
const patterns = Object.entries(messages).filter(([key]) => /\{\w+\}/.test(key)).map(([key,value]) => {
  const names: string[] = []
  const escaped=key.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')
  const source=escaped.replace(/\\\{(\w+)\\\}/g, (_,name) => { names.push(name); return '(.*?)' })
  return { regex:new RegExp('^'+source+'$'), value, names }
})

/** Translate interface labels and catalogued public content. Unknown/user-authored text is preserved. */
export function t(value: unknown, params?: Record<string,unknown>): string {
  const key = String(value ?? '')
  let output = locale.value === 'en' ? (messages[key] ?? key) : key
  if (locale.value === 'en' && !messages[key]) {
    for (const pattern of patterns) {
      const match=pattern.regex.exec(key)
      if(match){output=pattern.value.replace(/\{(\w+)\}/g, (token,name) => {
        const value=match[pattern.names.indexOf(name)+1]
        return value === undefined ? token : messages[value] ?? value
      });break}
    }
    if(output === key && key.includes('；')) {
      const parts=key.split('；'), translated=parts.map(piece=>t(piece))
      if(parts.some((piece,index)=>piece!==translated[index])) output=translated.join('; ')
    }
    if(output === key && key.includes('。')) {
      const prefix=compoundPrefixes.find(([source]) => key.startsWith(source))
      if(prefix) output=prefix[1]+t(key.slice(prefix[0].length))
      else if(key.split('。').filter(Boolean).length > 1) {
        const parts=key.split('。').filter(Boolean).map(piece=>piece+'。'), translated=parts.map(piece=>t(piece))
        if(parts.some((piece,index)=>piece!==translated[index])) output=translated.join(' ')
      }
    }
    if(output === key && key.includes(' · ') && key.endsWith('路线')) {
      const parts=key.slice(0,-2).split(' · ')
      if(parts.every(piece=>messages[piece])) output=parts.map(piece=>messages[piece]).join(' · ')+' route'
    }
  }
  if (params) output = output.replace(/\{(\w+)\}/g, (match, name) => {
    const value=String(params[name] ?? match)
    return locale.value === 'en' ? messages[value] ?? value : value
  })
  return output
}
export function setLocale(value: AppLocale) {
  if (value === locale.value) return
  locale.value = value
}
watch(locale, value => {
  try { localStorage.setItem(storageKey, value) } catch { /* Optional persistence. */ }
  document.documentElement.lang = value === 'en' ? 'en' : 'zh-CN'
}, { immediate: true })

export function formatDate(value: string | number | Date, options?: Intl.DateTimeFormatOptions) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat(localeTag.value, options ?? { dateStyle:'medium', timeStyle:'short' }).format(date)
}
/** Localize read-only table cells without modifying the stored/editable value. */
export function formatTableCell(_row: unknown, column: { property?: string }, value: unknown) {
  if (value == null || value === '') return ''
  if (typeof value === 'string' && /(?:date|time|_at)$/.test(column.property || '') && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    return formatDate(value)
  }
  return t(value)
}
export function installI18n(app: App) { app.config.globalProperties.$t = t }

declare module 'vue' { interface ComponentCustomProperties { $t: typeof t } }
