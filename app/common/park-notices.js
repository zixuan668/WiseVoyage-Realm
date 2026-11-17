// 官方通知正文：整理自颐和园官网公开信息（核对日期见 NOTICE_CHECKED_ON）。
// 参考 frontend/src/data/parkVisitorInfo.ts 与 StationVisitorInfo 的已发布文案。
// 本模块只提供应用内展示内容，不包含外部跳转；临时安排以门区当日公告为准。

export const NOTICE_CHECKED_ON = '2026-10-18'

export const noticeArticles = [
  {
    id: 'announcements',
    icon: 'bell',
    badge: { zh: '官网', en: 'Official' },
    category: { zh: '景区公告', en: 'Park notices' },
    title: { zh: '颐和园景区公告', en: 'Summer Palace park notices' },
    summary: { zh: '入园、园中园开放与现场求助的官网公告要点。', en: 'Official points on entry, inner-garden access and on-site help.' },
    sections: [
      {
        heading: { zh: '入园与安检', en: 'Entry and security checks' },
        paragraphs: [
          {
            zh: '入园请携带有效证件并配合安检。客流高峰或大型活动期间，园区可能采取临时限流、单向通行等措施，请听从现场工作人员引导。',
            en: 'Bring valid identification and cooperate with security checks. During peak periods or large events the park may limit entry or set one-way routes; please follow on-site staff.',
          },
        ],
      },
      {
        heading: { zh: '园中园开放', en: 'Inner gardens' },
        paragraphs: [
          {
            zh: '佛香阁、德和园、苏州街及颐和园博物馆周一闭园，重点节假日除外。园中园停止进入时间早于公园闭园时间，请预留足够的游览时间。',
            en: 'The Tower of Buddhist Incense, Garden of Virtue and Harmony, Suzhou Street and the Summer Palace Museum close on Mondays except major holidays. Inner gardens stop admitting visitors before the park closes, so plan enough time.',
          },
        ],
      },
      {
        heading: { zh: '咨询与求助', en: 'Help on site' },
        paragraphs: [
          {
            zh: '如需帮助，可向附近工作人员咨询。与同行人走散、物品遗失或身体不适时，请停留在安全区域，并说明最近的景点或地标。',
            en: 'Ask nearby staff whenever you need help. If you are separated from your group, lose something or feel unwell, stay in a safe place and describe your nearest attraction or landmark.',
          },
        ],
      },
    ],
    note: { zh: '临时开放与通行安排，请以门区当日公告和现场工作人员说明为准。', en: 'Temporary openings and access changes follow the day’s entrance notices and on-site staff instructions.' },
  },
  {
    id: 'visit',
    icon: 'clock',
    badge: { zh: '官网', en: 'Official' },
    category: { zh: '游览指南', en: 'Visit guide' },
    title: { zh: '游览提示及开放时间', en: 'Visitor tips and opening hours' },
    summary: { zh: '开放时间、园中园安排与游园安全提示。', en: 'Opening hours, inner-garden access and visitor safety tips.' },
    hours: {
      caption: { zh: '公园与园中园开放时间随季节调整。', en: 'Park and inner-garden hours change with the season.' },
      seasons: [
        {
          key: 'peak',
          label: { zh: '旺季 · 4月—10月', en: 'Apr–Oct' },
          rows: [
            { label: { zh: '公园', en: 'Park' }, time: '06:00 — 20:00', note: { zh: '19:00 停止入园', en: 'Last entry 19:00' } },
            { label: { zh: '园中园', en: 'Inner gardens' }, time: '08:00 — 18:00', note: { zh: '17:30 停止进入', en: 'Last entry 17:30' } },
          ],
        },
        {
          key: 'quiet',
          label: { zh: '淡季 · 11月—次年3月', en: 'Nov–Mar' },
          rows: [
            { label: { zh: '公园', en: 'Park' }, time: '06:30 — 19:00', note: { zh: '18:00 停止入园', en: 'Last entry 18:00' } },
            { label: { zh: '园中园', en: 'Inner gardens' }, time: '08:30 — 17:00', note: { zh: '16:30 停止进入', en: 'Last entry 16:30' } },
          ],
        },
      ],
      reminder: { zh: '佛香阁、德和园、苏州街及颐和园博物馆周一闭园，重点节假日除外。临时开放安排请看当日公告。', en: 'The Tower of Buddhist Incense, Garden of Virtue and Harmony, Suzhou Street and the Summer Palace Museum close on Mondays except major holidays. Check the day’s notices for temporary changes.' },
    },
    sections: [
      {
        heading: { zh: '购票与预约', en: 'Tickets and booking' },
        paragraphs: [
          {
            zh: '请通过官方渠道购票与预约，具体票种、价格与优惠政策以购票页面为准。',
            en: 'Buy tickets and book through official channels. Available ticket types, prices and concessions follow the booking page.',
          },
        ],
      },
      {
        heading: { zh: '游船提示', en: 'Boat trips' },
        paragraphs: [
          {
            zh: '先查看码头公告，按要求穿着救生衣。大风、降雨等天气可能影响运营，请以码头当日安排为准。',
            en: 'Check pier notices and wear a life jacket as instructed. Wind and rain can affect services; follow the pier’s arrangements for the day.',
          },
        ],
      },
      {
        heading: { zh: '步行与休息', en: 'Walking and rest breaks' },
        paragraphs: [
          {
            zh: '根据体力安排游程，适当补水和休息；湖岸、桥面及台阶处留意脚下，照看好同行儿童与长者。',
            en: 'Plan a walk that suits your energy, with water and rest breaks. Take care beside the lake, on bridges and on steps, and keep children and older companions close.',
          },
        ],
      },
    ],
    note: { zh: '开放时间与运营安排可能临时调整，请以当日公告为准。本页内容仅作参考。', en: 'Opening hours and services may change temporarily; follow the day’s notices. This page is for reference only.' },
  },
]
