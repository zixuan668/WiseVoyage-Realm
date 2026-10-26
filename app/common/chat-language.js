const accountCaches = new Map()
const inFlightCaches = new WeakMap()

export function getChatTranslationCache(owner) {
  if (accountCaches.has(owner)) return accountCaches.get(owner)
  const cache = new Map()
  cache.storageKey = 'chat_translations:v1:' + encodeURIComponent(owner)
  try {
    const raw = typeof uni !== 'undefined' && uni.getStorageSync(cache.storageKey)
    const entries = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (Array.isArray(entries)) for (const [text, pair] of entries.slice(-400)) {
      if (typeof text === 'string' && pair && typeof pair.zh === 'string' && typeof pair.en === 'string' && !/[\u3400-\u9fff]/.test(pair.en)) cache.set(text, pair)
    }
  } catch (_) {}
  accountCaches.set(owner, cache)
  return cache
}

function persistChatTranslations(cache) {
  if (!cache.storageKey || typeof uni === 'undefined') return
  while (cache.size > 400) cache.delete(cache.keys().next().value)
  try { uni.setStorageSync(cache.storageKey, JSON.stringify(Array.from(cache.entries()))) } catch (_) {}
}

export function warmChatTranslations(options) {
  // Latest visible messages take priority over older archived history.
  const lists = options.lists.map(list => list.slice().reverse())
  return Promise.all(['en', 'zh'].map(target => localizeChatMessages({ ...options, lists, target, applyText: false, concurrency: 2 })))
}

// Translate display copies only. Never send translated messages back as tour input.
export async function localizeChatMessages({ lists, field, target, cache, translate, isCurrent, applyText = true, concurrency = 1 }) {
  const groups = new Map()
  for (const message of new Set(lists.flat())) {
    const text = message && message[field]
    if (typeof text !== 'string' || !text.trim()) continue
    const source = message.translations || {}
    const hasChinese = /[\u3400-\u9fff]/.test(text)
    const language = hasChinese ? 'zh' : (message.lang || 'en')
    const original = source[language] || text
    const key = original
    const saved = cache.get(key) || { ...source, [language]: original }
    if (!saved[target] && (target === 'en' ? !/[\u3400-\u9fff]/.test(text) : language === 'zh')) continue
    if (!groups.has(key)) groups.set(key, { key, text: original, saved, messages: [] })
    groups.get(key).messages.push(message)
  }
  const apply = group => {
    for (const message of group.messages) {
      message.translations = { ...group.saved }
      if (!applyText) continue
      const changed = message[field] !== group.saved[target]
      message[field] = group.saved[target]
      message.lang = target
      if (changed && field === 'content' && message.segments) { message.segments = undefined; message.cursor = false }
    }
  }
  const pending = []
  for (const group of groups.values()) {
    if (!isCurrent()) return
    if (group.saved[target]) apply(group)
    else pending.push(group)
  }
  // The existing endpoint limits each quoted input to 4000 characters.
  // Split long replies before quoting so their ending cannot be truncated.
  if (!inFlightCaches.has(cache)) inFlightCaches.set(cache, new Map())
  const flights = inFlightCaches.get(cache), owned = [], waiting = []
  for (const group of pending) {
    const key = JSON.stringify([group.key, target])
    if (flights.has(key)) {
      const waitingForTranslation = flights.get(key).then(pair => {
        if (!isCurrent()) return
        if (pair) { group.saved = pair; apply(group); return }
        return localizeChatMessages({ lists: [group.messages], field, target, cache, translate, isCurrent, applyText, concurrency })
      })
      // Attach an error handler immediately while other owned batches are running.
      waitingForTranslation.catch(() => {})
      waiting.push(waitingForTranslation)
    } else {
      let resolve, reject
      const promise = new Promise((yes, no) => { resolve = yes; reject = no })
      promise.catch(() => {})
      group.flightKey = key; group.resolve = resolve; group.reject = reject
      group.promise = promise
      flights.set(key, promise); owned.push(group)
    }
  }
  const jobs = []
  for (const group of owned) {
    const chars = Array.from(group.text)
    group.parts = []
    for (let start = 0; start < chars.length; start += 1200) jobs.push({ group, index: group.parts.push('') - 1, text: chars.slice(start, start + 1200).join('') })
  }
  let next = 0
  const worker = async () => {
   while (next < jobs.length) {
    if (!isCurrent()) return
    const offset = next; next += 4
    const batch = jobs.slice(offset, offset + 4)
    // Quoting questions makes them translation data rather than new instructions.
    const values = await translate(batch.map(job => JSON.stringify(job.text)), target)
    if (!isCurrent()) return
    if (!Array.isArray(values) || values.length !== batch.length || values.some(value => typeof value !== 'string' || !value.trim() || (target === 'en' && /[\u3400-\u9fff]/.test(value)))) throw new Error('Invalid translation response')
    batch.forEach((job, index) => { job.group.parts[job.index] = values[index].trim() })
    for (const group of new Set(batch.map(job => job.group))) if (group.parts.every(Boolean)) {
      group.saved[target] = group.parts.join('\n')
      for (const text of Object.values(group.saved)) cache.set(text, group.saved)
      apply(group); group.resolve(group.saved)
      persistChatTranslations(cache)
    }
   }
  }
  try {
    await Promise.all(Array.from({ length: Math.min(concurrency, Math.ceil(jobs.length / 4)) }, worker))
    for (const group of owned) { if (flights.get(group.flightKey) === group.promise) flights.delete(group.flightKey); group.resolve(null) }
    await Promise.all(waiting)
  } catch (error) {
    for (const group of owned) group.reject(error)
    throw error
  } finally {
    for (const group of owned) if (flights.get(group.flightKey) === group.promise) flights.delete(group.flightKey)
  }
}
