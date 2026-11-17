<template>
  <view class="guide-page" :class="{ 'guide-notice-page': notices }">
    <view class="guide-header">
      <button class="guide-back app-back-btn" :aria-label="t('返回')" @tap="back"><view class="app-back-icon" aria-hidden="true"></view></button>
      <text class="guide-title" role="heading">{{ t(notices ? '官方通知' : '景区导览地图') }}</text>
    </view>

    <scroll-view v-if="notices" scroll-y class="notice-scroll" :show-scrollbar="false">
      <view class="notice-inner">
        <view class="notice-hero">
          <view class="notice-date">
            <text class="notice-month">{{ noticeCalendar.month }}</text>
            <view class="notice-day">
              <text class="notice-day-num">{{ noticeCalendar.day }}</text>
              <text v-if="noticeCalendar.dayUnit" class="notice-day-unit">{{ t(noticeCalendar.dayUnit) }}</text>
            </view>
          </view>
          <view class="notice-week">
            <view v-for="day in noticeCalendar.week" :key="day.key" class="notice-week-cell" :class="{ on: day.selected, today: day.today }" role="button" :aria-label="day.ariaLabel" @tap="selectNoticeDay(day)">
              <text class="notice-week-num">{{ day.day }}</text>
              <text class="notice-week-label">{{ day.label }}</text>
            </view>
          </view>
        </view>

        <template v-if="visibleNotices.length">
          <view class="notice-toolbar">
            <text class="notice-count">{{ t('共 {count} 条', { count: visibleNotices.length }) }}</text>
          </view>

          <view class="notice-timeline">
            <view class="notice-rail" aria-hidden="true"></view>
            <view v-for="(item, index) in visibleNotices" :key="item.id" class="notice-row" :class="{ featured: index === 0 }">
              <view class="notice-node" aria-hidden="true"></view>
              <button class="notice-card" @tap="openNotice(item)">
                <view class="notice-card-head">
                  <view class="notice-icon"><DashboardIcon :name="item.icon" /></view>
                  <view class="notice-heading">
                    <view class="notice-kicker">
                      <text class="notice-category">{{ lang(item.category) }}</text>
                      <text class="notice-sep" aria-hidden="true">|</text>
                      <text class="notice-title">{{ lang(item.title) }}</text>
                    </view>
                    <text class="notice-detail">{{ lang(item.summary) }}</text>
                  </view>
                </view>
                <view class="notice-card-foot">
                  <text class="notice-source">{{ t('来源：颐和园官网') }}</text>
                  <text class="notice-read">{{ t('阅读全文') }}<text class="notice-chevron">›</text></text>
                </view>
              </button>
            </view>
          </view>
        </template>
      </view>
    </scroll-view>
    <template v-else>
      <movable-area class="guide-stage" :scale-area="true">
        <movable-view :key="resetVersion" direction="all" :scale="true"
          :scale-min="1" :scale-max="4" :scale-value="zoomCommand" :animation="false" @scale="onScale" class="guide-pan">
          <image class="guide-image" :src="mapImage" mode="aspectFit"
            :aria-label="t('颐和园官方导览地图')" @load="loaded = true" @error="imageFailed" />
        </movable-view>
      </movable-area>
      <view class="guide-footer">
        <text v-if="failed" class="guide-error">{{ t('导览图加载失败，请打开颐和园官网') }}</text>
        <view class="guide-tools">
          <button :disabled="!loaded || zoom <= 1" :aria-label="t('缩小地图')" @tap="changeZoom(-.5)"><WanderIcon name="minus" /></button>
          <button :disabled="!loaded" @tap="reset">{{ t('适应屏幕') }}</button>
          <button :disabled="!loaded || zoom >= 4" :aria-label="t('放大地图')" @tap="changeZoom(.5)"><WanderIcon name="plus" /></button>
        </view>
        <text class="guide-source">{{ t('来源：颐和园官网') }}</text>
      </view>
    </template>

    <!-- 公告详情：卡片变整页（原卡片区域放大 → 内容替换 → 逐行错峰） -->
    <view v-if="activeNotice" class="notice-page" :class="{ 'is-closing': detailClosing }" :style="detailOriginStyle">
      <view class="notice-detail-head">
        <button class="guide-back app-back-btn notice-detail-back" :aria-label="t('返回')" @tap="closeNotice"><view class="app-back-icon" aria-hidden="true"></view></button>
        <text class="notice-detail-head-title">{{ lang(activeNotice.category) }}</text>
      </view>
      <scroll-view scroll-y class="notice-detail-scroll" :show-scrollbar="false">
        <view class="notice-detail-body" :class="{ 'is-in': detailReady }">
          <text class="notice-detail-title">{{ lang(activeNotice.title) }}</text>
          <text class="notice-detail-lead">{{ lang(activeNotice.summary) }}</text>
          <text class="notice-detail-meta">{{ t('来源：颐和园官网') }} · {{ t('核对日期') }} {{ noticeCheckedOn }}</text>

          <view v-if="activeNotice.hours" class="notice-hours">
            <text class="notice-hours-caption">{{ lang(activeNotice.hours.caption) }}</text>
            <view class="notice-season-row">
              <button v-for="season in activeNotice.hours.seasons" :key="season.key" class="notice-season" :class="{ on: noticeSeason === season.key }" @tap="noticeSeason = season.key">{{ lang(season.label) }}</button>
            </view>
            <view class="notice-hour-cards">
              <view v-for="row in noticeSeasonRows" :key="row.time" class="notice-hour-card">
                <text class="notice-hour-label">{{ lang(row.label) }}</text>
                <text class="notice-hour-time">{{ row.time }}</text>
                <text class="notice-hour-note">{{ lang(row.note) }}</text>
              </view>
            </view>
            <view class="notice-reminder"><text>{{ lang(activeNotice.hours.reminder) }}</text></view>
          </view>

          <view v-for="(section, index) in activeNotice.sections" :key="index" class="notice-article-section">
            <view class="notice-article-heading"><view class="notice-article-bar" aria-hidden="true"></view><text>{{ lang(section.heading) }}</text></view>
            <text v-for="(paragraph, pIndex) in section.paragraphs" :key="pIndex" class="notice-article-text">{{ lang(paragraph) }}</text>
          </view>

        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script>
