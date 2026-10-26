// 导览中与数字人的问答也记入「AI 小导游」的问答历史（右上角时钟图标）。
// 记录按账号隔离，和 AI 小导游共用 ai_chat_state:<账号> 存储。
const STATE_PREFIX = 'ai_chat_state:'
const MAX_MESSAGES = 200

function historyOwner() {
  var id = ''
  var name = ''
  try { id = uni.getStorageSync('user_id') } catch (e) { id = '' }
  try { name = uni.getStorageSync('username') } catch (e) { name = '' }
  if (id) return 'id:' + id
  if (name) return 'name:' + name
  return 'guest'
}

function readState(key) {
  try {
    var raw = uni.getStorageSync(key)
    if (!raw) return {}
    var state = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (!state || typeof state !== 'object' || Array.isArray(state)) return {}
    return state
  } catch (e) {
    return {}
  }
}

// role: 'user' 表示游客提问，'guide' / 'ai' 表示数字人回答。
export function appendTourChatMessage(role, content) {
  var text = content == null ? '' : String(content).trim()
  if (!text) return
  var key = STATE_PREFIX + encodeURIComponent(historyOwner())
  var state = readState(key)
  var list = Array.isArray(state.messages) ? state.messages.slice() : []
  list.push({ role: role === 'guide' || role === 'ai' ? 'ai' : 'user', content: text, source: 'tour' })
  state.messages = list.slice(-MAX_MESSAGES)
  try { uni.setStorageSync(key, JSON.stringify(state)) } catch (e) {}
}
