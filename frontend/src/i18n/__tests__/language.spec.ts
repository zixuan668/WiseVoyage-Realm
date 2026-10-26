import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import LanguageSwitch from '@/components/LanguageSwitch.vue'
import { t, locale, formatDate, formatTableCell, setLocale } from '@/i18n'
import scenicDetails from './fixtures/scenic-details.json'

describe('application language', () => {
  it('translates full public attraction details and restores the exact Chinese source', () => {
    for (const spot of Object.values(scenicDetails)) {
      setLocale('en')
      for (const value of Object.values(spot)) {
        if (value.includes(';')) continue // Tags are individually rendered by the page.
        expect(t(value)).not.toMatch(/[\u3400-\u9fff]/)
      }
      const history = t(spot.history_detail)
      expect(history.length).toBeGreaterThan(spot.history_detail.length)
      setLocale('zh')
      expect(t(spot.history_detail)).toBe(spot.history_detail)
      expect(t(spot.photo_tips)).toBe(spot.photo_tips)
    }
  })
  it('updates labels without remounting a form or changing entered content', async () => {
    const Page=defineComponent({components:{LanguageSwitch},data:()=>({input:'原始输入'}),template:`<section><LanguageSwitch/><h1>{{ $t("后台登录") }}</h1><input v-model="input" :placeholder="$t('请输入账号')"/><span>{{ $t("仁寿殿") }}</span></section>`})
    const wrapper=mount(Page)
    const input=wrapper.find('input').element
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.find('h1').text()).toBe('Admin login')
    expect(wrapper.find('span').text()).toBe('Hall of Benevolence and Longevity')
    expect(wrapper.find('input').element).toBe(input)
    expect(wrapper.find('input').element.value).toBe('原始输入')
    expect(document.documentElement.lang).toBe('en')
    expect(localStorage.getItem('zhiyou.app-language')).toBe('en')
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.find('h1').text()).toBe('后台登录')
    wrapper.unmount()
  })
  it('localizes parameterized stop labels but preserves unknown user names', async () => {
    const wrapper=mount(LanguageSwitch)
    await wrapper.findAll('button')[1].trigger('click')
    expect(t('选择景点 {p0}',{p0:'长廊'})).toBe('Select stop: Long Corridor')
    expect(t('选择景点 {p0}',{p0:'游客自取昵称'})).toBe('Select stop: 游客自取昵称')
    expect(t('从 16 个景点中筛出 8 个兴趣匹配且适合当前节奏的候选，选入 3 个；停留、步行、休息、离园和预留合计 90 / 120 分钟。')).not.toContain('景点')
    expect(locale.value).toBe('en')
    wrapper.unmount()
  })
  it('uses the application locale for dates', async () => {
    const wrapper=mount(LanguageSwitch)
    await wrapper.findAll('button')[1].trigger('click')
    expect(formatDate('2026-10-12T12:00:00',{month:'short',day:'numeric'})).toBe('Oct 12')
    wrapper.unmount()
  })
  it('localizes read-only table cells while preserving unknown stored text and IDs', () => {
    setLocale('en')
    expect(formatTableCell({}, {property:'spot_name'}, '长廊')).toBe('Long Corridor')
    expect(formatTableCell({}, {property:'upload_date'}, '2026-10-12T12:00:00')).toContain('Oct 12')
    expect(formatTableCell({}, {property:'title'}, '管理员原始记录')).toBe('管理员原始记录')
    expect(formatTableCell({}, {property:'spot_id'}, 35)).toBe('35')
  })
})