import WanderIcon from '../../components/WanderIcon.vue'
import DashboardIcon from '../../components/DashboardIcon.vue'
import { NOTICE_CHECKED_ON, noticeArticles } from '../../common/park-notices.js'

const site = 'https://www.summerpalace.net.cn'
const officialImage = site + '/Public/static/themes/image/pinning_img1.jpg'
const WEEK_LABELS_ZH = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const WEEK_LABELS_EN = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export default {
  components: { WanderIcon, DashboardIcon },
  data() {
    return {
      officialNotices: noticeArticles,
      noticeCheckedOn: NOTICE_CHECKED_ON,
      selectedDayKey: 0,
      activeNotice: null, detailReady: false, detailClosing: false, noticeBusy: false,
      detailOriginStyle: {}, noticeSeason: 'peak',
      notices: false,
      mapImage: '/static/park-dashboard/official-guide.webp',
      loaded: false, failed: false, zoom: 1, zoomCommand: 1, resetVersion: 0,
    }
  },
  computed: {
    noticeCalendar() {
      const now = new Date()
      const en = this.tourLanguage === 'en'
      const labels = en ? WEEK_LABELS_EN : WEEK_LABELS_ZH
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      const todayKey = today.getTime()
      const selectedKey = this.selectedDayKey || todayKey
      const monday = new Date(today)
      monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7))
      const week = []
      for (let i = 0; i < 7; i++) {
        const day = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i)
        const key = day.getTime()
        week.push({
          key,
          day: day.getDate(),
          label: labels[day.getDay()],
          today: key === todayKey,
          selected: key === selectedKey,
          ariaLabel: en ? MONTHS_EN[day.getMonth()] + ' ' + day.getDate() : (day.getMonth() + 1) + '月' + day.getDate() + '日',
        })
      }
      const selected = new Date(selectedKey)
      return {
        month: en ? MONTHS_EN[selected.getMonth()] + ' ' + selected.getFullYear() : selected.getFullYear() + '年' + (selected.getMonth() + 1) + '月',
        day: selected.getDate(),
        dayUnit: en ? '' : '日',
        week,
      }
    },
    visibleNotices() {
      const now = new Date()
      const todayKey = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
      const selectedKey = this.selectedDayKey || todayKey
      // 目前内置的两条公告属于“今天”；切到其他日期时列表留空。
      return selectedKey === todayKey ? this.officialNotices : []
    },
    noticeSeasonRows() {
      const hours = this.activeNotice && this.activeNotice.hours
      if (!hours) return []
      const season = hours.seasons.find(item => item.key === this.noticeSeason) || hours.seasons[0]
      return season ? season.rows : []
    },
  },
  onLoad(query) { this.notices = query?.view === 'notices' },
  onBackPress() {
    if (this.activeNotice) { this.closeNotice(); return true }
    return false
  },
  onUnload() { clearTimeout(this._noticeTimer) },
  methods: {
    lang(value) {
      if (!value) return ''
      return this.tourLanguage === 'en' ? (value.en || value.zh || '') : (value.zh || value.en || '')
    },
    back() { uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/tabs/tabs' }) }) },
    selectNoticeDay(day) {
      if (day && day.key) this.selectedDayKey = day.key
    },
    openNotice(notice) {
      if (this.noticeBusy || !notice) return
      const index = this.visibleNotices.findIndex(item => item.id === notice.id)
      if (index < 0) return
      this.noticeBusy = true
      const month = new Date().getMonth() + 1
      this.noticeSeason = month >= 4 && month <= 10 ? 'peak' : 'quiet'
      this.noticeOrigin('.notice-card', index, () => {
        this.activeNotice = notice
        this.detailReady = false
        this.detailClosing = false
        clearTimeout(this._noticeTimer)
        // 卡片放大到整页约 320ms 后再让正文逐行进入
        this._noticeTimer = setTimeout(() => {
          this.detailReady = true
          this.noticeBusy = false
        }, 300)
      })
    },
    noticeOrigin(selector, index, next) {
      const query = uni.createSelectorQuery().in(this)
      query.selectAll(selector).boundingClientRect()
      query.exec(rects => {
        const rect = rects && rects[index]
        let style = { '--notice-top': '34%', '--notice-right': '10%', '--notice-bottom': '46%', '--notice-left': '10%' }
        try {
          const info = uni.getSystemInfoSync()
          if (rect && rect.width && info && info.windowWidth) {
            const inset = value => Math.max(0, Math.round(value)) + 'px'
            style = {
              '--notice-top': inset(rect.top),
              '--notice-right': inset(info.windowWidth - rect.right),
              '--notice-bottom': inset(info.windowHeight - rect.bottom),
              '--notice-left': inset(rect.left),
            }
          }
        } catch (error) {}
        this.detailOriginStyle = style
        next()
      })
    },
    closeNotice() {
      if (!this.activeNotice || this.noticeBusy) return
      this.noticeBusy = true
      this.detailClosing = true
      clearTimeout(this._noticeTimer)
      this._noticeTimer = setTimeout(() => {
        this.activeNotice = null
        this.detailClosing = false
        this.noticeBusy = false
      }, 230)
    },
    onScale(event) {
      const value = Number(event.detail?.scale)
      if (Number.isFinite(value)) this.zoom = value
    },
    changeZoom(amount) {
      const target = Math.max(1, Math.min(4, this.zoom + amount))
      // A pinch moves the live value independently of the last button command.
      if (target === this.zoomCommand) this.zoomCommand = this.zoom
      this.$nextTick(() => { this.zoomCommand = target })
    },
    reset() { this.zoom = this.zoomCommand = 1; this.resetVersion++ },
    imageFailed() {
      if (this.mapImage !== officialImage) this.mapImage = officialImage
      else this.failed = true
    },
  },
}
</script>

