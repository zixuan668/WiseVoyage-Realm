const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const source = (file) => fs.readFileSync(require('node:path').join(__dirname, '..', file), 'utf8')
function planner(request) {
  const script = source('components/WanderPlanner.vue').match(/<script>([\s\S]*?)<\/script>/)[1]
  const options = vm.runInNewContext(script.replace(/^import .*$/gm,'').replace('export default','globalThis.component=')+';component', {
    WanderIcon:{}, RouteRoadMap:{}, PageDock:{}, assetUrl:x=>x, walkingDistance(){},
    previewOptions:(ids,plan)=>({...plan,spot_ids:ids}), routeRequest:request,
  })
  const state = {...options.data(),$emit(){},spots:[{spot_id:1},{spot_id:2}],guides:[]}
  for (const [key,method] of Object.entries(options.methods)) state[key]=method.bind(state)
  for (const [key,getter] of Object.entries(options.computed)) Object.defineProperty(state,key,{get:()=>getter.call(state)})
  return state
}

test('cancelling planning aborts the request and discards a late result', async () => {
  let complete, aborted=0
  const state=planner(()=>({ promise:new Promise(resolve=>{complete=resolve}), abort(){aborted++} }))
  state.stage='time'
  const pending=state.generate()
  assert.equal(state.stage,'time')
  assert.equal(state.arranging,true)
  assert.equal(state.back(),true)
  assert.equal(state.arranging,false)
  complete({spot_ids:[1]})
  await pending
  assert.equal(aborted,1)
  assert.equal(state.stage,'time')
  assert.equal(state.overview,null)
})

test('cancelling during location lookup prevents a late recommendation request', async () => {
  let locate, recommendations=0
  const state=planner(()=>{ recommendations++ })
  state.locationEntry=()=>new Promise(resolve=>{locate=resolve})
  state.stage='time'
  const pending=state.chooseTime(30)
  assert.equal(state.stage,'time')
  assert.equal(state.arranging,true)
  assert.equal(state.back(),true)
  assert.equal(state.arranging,false)
  locate(2)
  await pending
  assert.equal(recommendations,0)
  assert.equal(state.entry,1)
  assert.equal(state.stage,'time')
})

test('blind map keeps the walked approach and omits the destination, downstream route and markers', () => {
  const { blindPreviewMap }=vm.runInNewContext(source('common/wander.js').replace(/^export /gm,'')+';({blindPreviewMap})')
  const point=latitude=>({latitude,longitude:116.27})
  const entry=point(39.993), stop=point(39.996), destination=point(40), exit=point(40.001)
  const overview={entry_leg:{},legs:[{}],exit_leg:{},stops:[{},{}]}
  const full={polyline:[{points:[entry,stop]},{points:[stop,destination]},{points:[destination,exit]}],
    legIndexes:[0,1,2],markers:[{...entry,id:1001},{...stop,id:1},{...destination,id:2},{...exit,id:1002}]}
  const preview=blindPreviewMap(full,overview)
  assert.deepEqual([...preview.markers.map(marker=>marker.id)],[1001,1])
  assert.equal(preview.polyline.length,2)
  assert.ok(preview.points.every(p=>p.latitude<destination.latitude))
  assert.deepEqual([...preview.legIndexes],[0,1])
})

test('Wander map stops and access points are anonymous, with public gates and visit times still available', () => {
  const { routeMapLabels }=vm.runInNewContext(source('common/route-planning.js').replace(/^import .*$/gm,'').replace(/^export /gm,'')+';({routeMapLabels})')
  const overview={entry_anchor:{label:'东宫门'},exit_anchor:{label:'北宫门'},stops:[{
    spot_name:'仁寿殿', access_label:'仁寿殿东侧入口', access_latitude:39.99, access_longitude:116.27, visit_minutes:15,
  }]}
  const t=(value,params={})=>value.replace(/\{(\w+)\}/g,(_,key)=>params[key])
  const labels=routeMapLabels(overview,t,{hideSpotNames:true})
  assert.equal(labels[1].name,'第 1 站')
  assert.deepEqual([...labels[1].lines],['步行接入点','预计停留 15 分钟'])
  assert.equal(labels[1001],'东宫门')
  assert.equal(labels[1002],'北宫门')
  assert.equal(routeMapLabels(overview,t,{hideSpotNames:true,hideExit:true})[1002],undefined)
  assert.equal(routeMapLabels(overview,t)[1].name,'仁寿殿')
})
