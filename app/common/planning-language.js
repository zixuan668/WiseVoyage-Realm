import { translateTour } from './tour-language.js'

// LZX's planner accepts Chinese intent keywords. Adapt its request only; the
// visitor's message and the server's route IDs/order/time remain unchanged.
const concepts = [
  ['history|historical|culture|cultural|architecture', '历史文化'],
  ['nature|natural|scenery|landscape', '自然风光'],
  ['photography|photos?|pictures?', '拍照'],
  ['family|children|kids?', '亲子孩子'],
]
const cities = { 'beijing':'北京', 'suzhou':'苏州', 'hangzhou':'杭州', 'guilin':'桂林',
  'zhangjiajie':'张家界', "xi'an":'西安', 'xian':'西安', 'shanghai':'上海', 'chengdu':'成都', 'chongqing':'重庆' }

export function planningMessage(value) {
  let message = String(value || '')
  for (const [words, chinese] of concepts) {
    message = message.replace(new RegExp("\\b(?:not interested in|don't want|do not want|without|avoid|no)\\s+(?:the\\s+)?(?:" + words + ')\\b', 'gi'), '不想' + chinese)
    message = message.replace(new RegExp('\\b(?:' + words + ')\\b', 'gi'), chinese)
  }
  message = message.replace(/\bhalf[ -]day\b/gi, '半天').replace(/\b(?:full[ -]day|one day|all day)\b/gi, '一天')
    .replace(/\b(\d+(?:\.\d+)?)[\s-]*(?:hours?|hrs?|h)\b/gi, '$1小时')
    .replace(/\b(\d+)\s*(?:minutes?|mins?|min)\b/gi, '$1分钟')
    .replace(/\b(?:relaxed|slow|less walking|fewer steps|avoid stairs|stroller|elderly)\b/gi, '轻松慢走少台阶')
    .replace(/\bsummer palace\b/gi, '北京颐和园')
    .replace(/\beast palace gate\b/gi, '东宫门').replace(/\bnorth palace gate\b/gi, '北宫门')
  for (const [english, chinese] of Object.entries(cities)) message = message.replace(new RegExp('\\b' + english + '\\b', 'gi'), chinese)
  return message
}

export function recommendationText(data, language) {
  if (language !== 'en') return data.ai_response || '已为您推荐景点'
  const names = (data.spot_names || []).map(name => translateTour(name, language))
  const minutes = data.estimated_time_minutes ?? data.total_duration
  if (!names.length) return translateTour('已为您推荐景点', language)
  return translateTour('推荐路线：{spots}。预计{minutes}分钟。', language,
    { spots:names.join(' → '), minutes:minutes == null ? '—' : minutes })
}

export function questionLanguage(message, appLanguage) {
  if (appLanguage === 'en') return 'en'
  if (/^\s*(?:please\s+)?(?:where|what|when|why|how|who|which|can|could|would|is|are|do|does|tell|explain|describe|compare|summari[sz]e|give)\b/i.test(message)) return 'en'
  return /[a-z]{2}/i.test(message) && !/[\u3400-\u9fff]/.test(message) ? 'en' : 'zh'
}

export function photoIdentificationText(result, language) {
  if(result.status!=='candidate'||!Number.isInteger(result.spot_id)||result.spot_id<=0)
    return translateTour('照片里没有匹配到已收录的景点，请补拍全景、标志建筑或名称标识，或手动选择景点继续提问。',language)
  let name=translateTour(result.spot_name||'景点',language)
  if(language==='en'&&/[\u3400-\u9fff]/.test(name))name='the candidate place'
  return translateTour('已识别为「{spot}」。',language,{spot:name})
}

export function findQuestionSpot(message, spots, selectedId) {
  const text = String(message).normalize('NFKC').toLowerCase()
  const matches = spots.flatMap(spot => [spot.spot_name, translateTour(spot.spot_name, 'en')]
    .filter(Boolean).filter(name => text.includes(name.normalize('NFKC').toLowerCase()))
    .map(name => ({spot,length:name.length})))
  matches.sort((a,b) => b.length-a.length)
  return matches[0]?.spot || spots.find(spot => spot.spot_id === selectedId) || null
}