<style scoped>
.guide-page {
  display: flex; flex-direction: column; width: 100%; height: 100vh; height: 100dvh;
  box-sizing: border-box; padding: var(--status-bar-height, 0px) 0 env(safe-area-inset-bottom);
  background: #f7f4ff; color: #302451;
}
.guide-header { height: 62px; display: flex; align-items: center; padding: 0 14px; gap: 12px; flex: none; font-size: 19px; }
.guide-header, .guide-footer { position: relative; z-index: 1; background: #f7f4ff; }
.guide-page:not(.guide-notice-page) .guide-header::after, .guide-footer::before {
  content: ''; position: absolute; left: 0; right: 0; height: 16px; pointer-events: none;
}
.guide-page:not(.guide-notice-page) .guide-header::after {
  top: 100%; background: linear-gradient(to bottom, #f7f4ff, #fff0);
}
.guide-footer::before { bottom: 100%; background: linear-gradient(to top, #f7f4ff, #fff0); }
.guide-page button { margin: 0; border: 0; padding: 0; color: inherit; line-height: inherit; font: inherit; }
.guide-page button::after { border: 0; }
/* 返回键外观由全局 .app-back-btn 统一，这里只保留工具按钮的浅紫圆角 */
.guide-page .guide-tools button {
  display: grid; place-items: center; min-height: 44px; min-width: 44px;
  border-radius: 14px; background: #ede6fb; color: #58428a;
}
.guide-stage { flex: 1; width: 100%; height: auto; min-height: 0; overflow: hidden; background: #fff; }
.guide-stage, .guide-pan { touch-action: none; }
.guide-pan, .guide-image { width: 100%; height: 100%; }
.guide-image { pointer-events: none; }
.guide-footer { flex: none; display: grid; justify-items: center; padding: 10px 16px 5px; }
.guide-tools { display: flex; gap: 8px; }
.guide-tools button:nth-child(2) { padding: 0 14px; font-size: 13px; }
.guide-tools button[disabled] { opacity: .5; }
.guide-source { font-size: 12px; padding: 10px 14px; color: #6b6278; white-space: nowrap; }
.guide-error { font-size: 13px; margin-bottom: 8px; }

/* ===== 官方通知：日期头 + 时间线 ===== */
.guide-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.guide-notice-page { background: linear-gradient(168deg, #fbf9ff 0%, #f3eeff 46%, #eef4fc 100%); }
.guide-notice-page .guide-header { justify-content: center; background: transparent; }
.guide-notice-page .guide-title {
  position: absolute; left: 50%; transform: translateX(-50%);
  font-size: 18px; font-weight: 600; color: #2a2438; letter-spacing: .02em;
}
.guide-notice-page .guide-back { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); }
.notice-scroll { flex: 1; width: 100%; height: 0; min-height: 0; }
.notice-inner { max-width: 560px; margin: 0 auto; box-sizing: border-box; padding-bottom: calc(env(safe-area-inset-bottom) + 24px); }
.notice-hero { display: flex; align-items: flex-end; gap: 14px; padding: 4px 16px 0; }
.notice-date { flex: none; min-width: 74px; }
.notice-month { display: block; font-size: 12px; color: #8a7fb0; letter-spacing: .04em; }
.notice-day { display: flex; align-items: flex-start; margin-top: 1px; }
.notice-day-num { font-family: Georgia, "Times New Roman", serif; font-size: 46px; line-height: 1; font-weight: 700; color: #2a2438; letter-spacing: -.02em; }
.notice-day-unit { margin: 8px 0 0 3px; font-size: 13px; color: #6d6480; }
.notice-week { flex: 1; min-width: 0; display: flex; align-items: stretch; gap: 2px; padding-bottom: 4px; }
.notice-week-cell { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 6px 0 7px; border-radius: 12px; }
.notice-week-num { font-size: 15px; font-weight: 600; color: #4a4358; line-height: 1.1; }
.notice-week-label { font-size: 9px; color: #9a92ad; line-height: 1.2; white-space: nowrap; }
.notice-week-cell.on { background: linear-gradient(135deg, #6a5ae0 0%, #8b78e6 100%); box-shadow: 0 8px 16px -9px rgba(88, 66, 190, .65); }
.notice-week-cell.on .notice-week-num, .notice-week-cell.on .notice-week-label { color: #fff; }
.notice-week-cell.today:not(.on) .notice-week-num { color: #6a5ae0; }
.notice-week-cell.today:not(.on) .notice-week-label { color: #8b78e6; }
.notice-toolbar { display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding: 8px 16px 12px; }
.notice-count { flex: none; padding: 5px 11px; border-radius: 999px; background: rgba(255, 255, 255, .78); border: 1px solid rgba(139, 120, 230, .24); color: #6a5ae0; font-size: 11px; line-height: 1.3; }
.notice-timeline { position: relative; padding: 0 16px; }
.notice-rail { position: absolute; left: 29px; top: 32px; bottom: 10px; width: 1px; background: linear-gradient(180deg, rgba(139, 120, 230, .20) 0%, rgba(139, 120, 230, .10) 55%, rgba(139, 120, 230, 0) 100%); z-index: 1; }
.notice-row { position: relative; padding-left: 26px; margin-bottom: 14px; }
.notice-row:last-child { margin-bottom: 0; }
.notice-node { position: absolute; left: 7px; top: 26px; width: 9px; height: 9px; border-radius: 50%; background: #fff; border: 2px solid #8b78e6; box-shadow: 0 0 0 3px rgba(139, 120, 230, .10); z-index: 2; }
.notice-row.featured .notice-node { background: #6a5ae0; border-color: #6a5ae0; }
/* 用 .guide-page 前缀保证优先级高于页面级 button 重置 */
.guide-page .notice-card { display: block; width: 100%; box-sizing: border-box; margin: 0; padding: 13px 14px 11px; text-align: left; border-radius: 18px; background: #fff; border: 1px solid rgba(139, 120, 230, .16); box-shadow: 0 12px 26px -22px rgba(70, 54, 130, .4); }
.guide-page .notice-card:active { transform: scale(.99); }
.notice-card-head { display: flex; align-items: flex-start; gap: 10px; }
.notice-icon { flex: none; width: 40px; height: 40px; border-radius: 13px; display: grid; place-items: center; background: #f0ebff; color: #6a5ae0; }
.notice-heading { flex: 1; min-width: 0; }
.notice-kicker { display: flex; align-items: baseline; flex-wrap: wrap; column-gap: 5px; row-gap: 2px; }
.notice-category { font-size: 13px; font-weight: 600; color: #6a5ae0; }
.notice-sep { font-size: 11px; color: #cdc4e4; }
.notice-title { font-size: 14.5px; font-weight: 700; color: #2a2438; line-height: 1.35; }
.notice-detail { display: -webkit-box; margin-top: 5px; font-size: 11.5px; line-height: 1.55; color: #7d748c; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.notice-badge { flex: none; padding: 2px 7px; border-radius: 999px; background: #f3efff; color: #6a5ae0; font-size: 9.5px; line-height: 1.7; }
.notice-card-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 10px; padding-top: 8px; border-top: 1px dashed rgba(139, 120, 230, .2); }
.notice-source { font-size: 10px; color: #a29ab0; }
.notice-read { display: flex; align-items: center; gap: 1px; font-size: 10.5px; color: #6a5ae0; }
.notice-chevron { font-size: 13px; line-height: 1; }
/* 首条强调：深紫渐变卡片 */
.notice-row.featured .notice-card { background: linear-gradient(140deg, #5b46c9 0%, #6c55d8 54%, #8b78e6 100%); border-color: transparent; box-shadow: 0 20px 36px -22px rgba(80, 58, 190, .85); }
.notice-row.featured .notice-icon { background: rgba(255, 255, 255, .18); color: #fff; }
.notice-row.featured .notice-category { color: #eae4ff; }
.notice-row.featured .notice-sep { color: rgba(255, 255, 255, .4); }
.notice-row.featured .notice-title { color: #fff; }
.notice-row.featured .notice-detail { color: rgba(255, 255, 255, .82); }
.notice-row.featured .notice-badge { background: rgba(255, 255, 255, .16); color: #fff; }
.notice-row.featured .notice-card-foot { border-top-color: rgba(255, 255, 255, .2); }
.notice-row.featured .notice-source { color: rgba(255, 255, 255, .62); }
.notice-row.featured .notice-read { color: #fff; }


/* ===== 公告详情：卡片放大成整页（01 卡片变整页） ===== */
.notice-page {
  position: fixed; top: 0; right: 0; bottom: 0; left: 0; z-index: 60; display: flex; flex-direction: column;
  background: linear-gradient(168deg, #fbf9ff 0%, #f3eeff 46%, #eef4fc 100%);
  padding-top: var(--status-bar-height, 20px);
  animation: noticeExpand 320ms cubic-bezier(.2, .75, .25, 1) both;
}
@keyframes noticeExpand {
  from { clip-path: inset(var(--notice-top, 34%) var(--notice-right, 10%) var(--notice-bottom, 46%) var(--notice-left, 10%) round 16px); opacity: .82; }
  to { clip-path: inset(0 0 0 0 round 0); opacity: 1; }
}
.notice-page.is-closing { animation: noticeCollapse 230ms cubic-bezier(.4, 0, .62, 1) both; }
@keyframes noticeCollapse {
  from { clip-path: inset(0 0 0 0 round 0); opacity: 1; }
  to { clip-path: inset(var(--notice-top, 34%) var(--notice-right, 10%) var(--notice-bottom, 46%) var(--notice-left, 10%) round 16px); opacity: .65; }
}
.notice-detail-head { position: relative; flex: none; height: 56px; display: flex; align-items: center; justify-content: center; padding: 0 16px; }
.notice-detail-back { position: absolute; left: 16px; top: 50%; transform: translateY(-50%); }
.notice-detail-head-title { font-size: 17px; font-weight: 600; color: #2a2438; letter-spacing: .02em; }
.notice-detail-scroll { flex: 1; height: 0; min-height: 0; }
.notice-detail-body { max-width: 560px; margin: 0 auto; padding: 2px 20px calc(env(safe-area-inset-bottom) + 28px); box-sizing: border-box; }
.notice-detail-body > * { opacity: 0; }
.notice-detail-body.is-in > * { animation: noticeLineIn 340ms cubic-bezier(.2, .7, .2, 1) both; }
.notice-detail-body.is-in > *:nth-child(1) { animation-delay: 40ms; }
.notice-detail-body.is-in > *:nth-child(2) { animation-delay: 95ms; }
.notice-detail-body.is-in > *:nth-child(3) { animation-delay: 150ms; }
.notice-detail-body.is-in > *:nth-child(4) { animation-delay: 200ms; }
.notice-detail-body.is-in > *:nth-child(5) { animation-delay: 250ms; }
.notice-detail-body.is-in > *:nth-child(6) { animation-delay: 300ms; }
.notice-detail-body.is-in > *:nth-child(7) { animation-delay: 345ms; }
.notice-detail-body.is-in > *:nth-child(8) { animation-delay: 390ms; }
@keyframes noticeLineIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: none; }
}
.notice-detail-tag { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 999px; background: #f0ebff; color: #6a5ae0; font-size: 11px; line-height: 1.4; }
.notice-detail-title { display: block; margin-top: 12px; font-size: 24px; line-height: 1.35; font-weight: 700; color: #241f31; letter-spacing: .01em; }
.notice-detail-lead { display: block; margin-top: 10px; font-size: 13.5px; line-height: 1.7; color: #6f6685; }
.notice-detail-meta { display: block; margin-top: 8px; font-size: 11px; color: #a29ab0; }
.notice-hours { margin-top: 18px; padding: 14px 14px 12px; border-radius: 18px; background: #fff; border: 1px solid rgba(139, 120, 230, .16); box-shadow: 0 12px 26px -22px rgba(70, 54, 130, .4); }
.notice-hours-caption { display: block; font-size: 12px; color: #7d748c; line-height: 1.6; }
.notice-season-row { display: flex; gap: 8px; margin-top: 10px; }
.guide-page .notice-season { flex: 1; margin: 0; padding: 7px 0; border-radius: 11px; background: #f5f1ff; color: #6f6685; font-size: 11.5px; line-height: 1.3; border: 1px solid transparent; }
.notice-season.on { background: linear-gradient(135deg, #6a5ae0, #8b78e6); color: #fff; }
.notice-hour-cards { display: flex; gap: 10px; margin-top: 12px; }
.notice-hour-card { flex: 1; min-width: 0; padding: 10px 12px; border-radius: 14px; background: #faf8ff; border: 1px solid rgba(139, 120, 230, .14); }
.notice-hour-label { display: block; font-size: 11px; color: #8a7fb0; }
.notice-hour-time { display: block; margin-top: 4px; font-size: 17px; font-weight: 700; color: #2a2438; font-variant-numeric: tabular-nums; }
.notice-hour-note { display: block; margin-top: 3px; font-size: 10px; color: #9a92ad; }
.notice-reminder { margin-top: 12px; padding: 10px 12px; border-radius: 12px; background: #f6f1ff; }
.notice-reminder text { font-size: 11.5px; line-height: 1.65; color: #6b5f86; }
.notice-article-section { margin-top: 22px; }
.notice-article-heading { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 700; color: #2a2438; line-height: 1.5; }
.notice-article-bar { flex: none; width: 3px; height: 15px; border-radius: 3px; background: linear-gradient(180deg, #8b78e6, #6a5ae0); }
.notice-article-text { display: block; margin-top: 8px; font-size: 13px; line-height: 1.85; color: #5f576f; }
.notice-article-note { margin-top: 24px; padding: 12px 14px; border-radius: 14px; background: rgba(139, 120, 230, .08); }
.notice-article-note text { font-size: 11px; line-height: 1.7; color: #7d748c; }
</style>
