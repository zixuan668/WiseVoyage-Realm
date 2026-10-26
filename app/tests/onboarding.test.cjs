const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const root = path.resolve(__dirname, '..')

function harness(file, initial = {}, route = '') {
  const storage = { ...initial }, navigation = [], toasts = [], timers = [], requests = []
  const context = { console, LOGIN_PROVIDER: 'password', LANGUAGE_STORAGE_KEY: 'language', AuthPage: {}, BrandLogo: {},
    APP_LOGIN: true, DEVELOPMENT_LOGIN: false, BASE_URL: '/api/v1', translateTour: value => value,
    setTimeout: (fn, delay) => { const timer = { fn, delay, cancelled: false }; timers.push(timer); return timer },
    clearTimeout: timer => { if (timer) timer.cancelled = true },
    getCurrentPages: () => route ? [{ route }] : [],
    uni: {
      getStorageSync: key => storage[key],
      setStorageSync: (key, value) => { storage[key] = value },
      reLaunch: options => navigation.push(options),
      showToast: options => toasts.push(options),
      request: options => requests.push(options),
      getSystemInfoSync: () => ({ windowWidth: 375, windowHeight: 812 }),
      createSelectorQuery: () => {
        const query = { in: () => query, select: () => query,
          boundingClientRect: callback => { query.callback = callback; return query },
          exec: () => query.callback({ left: 40, top: 700, width: 300, height: 48 }),
        }
        return query
      },
    },
  }
  vm.createContext(context)
  const helpers = fs.readFileSync(path.join(root, 'common/onboarding.js'), 'utf8').replace(/export /g, '')
  vm.runInContext(helpers, context)
  vm.runInContext(fs.readFileSync(path.join(root, 'common/station-claim.js'), 'utf8').replace(/export /g, ''), context)
  const script = fs.readFileSync(path.join(root, file), 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
  vm.runInContext(script.replace(/^import .*$/gm, '').replace('export default', 'globalThis.options ='), context)
  const options = context.options
  const state = options.data ? options.data() : {}
  for (const [key, fn] of Object.entries(options.methods || {})) state[key] = fn.bind(state)
  for (const [key, fn] of Object.entries(options.computed || {})) Object.defineProperty(state, key, { get: () => fn.call(state) })
  return { context, options, state, storage, navigation, toasts, timers, requests }
}

test('first launch is visible before authentication, including resumed old routes', () => {
  const first = harness('App.vue', {}, 'pages/auth/auth')
  first.options.onShow.call(first.state)
  assert.equal(first.navigation[0].url, '/pages/onboarding/onboarding')
  for (const route of ['', 'pages/onboarding/onboarding']) {
    const intro = harness('App.vue', {}, route)
    intro.options.onShow.call(intro.state)
    assert.equal(intro.navigation.length, 0, 'do not relaunch the default first page twice')
  }
})

test('indicator follows both directions during the actual swipe and settles to the selected page', () => {
  const h = harness('pages/onboarding/onboarding.vue')
  h.options.onLoad.call(h.state)
  h.state.onTouchStart()
  h.state.onTransition({ detail: { dx: 187.5 } })
  assert.equal(h.state.progress, .5)
  assert.match(h.state.indicatorStyle.transform, /translate3d\(11.5px/)
  h.state.onTouchEnd()
  h.state.onChange({ detail: { current: 1 } })
  assert.equal(h.state.current, 1)
  assert.equal(h.state.progress, 1)
  h.state.onAnimationFinish({ detail: { current: 1 } })
  h.state.onTouchStart()
  h.state.onTransition({ detail: { dx: -187.5 } })
  assert.equal(h.state.progress, .5)
  h.state.onTouchEnd()
  h.state.onAnimationFinish({ detail: { current: 0 } })
  assert.equal(h.state.progress, 0)
  assert.equal(Object.keys(h.storage).length, 0)
  h.state.selectSlide(2)
  assert.equal(h.state.current, 2)
  assert.equal(h.state.progress, 2)
  assert.equal(h.navigation.length, 0)
})

test('holding shrinks the rounded button, releasing dissolves it into dots, then sign-in', () => {
  const h = harness('pages/onboarding/onboarding.vue', { token: 'existing', login_provider: 'password' })
  h.state.holdStart()
  assert.equal(h.state.pressing, true, 'the button shrinks while the finger is down')
  assert.equal(h.state.bursting, false, 'nothing scatters before the finger is lifted')
  assert.equal(h.state.leaving, false)
  h.state.holdEnd()
  assert.equal(h.storage['zhiyou.onboarding.v1.completed'], true)
  assert.equal(h.state.pressing, false)
  assert.equal(h.state.bursting, true)
  assert.equal(h.state.particles.length, 72, '18 x 4 dots cover the label box, not the whole pill')
  const sizes = new Set(h.state.particles.map(p => p.style.width))
  assert.ok(sizes.size > 8, 'the dots run from small grains to a few larger beads')
  const colors = new Set(h.state.particles.map(p => p.style.backgroundColor))
  assert.equal(colors.size, 5, 'purple, light purple and pale purple dots')
  assert.equal(h.state.originX, 190)
  assert.equal(h.state.originY, 724)
  assert.equal(h.state.showLogin, false, 'sign-in appears only after the dots are released')
  h.state.holdStart()
  h.state.finish(true)
  assert.equal(h.timers.length, 2, 'the synthesized tap after touchend cannot start a second run')
  h.timers.find(t => t.delay === 320).fn()
  assert.equal(h.state.showLogin, true)
  h.timers.find(t => t.delay === 1350).fn()
  assert.equal(h.navigation.length, 1)
  assert.equal(h.navigation[0].url, '/pages/auth/auth?fromOnboarding=1')
  assert.equal(h.storage.token, 'existing')
})

test('click fallback presses briefly, then releases into the dots', () => {
  const h = harness('pages/onboarding/onboarding.vue')
  h.state.finish(true)
  assert.equal(h.state.pressing, true)
  assert.equal(h.state.bursting, false)
  h.timers.find(t => t.delay === 180).fn()
  assert.equal(h.state.pressing, false)
  assert.equal(h.state.bursting, true)
  assert.equal(h.state.particles.length, 72)
  assert.equal(h.state.leaving, true)
})

test('the welcome page switches between Chinese and English copy in place', () => {
  const h = harness('pages/onboarding/onboarding.vue')
  h.options.onLoad.call(h.state)
  assert.equal(h.state.english, false)
  assert.equal(h.state.slides[0].title, '想去哪里\n就从这里出发')
  h.state.setLanguage('en')
  assert.equal(h.state.english, true)
  assert.equal(h.storage.language, 'en')
  assert.equal(h.state.slides[0].title, 'Your places.\nYour own journey.')
  h.state.setLanguage('zh')
  assert.equal(h.state.english, false)
  assert.equal(h.storage.language, 'zh')
  assert.equal(h.state.slides[2].title, '旅途有疑问\n随时问小导游')
  h.state.toggleLanguage()
  assert.equal(h.state.english, true)
  assert.equal(h.storage.language, 'en')
  assert.equal(h.state.slides[0].title, 'Your places.\nYour own journey.')
  h.state.toggleLanguage()
  assert.equal(h.state.english, false)
  assert.equal(h.storage.language, 'zh')
  assert.equal(h.state.slides[0].title, '想去哪里\n就从这里出发')
})

test('skip lifts away and reveals sign-in from the skip button', () => {
  const h = harness('pages/onboarding/onboarding.vue')
  h.state.skipIntro()
  assert.equal(h.storage['zhiyou.onboarding.v1.completed'], true)
  assert.equal(h.state.leaving, true)
  assert.equal(h.state.skipping, true)
  assert.equal(h.state.originX, 190)
  assert.equal(h.state.originY, 724)
  assert.equal(h.state.showLogin, false)
  assert.equal(h.state.bursting, false, 'skip does not burst the call to action')
  h.state.skipIntro()
  assert.equal(h.timers.length, 2, 'ignore repeated taps while the transition is running')
  h.timers.find(t => t.delay === 70).fn()
  assert.equal(h.state.showLogin, true)
  h.timers.find(t => t.delay === 980).fn()
  assert.equal(h.navigation.length, 1)
  assert.equal(h.navigation[0].url, '/pages/auth/auth?fromOnboarding=1')
})

test('skip and subsequent launches preserve signed-in accounts and choose the correct entry', () => {
  const account = { token: 'existing', login_provider: 'password' }
  const h = harness('pages/onboarding/onboarding.vue', account)
  h.state.finish(false)
  assert.equal(h.navigation[0].url, '/pages/auth/auth?fromOnboarding=1')
  assert.equal(h.storage.token, 'existing')
  const reopened = harness('pages/onboarding/onboarding.vue', h.storage)
  reopened.options.onLoad.call(reopened.state)
  assert.equal(reopened.navigation[0].url, '/pages/tabs/tabs?tab=tour')
  const oldProvider = harness('pages/onboarding/onboarding.vue', { ...account, login_provider: 'legacy-login' })
  oldProvider.state.finish(false)
  assert.equal(oldProvider.navigation[0].url, '/pages/auth/auth?fromOnboarding=1')
})

test('onboarding explicitly opens sign-in without automatically restoring a saved account', () => {
  const h = harness('pages/auth/auth.vue', { token: 'existing', login_provider: 'password' })
  h.options.onLoad.call(h.state, { fromOnboarding: '1' })
  assert.equal(h.requests.length, 0)
  assert.equal(h.navigation.length, 0)
  h.options.onLoad.call(h.state, {})
  assert.equal(h.requests[0].url, '/api/v1/user/me')
})

test('unloading during the animation cancels pending reveal and navigation', () => {
  const h = harness('pages/onboarding/onboarding.vue')
  h.state.finish(true)
  h.options.onUnload.call(h.state)
  assert.ok(h.timers.every(timer => timer.cancelled))
})

test('storage failures stay on the introduction; navigation failures allow retry', () => {
  const h = harness('pages/onboarding/onboarding.vue')
  h.context.uni.setStorageSync = () => { throw new Error('storage full') }
  h.state.finish(false)
  assert.equal(h.navigation.length, 0)
  assert.equal(h.state.leaving, false)
  assert.equal(h.toasts.length, 1)
  const retry = harness('pages/onboarding/onboarding.vue')
  retry.state.finish(false)
  retry.navigation[0].fail()
  assert.equal(retry.state.leaving, false)
  retry.state.finish(false)
  assert.equal(retry.navigation.length, 2)
})
