const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..')
function component(file){
 const storage={user_id:17,token:'test'},toasts=[],calls=[],navigation=[]
 const c={getCurrentPages:()=>[{route:"pages/mine/history"},{route:"pages/tour-summary/tour-summary"}],console,Date,Promise,setTimeout,clearTimeout,setInterval,clearInterval,BASE_URL:'http://local/api/v1',LANGUAGE_STORAGE_KEY:'language',assetUrl:x=>x,isBeijingCity:()=>true,selectedOrder:(order,ids)=>order.filter(id=>ids[id]),previewOptions:ids=>({spot_ids:ids}),roadMap:()=>null,FloatingTourButton:{},RouteTiming:{},ScenicSheet:{},NocturneConfirm:{},TourXingyun:{},TourXfyun:{},RouteOverview:{},TourRouteRepair:{},PageDock:{},uni:{getStorageSync:k=>storage[k],setStorageSync:(k,v)=>{storage[k]=v},showToast:o=>toasts.push(o),getSystemInfoSync:()=>({}),request:o=>{calls.push(o)},reLaunch:o=>navigation.push(o),navigateTo:o=>navigation.push(o),navigateBack:()=>navigation.push({back:true})}}
 c.AuthPage={}
 vm.createContext(c)
 vm.runInContext(fs.readFileSync(path.join(root,'common/avatar-audio.js'),'utf8').replace(/export /g,''),c)
 vm.runInContext(fs.readFileSync(path.join(root,'common/chat-language.js'),'utf8').replace(/export /g,''),c)
 const source=fs.readFileSync(path.join(root,file),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
 vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.options='),c)
 const o=c.options,s={t:x=>x,$nextTick:fn=>fn?.()};Object.assign(s,o.data.call(s));for(const [k,f] of Object.entries(o.methods))s[k]=f.bind(s);for(const [k,f] of Object.entries(o.computed||{}))Object.defineProperty(s,k,{get:()=>f.call(s)})
 return{s,o,storage,toasts,calls,navigation,uni:c.uni}
}
function swipe(s, fromX, toX, endX, endY){
  s.onSpotTouchStart({touches:[{clientX:fromX,clientY:200}]})
  s.onSpotTouchMove({touches:[{clientX:toX,clientY:205}]})
  s.onSpotTouchEnd({changedTouches:[{clientX:endX,clientY:endY}]})
}
test('spot card swipe switches both directions',()=>{
  const {s}=component('pages/tour/tour.vue')
  s.spotCards=[{spot_id:51},{spot_id:52},{spot_id:53}];s.spotIdx=1
  swipe(s,320,120,120,205)
  assert.equal(s.spotIdx,2,'left swipe should go to next spot')
  swipe(s,120,320,320,205)
  assert.equal(s.spotIdx,1,'right swipe should go to previous spot')
})
test('swipe still works when touchend coordinates are missing or zero',()=>{
  const {s}=component('pages/tour/tour.vue')
  s.spotCards=[{spot_id:51},{spot_id:52},{spot_id:53}];s.spotIdx=1
  swipe(s,320,120,0,0)
  assert.equal(s.spotIdx,2,'left swipe uses move delta')
  swipe(s,120,320,0,0)
  assert.equal(s.spotIdx,1,'right swipe uses move delta')
})
test('vertical or tiny drags never switch spots',()=>{
  const {s}=component('pages/tour/tour.vue')
  s.spotCards=[{spot_id:51},{spot_id:52}];s.spotIdx=0
  swipe(s,200,210,210,330)
  assert.equal(s.spotIdx,0)
  swipe(s,200,190,190,200)
  assert.equal(s.spotIdx,0)
})
