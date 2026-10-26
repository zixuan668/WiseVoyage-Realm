// WebKit can suspend SDK audio until a gesture reaches the render-layer window.
const CONTROLLER_KEY = '__zhiyouAvatarAudioController'

export function createAvatarAudioController(runtimeWindow, runtimeDocument, onBlocked, options = {}) {
  let manager = runtimeWindow[CONTROLLER_KEY]
  if (!manager) {
    const contexts = new Set(), subscribers = new Set(), originals = new Map()
    const streams = new Map(), destinations = new Map(), nodeMethods = []
    const removeStream = audio => {
      const relay = streams.get(audio)
      if (!relay) return
      streams.delete(audio); destinations.delete(audio.destination)
      for (const name of ['play', 'playing', 'pause', 'error']) relay.element.removeEventListener(name, report)
      relay.element.pause(); relay.element.srcObject = null; relay.element.remove()
      relay.node.disconnect()
      for (const track of relay.node.stream.getTracks()) track.stop()
    }
    const report = () => {
      for (const audio of contexts) if (audio.state === 'closed') { contexts.delete(audio); removeStream(audio) }
      const blocked = [...contexts].some(audio => audio.state === 'suspended' || audio.state === 'interrupted') ||
        [...streams.values()].some(relay => relay.element.paused || !!relay.element.error)
      for (const notify of subscribers) notify(blocked)
    }
    const unlock = () => {
      try {
        const session = runtimeWindow.navigator && runtimeWindow.navigator.audioSession
        if (session && session.type !== 'playback') session.type = 'playback'
      } catch (_) { /* Older WebKit has no writable audio session. */ }
      const pending = []
      for (const audio of contexts) {
        if (audio.state !== 'suspended' && audio.state !== 'interrupted') continue
        try { pending.push(Promise.resolve(audio.resume())) } catch (_) { /* Report the blocked state below. */ }
      }
      for (const { element } of streams.values()) {
        if (!element.paused && !element.error) continue
        try { pending.push(Promise.resolve(element.play())) } catch (_) { /* Keep the enable-sound control available. */ }
      }
      return Promise.allSettled(pending).then(report)
    }
    if (options.streamOutput) {
      const proto = runtimeWindow.AudioNode && runtimeWindow.AudioNode.prototype
      if (!proto) throw new Error('当前系统不支持实时声音输出')
      // Redirect only the tracked SDK contexts' final output. Internal audio
      // connections and all contexts outside this controller retain their route.
      for (const key of ['connect', 'disconnect']) {
        const original = proto[key]
        const wrapped = function(...args) {
          const destination = destinations.get(args[0]), requested = args[0]
          if (destination) args[0] = destination
          const result = original.apply(this, args)
          return destination && key === 'connect' ? requested : result
        }
        proto[key] = wrapped
        nodeMethods.push({ proto, key, original, wrapped })
      }
    }
    const streamOutput = audio => {
      if (!options.streamOutput) return
      if (typeof audio.createMediaStreamDestination !== 'function') throw new Error('当前系统不支持实时声音输出')
      const node = audio.createMediaStreamDestination(), element = runtimeDocument.createElement('audio')
      streams.set(audio, { node, element })
      element.muted = false; element.volume = 1; element.playsInline = true
      element.setAttribute('playsinline', ''); element.setAttribute('aria-hidden', 'true')
      element.style.display = 'none'
      for (const name of ['play', 'playing', 'pause', 'error']) element.addEventListener(name, report)
      element.srcObject = node.stream
      runtimeDocument.body.appendChild(element)
      destinations.set(audio.destination, node)
    }
    const wrappers = new Map()
    for (const key of ['AudioContext', 'webkitAudioContext']) {
      const Original = runtimeWindow[key]
      if (typeof Original !== 'function') continue
      let Wrapped = wrappers.get(Original)
      if (!Wrapped) {
        Wrapped = new Proxy(Original, { construct(Target, args, NewTarget) {
          const audio = Reflect.construct(Target, args, NewTarget)
          contexts.add(audio)
          try { streamOutput(audio) } catch (error) {
            contexts.delete(audio); removeStream(audio)
            if (audio.close) Promise.resolve(audio.close()).catch(() => {})
            throw error
          }
          if (audio.addEventListener) audio.addEventListener('statechange', report)
          report()
          return audio
        } })
        wrappers.set(Original, Wrapped)
      }
      try { runtimeWindow[key] = Wrapped; originals.set(key, { Original, Wrapped }) } catch (_) {}
    }
    const gestures = ['touchend', 'click', 'keydown']
    if (runtimeDocument.addEventListener) for (const event of gestures) runtimeDocument.addEventListener(event, unlock, true)
    manager = { contexts, subscribers, unlock, report, destroy() {
      if (runtimeDocument.removeEventListener) for (const event of gestures) runtimeDocument.removeEventListener(event, unlock, true)
      for (const [key, { Original, Wrapped }] of originals) if (runtimeWindow[key] === Wrapped) runtimeWindow[key] = Original
      for (const audio of contexts) if (audio.removeEventListener) audio.removeEventListener('statechange', report)
      for (const audio of [...streams.keys()]) removeStream(audio)
      for (const { proto, key, original, wrapped } of nodeMethods) if (proto[key] === wrapped) proto[key] = original
      contexts.clear()
      delete runtimeWindow[CONTROLLER_KEY]
    } }
    runtimeWindow[CONTROLLER_KEY] = manager
  }
  const notify = typeof onBlocked === 'function' ? onBlocked : () => {}
  manager.subscribers.add(notify)
  manager.report()
  let released = false
  return { unlock: manager.unlock, describe() {
    return {
      contexts: [...manager.contexts].map(audio => ({ state: audio.state, sampleRate: audio.sampleRate, time: audio.currentTime })),
      session: runtimeWindow.navigator && runtimeWindow.navigator.audioSession && runtimeWindow.navigator.audioSession.type,
      media: runtimeDocument.querySelectorAll ? [...runtimeDocument.querySelectorAll('audio')].map(audio => ({ paused: audio.paused, muted: audio.muted, volume: audio.volume, readyState: audio.readyState, error: audio.error && audio.error.code })) : [],
    }
  }, release() {
    if (released) return
    released = true
    manager.subscribers.delete(notify)
    if (!manager.subscribers.size) manager.destroy()
  } }
}

export function prepareNativeGuideAudio(runtime) {
  if (!runtime || !runtime.os || runtime.os.name !== 'iOS' || !runtime.ios) return
  try {
    const session = runtime.ios.importClass('AVAudioSession').sharedInstance()
    runtime.ios.invoke(session, 'setCategory:error:', 'AVAudioSessionCategoryPlayback', null)
    runtime.ios.invoke(session, 'setActive:error:', true, null)
    console.log('[guide-audio] native', JSON.stringify({ category: runtime.ios.invoke(session, 'category'), volume: runtime.ios.invoke(session, 'outputVolume') }))
  } catch (error) { console.warn('[guide-audio] Cannot activate iOS playback:', error.message) }
}
