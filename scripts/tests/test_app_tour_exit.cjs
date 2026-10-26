const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const path = require('node:path')
const root = path.resolve(__dirname, '../..')
async function main() {
  const events = [], container = { innerHTML: 'avatar' }
  let finishDestroy
  const runtime = fs.readFileSync(path.join(root, 'app/components/tour-xingyun.vue'), 'utf8').match(/<script module="runtime" lang="renderjs">([\s\S]*?)<\/script>/)[1]
  const context = vm.createContext({ Promise, loadXingyunSdk:async()=>{}, setTimeout, clearTimeout, document: { getElementById: () => container } })
  vm.runInContext(runtime.replace(/^import .*$/gm,'').replace('export default', 'globalThis.component=') + '\navatar={destroy:()=>new Promise(resolve=>globalThis.finishDestroy=resolve)}', context)
  const closing = context.component.methods.apply({ command: 'close', id: 7 }, null, { callMethod: (_, e) => events.push(e) })
  assert.equal(events.length, 0, 'must wait for SDK destruction')
  await Promise.resolve()
  context.finishDestroy()
  await closing
  assert.equal(container.innerHTML, '')
  assert.equal(events[0].state, 'closed')
  assert.equal(events[0].id, 7)

  // A delayed error from the old SDK must never destroy the new connection.
  const instances = []
  context.window = { XmovAvatar: class {
    constructor(options) { this.options = options; this.destroyed = false; instances.push(this) }
    init() { return Promise.resolve() }
    destroy() { this.destroyed = true; return Promise.resolve() }
  } }
  const owner = { callMethod: () => {} }
  await context.component.methods.apply({ gateway: 'first', command: 'connect' }, null, owner)
  await context.component.methods.apply({ gateway: 'second', command: 'connect' }, null, owner)
  instances[0].options.onMessage({ code: 500, message: 'old connection closed' })
  assert.equal(instances[1].destroyed, false)
  await context.component.methods.apply({ command: 'close', id: 8 }, null, owner)

  const source = fs.readFileSync(path.join(root, 'app/pages/tour/tour.vue'), 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
  const navigations = [], notices = []
  const pageContext = vm.createContext({ Promise, setTimeout, clearTimeout, uni: { reLaunch: o => navigations.push(o.url), showToast: o => notices.push(o.title) }, TourXingyun: {}, TourXfyun: {}, NocturneConfirm: {}, RouteOverview: {}, TourRouteRepair: {} })
  vm.runInContext(source.replace(/^import .*$/gm, '').replace('export default', 'globalThis.page='), pageContext)
  const page = { t:x=>x, ...pageContext.page.data(), ...pageContext.page.methods, sid: 12, appXingyun: true, guideProvider: 'xingyun', cancelRecord() {}, stopPlayback() {}, stopGps() {}, $nextTick: () => Promise.resolve() }
  page.leaveTour()
  assert.equal(navigations.length, 1, 'exit must not wait for SDK close acknowledgment')
  assert.equal(page.leavingTour, true)
  page.leaveTour()
  page.onXingyunState({ state: 'closed', id: page._xingyunCloseId })
  assert.deepEqual(navigations, ['/pages/tabs/tabs?tab=tour'])
  page.leavingTour = false
  vm.runInContext('api.endSession=()=>Promise.resolve({data:{success:false,message:"结束失败"}})', pageContext)
  await page.endTour()
  assert.equal(navigations.length, 1, 'failed end must keep the tour open for retry')
  assert.equal(page.endingTour, false)
  assert.deepEqual(notices, ['结束导览保存失败，请重试'])
  vm.runInContext('api.endSession=()=>Promise.resolve({data:{success:true}})', pageContext)
  await page.endTour()
  assert.equal(navigations[1], '/pages/tour-summary/tour-summary?sessionId=12')
  let releaseOld
  page._xingyunClosePromise = new Promise(resolve => { releaseOld = resolve })
  page.tourVisible = true
  page.xingyunActive = false
  page.guideId = 1
  let configRequests = 0
  pageContext.request = () => { configRequests++; return Promise.resolve({data:{configured:false}}) }
  const reconnect = page.connectXingyun()
  assert.equal(configRequests, 0, 'reconnect must wait for previous SDK cleanup')
  page.tourVisible = false
  releaseOld()
  await reconnect
  assert.equal(configRequests, 0, 'hidden page must not reconnect after cleanup')
  console.log('PASS: SDK cleanup, stale callbacks, immediate home navigation, duplicate exit guard, end failure')
}
main().catch(e => { console.error(e); process.exitCode = 1 })
