// Intrinsic canvas long edges, independent of WebView DPR and CSS display size.
// Preserve the decoded source by default; never invent pixels for a smaller source.
export const AVATAR_QUALITY_STEPS = [1920, 1280, 960]
const sourceSizes = new WeakMap()

export function rightSizeAvatarCanvas(canvas, options = {}) {
  if (!canvas || !(canvas.width > 0) || !(canvas.height > 0)) return false
  const rect = typeof canvas.getBoundingClientRect === 'function' ? canvas.getBoundingClientRect() : null
  if (!rect || !(rect.width > 0) || !(rect.height > 0)) return false
  let source = sourceSizes.get(canvas)
  if (!source) {
    source = { width: canvas.width, height: canvas.height }
    sourceSizes.set(canvas, source)
  }
  const requested = Number(options.maxLongEdge)
  const limit = Math.max(AVATAR_QUALITY_STEPS[AVATAR_QUALITY_STEPS.length - 1],
    Number.isFinite(requested) && requested > 0 ? requested : AVATAR_QUALITY_STEPS[0])
  const scale = Math.min(1, limit / Math.max(source.width, source.height))
  const even = value => Math.max(2, Math.round(value / 2) * 2)
  const width = scale === 1 ? source.width : even(source.width * scale)
  const height = scale === 1 ? source.height : even(source.height * scale)
  if (canvas.width === width && canvas.height === height) return false
  canvas.width = width
  canvas.height = height
  return true
}

// Sample at most once a second. Wall-clock streaks, startup grace and cooldown
// prevent bursty SDK callbacks or page suspension from exhausting quality levels.
export function createAvatarQualityController() {
  let step = 0, startedAt = 0, lastChangeAt = null, lastSampleAt = null
  let lowSince = null, highSince = null
  const clearStreaks = () => { lowSince = null; highSince = null }
  const controller = {
    get step() { return step },
    reset(now = Date.now()) {
      step = 0; startedAt = now; lastChangeAt = null; lastSampleAt = null
      clearStreaks()
    },
    sample(stats, now = Date.now()) {
      if (lastSampleAt !== null && now - lastSampleAt >= 0 && now - lastSampleAt < 1000) return step
      if (lastSampleAt !== null && (now - lastSampleAt > 3000 || now < lastSampleAt)) clearStreaks()
      lastSampleAt = now
      const fps = Number(stats && stats.current)
      if (!Number.isFinite(fps) || fps <= 0 || now - startedAt < 10000 ||
          (lastChangeAt !== null && now - lastChangeAt < 15000)) {
        clearStreaks()
        return step
      }
      if (fps < 18 && step < AVATAR_QUALITY_STEPS.length - 1) {
        highSince = null
        if (lowSince === null) lowSince = now
        if (now - lowSince >= 8000) {
          step++; lastChangeAt = now; clearStreaks()
        }
      } else if (fps >= 23 && step > 0) {
        lowSince = null
        if (highSince === null) highSince = now
        if (now - highSince >= 20000) {
          step--; lastChangeAt = now; clearStreaks()
        }
      } else clearStreaks()
      return step
    },
  }
  controller.reset()
  return controller
}
