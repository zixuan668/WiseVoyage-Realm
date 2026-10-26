import { ref, onMounted, onBeforeUnmount } from 'vue'

/** A warning is based on user activity, never reset by a heartbeat or animation. */
export function useStationIdle(options: {
  seconds: () => number
  active: () => boolean
  busy: () => boolean
  onExpire: () => void
}) {
  const remaining = ref<number | null>(null)
  let lastActivity = Date.now(),
    timer: ReturnType<typeof setInterval> | undefined
  function touch() {
    lastActivity = Date.now()
    remaining.value = null
  }
  function tick() {
    if (!options.active()) {
      touch()
      return
    }
    if (options.busy()) {
      lastActivity = Date.now()
      remaining.value = null
      return
    }
    const left = Math.max(0, Math.ceil(options.seconds() - (Date.now() - lastActivity) / 1000))
    remaining.value = left <= 20 ? left : null
    if (!left) {
      touch()
      options.onExpire()
    }
  }
  onMounted(() => {
    window.addEventListener('pointerdown', touch, { passive: true })
    window.addEventListener('keydown', touch)
    timer = setInterval(tick, 1000)
  })
  onBeforeUnmount(() => {
    if (timer) clearInterval(timer)
    window.removeEventListener('pointerdown', touch)
    window.removeEventListener('keydown', touch)
  })
  return { remaining, touch, tick }
}
