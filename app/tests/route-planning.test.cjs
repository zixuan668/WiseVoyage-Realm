const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..'),plain=value=>JSON.parse(JSON.stringify(value)),tick=()=>new Promise(resolve=>setImmediate(resolve))
function environment(){
  const calls=[],storage={token:'account-token',user_id:5,'xingyun-tour-7':'tour-capability'}
  const uni={getStorageSync:key=>storage[key],setStorageSync:(key,value)=>storage[key]=value,removeStorageSync:key=>delete storage[key],showToast(){},navigateTo(){},reLaunch(){},getSystemInfoSync:()=>({}),request(options){const call={...options,aborted:false};calls.push(call);return{abort(){call.aborted=true}}}}
  const context={uni,console,Promise,Date,Set,Number,Math,JSON,setTimeout,clearTimeout,setInterval:()=>1,clearInterval(){},BASE_URL:'http://local/api/v1'}
  vm.createContext(context)
  const coords=fs.readFileSync(path.join(root,'../shared/coordinates.js'),'utf8').replace(/export /g,'')
  vm.runInContext(coords,context)
  const source=fs.readFileSync(path.join(root,'common/route-planning.js'),'utf8').replace(/^import .*$/gm,'').replace(/export /g,'')
  vm.runInContext(source+'\nglobalThis.helpers={selectedOrder,moveStop,previewOptions,roadMap,routeRequest,isRouteChange,repairDefaults}',context)
  Object.assign(context,context.helpers)
  return{context,calls,storage,helpers:context.helpers,respond(call,data,status=200){call.success({statusCode:status,data:status===200?{success:true,data}:data})}}
}
function component(env,file,props={}){
  const source=fs.readFileSync(path.join(root,file),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
  Object.assign(env.context,{FloatingTourButton:{},ScenicSheet:{},RouteOverview:{},RouteTiming:{},TourRouteRepair:{},NocturneConfirm:{},TourXingyun:{},TourXfyun:{},prioritizeSummerPalace:(spots,routes)=>({spots,routes}),LANGUAGE_STORAGE_KEY:'language',translateTour:x=>x,assetUrl:x=>x})
  vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.options='),env.context)
  const options=env.context.options,events=[],state={...props};Object.assign(state,options.data.call(state));
  state.$emit=(...args)=>events.push(args);state.t=x=>x;state.$nextTick=async callback=>{callback?.()};state.$forceUpdate=()=>{}
  for(const [name,method] of Object.entries(options.methods||{}))state[name]=method.bind(state)
  for(const [name,getter] of Object.entries(options.computed||{}))Object.defineProperty(state,name,{get:(typeof getter==='function'?getter:getter.get).bind(state),configurable:true})
  return{state,options,events}
}
const spots=[{spot_id:12,spot_name:'A',city:'北京'},{spot_id:3,spot_name:'B',city:'北京'},{spot_id:11,spot_name:'C',city:'北京'}]
test('AI route handoff preserves server order, budget and pace, and rejects another account',()=>{
 const env=environment(),{state:s}=component(env,'pages/tour-guide/tour-guide.vue');s.spots=spots
 const plan={spot_ids:[12,11,3],requested_time_minutes:150,pace:'relaxed',preferences:['nature'],estimated_time_minutes:91}
 env.storage.ai_spot_ids=JSON.stringify(plan.spot_ids);env.storage.ai_route_plan=JSON.stringify(plan);env.storage.ai_route_owner='id:5';s.restoreAISelection()
 assert.deepEqual(plain(s.selectedIds),[12,11,3]);assert.equal(s.budgetOptions[s.budgetIndex],150);assert.equal(s.paceIndex,1);assert.equal(s.personalPlan.estimated_time_minutes,91)
 env.storage.ai_route_plan=JSON.stringify({...plan,spot_ids:[3]});env.storage.ai_route_owner='id:other';s.restoreAISelection();assert.deepEqual(plain(s.selectedIds),[12,11,3])
})
function plan(overrides={}){return{feasible:true,proposal_token:'signed-plan',expires_at:Date.now()/1000+600,next_spots:[spots[2]],removed:[],totals:{walking_meters:250,total_minutes:30},original_totals:{walking_meters:500,total_minutes:60},options:{remaining_minutes:40,pace:'standard',end_area:'auto',reserve_minutes:0,excluded_spot_ids:[3],required_spot_ids:[],scenario:'time',allow_reorder:true,avoid_steps:false},...overrides}}

test('selected numeric IDs preserve user order across move, removal and reselection',()=>{
  const {helpers:h}=environment();const original=[12,3,11]
  assert.deepEqual(plain(h.selectedOrder(original,{3:true,11:true,12:true})),original)
  assert.deepEqual(plain(h.moveStop(original,11,-1)),[12,11,3]);assert.deepEqual(original,[12,3,11])
  assert.deepEqual(plain(h.selectedOrder([12,11],{12:true,11:true,3:true})),[12,11,3])
})
test('route map uses real road geometry and never draws missing straight connectors',()=>{
  const {helpers:h}=environment(),m=h.roadMap({stops:[],legs:[{geometry:[[40,116],[40.01,116.01]]},{available:false,geometry:[[40,116],[41,117]]},{geometry:[[999,116],[40,117]]},{meters:123}]})
  assert.equal(m.polyline.length,1);assert.equal(m.polyline[0].points.length,2)
})
test('repair initial time accounts for elapsed time and applied replan, with route intent negations',()=>{
  const {helpers:h}=environment(),now=Date.now()
  assert.equal(h.repairDefaults({visitor_preferences:JSON.stringify({last_replan:{remaining_minutes:40,applied_at:(now-5*60000)/1000,pace:'relaxed'}})},now).minutes,35)
  assert.equal(h.isRouteChange('I have 40 minutes left, skip the next stop'),true)
  assert.equal(h.isRouteChange('I am not tired, do not replan'),false)
})
test('negated skip and exit requests do not trigger a contrary route change',()=>{
  const {helpers:h}=environment()
  assert.equal(h.isRouteChange('不要跳过下一站'),false)
  assert.equal(h.isRouteChange("Don't skip the next stop"),false)
  assert.equal(h.isRouteChange('准备离园，从东宫门走'),true)
})
test('preview and apply requests carry both account auth and the matching tour capability',async()=>{
  const env=environment(),request=env.helpers.routeRequest('/tour-session/7/replan/preview',{remaining_minutes:40},7)
  assert.equal(env.calls[0].header.Authorization,'Bearer account-token');assert.equal(env.calls[0].header['X-Tour-Access'],'tour-capability')
  env.respond(env.calls[0],{detail:'方案已过期，请重新生成'},409)
  await assert.rejects(request.promise,error=>error.status===409&&/已过期/.test(error.message))
})
test('late route preview cannot replace a newer ordering or reopen a disposed panel',async()=>{
  const env=environment(),c=component(env,'components/RouteTiming.vue',{ids:[12,3],spots,plan:null,pace:'standard'}),s=c.state
  const first=s.refresh();s.ids=[3,12];const second=s.refresh();assert.equal(env.calls[0].aborted,true)
  env.respond(env.calls[1],{total_minutes:33,complete:true});await second;env.respond(env.calls[0],{total_minutes:99,complete:true});await first
  assert.equal(s.overview.total_minutes,33)
  const third=s.refresh();c.options.beforeUnmount.call(s);env.respond(env.calls[2],{total_minutes:100});await third;assert.equal(s.overview.total_minutes,33)
})
test('time and exit validation prevent invalid previews, and preview never applies a plan',async()=>{
  const env=environment(),{state:s}=component(env,'components/TourRouteRepair.vue',{sid:7,currentName:'A',remainingSpots:spots.slice(1),prompt:'',initial:{}})
  await s.preview();assert.match(s.error,/剩余时间/);assert.equal(env.calls.length,0)
  s.minutes='1.5';await s.preview();assert.match(s.error,/1至480/)
  s.minutes='40';s.scenario='exit';await s.preview();assert.match(s.error,/具体离园出口/)
  s.scenario='time';const pending=s.preview();assert.match(env.calls[0].url,/replan\/preview$/);env.respond(env.calls[0],plan());await pending
  assert.equal(s.canApply,true);assert.equal(env.calls.length,1);assert.equal(s.message,'');assert.equal(s.choices[3],'skip')
})
test('only selected feasible, current, unexpired proposals can be applied',async()=>{
  const env=environment(),c=component(env,'components/TourRouteRepair.vue',{sid:7,currentName:'A',remainingSpots:spots.slice(1),prompt:'',initial:{minutes:40}}),s=c.state;s._owner=s.owner()
  const pending=s.preview();env.respond(env.calls[0],plan({alternatives:[plan({proposal_token:'alternative-token'})]}));await pending
  s.minutes='41';await s.apply();assert.equal(env.calls.length,1);s.minutes=40
  s.clock=Date.now()+700000;await s.apply();assert.equal(env.calls.length,1);s.clock=Date.now()
  s.plans[0].feasible=false;await s.apply();assert.equal(env.calls.length,1)
  s.selected=1;const applying=s.apply();assert.equal(env.calls[1].data.proposal_token,'alternative-token');env.respond(env.calls[1],{spot_ids:[12,11]});await applying
  assert.equal(c.events.at(-1)[0],'applied')
})
test('changed progress rejects an old proposal and requests live state refresh',async()=>{
  const env=environment(),c=component(env,'components/TourRouteRepair.vue',{sid:7,currentName:'A',remainingSpots:spots.slice(1),prompt:'',initial:{minutes:40}}),s=c.state;s._owner=s.owner()
  const pending=s.preview();env.respond(env.calls[0],plan());await pending
  const applying=s.apply();env.respond(env.calls[1],{detail:'路线或进度已变化，请重新生成方案'},409);await applying
  assert.equal(s.plans.length,0);assert.equal(c.events.at(-1)[0],'refresh');assert.match(s.error,/进度已变化/)
})
test('creating a tour uses the visible ordered IDs and retains order between planning tabs',async()=>{
  const env=environment(),c=component(env,'pages/tour-guide/tour-guide.vue'),s=c.state;s.spots=spots;s.pickedIds={12:true,3:true,11:true};s.orderedIds=[12,3,11];s.pickedGuide={guide_id:2};s.pageVisible=true
  s.switchPlanningTab('personal');s.switchPlanningTab('route');assert.deepEqual(plain(s.selectedIds),[12,3,11])
  s.moveSelectedSpot(11,-1);assert.deepEqual(plain(s.selectedIds),[12,11,3]);s.itineraryState={key:s.itineraryKey,busy:false,error:'',data:{complete:true}};assert.equal(s.canStart,true)
  s.startTour();assert.deepEqual(JSON.parse(new URL(env.calls[0].url).searchParams.get('spot_ids')),[12,11,3]);s.startTour();assert.equal(env.calls.length,1);s.moveSelectedSpot(3,-1);assert.deepEqual(plain(s.selectedIds),[12,11,3])
  env.respond(env.calls[0],{});await tick()
})

test('expired sign-in clears the stale credential and opens sign-in instead of reporting a network error',async()=>{
  const env=environment(),{state:s}=component(env,'pages/tour-guide/tour-guide.vue'),nav=[],toasts=[]
  env.context.uni.reLaunch=o=>nav.push(o.url);env.context.uni.showToast=o=>toasts.push(o.title)
  env.storage.login_provider='password'
  s.spots=spots;s.pickedIds={12:true};s.orderedIds=[12];s.pickedGuide={guide_id:2}
  s.itineraryState={key:s.itineraryKey,busy:false,error:'',data:{complete:true}}
  s.startTour();env.respond(env.calls[0],{detail:'Could not validate credentials'},401);await tick()
  assert.equal(env.storage.token,undefined);assert.equal(env.storage.login_provider,undefined)
  assert.deepEqual(nav,['/pages/auth/auth?expired=1']);assert.deepEqual(toasts,[]);assert.equal(s.starting,false)
  assert.equal(env.calls.length,1,'must not start a tour with an invalid account')
})

test('a late unauthorized response cannot sign out a newly signed-in account',async()=>{
  const env=environment(),{state:s}=component(env,'pages/tour-guide/tour-guide.vue'),nav=[]
  env.context.uni.reLaunch=o=>nav.push(o.url)
  s.spots=spots;s.pickedIds={12:true};s.orderedIds=[12];s.pickedGuide={guide_id:2}
  s.itineraryState={key:s.itineraryKey,busy:false,error:'',data:{complete:true}}
  s.startTour();env.storage.token='new-account-token'
  env.respond(env.calls[0],{},401);await tick()
  assert.equal(env.storage.token,'new-account-token');assert.deepEqual(nav,[])
})

test('tour creation shows service errors separately from connection failures',async()=>{
  for(const status of [409,0]){
    const env=environment(),{state:s}=component(env,'pages/tour-guide/tour-guide.vue'),toasts=[]
    env.context.uni.showToast=o=>toasts.push(o.title)
    s.spots=spots;s.pickedIds={12:true};s.orderedIds=[12];s.pickedGuide={guide_id:2}
    s.itineraryState={key:s.itineraryKey,busy:false,error:'',data:{complete:true}}
    s.startTour()
    if(status)env.respond(env.calls[0],{detail:'数字人暂不可用，请重新选择'},status)
    else env.calls[0].fail({errMsg:'request:fail timeout'})
    await tick()
    assert.equal(toasts[0],status?'数字人暂不可用，请重新选择':'网络连接失败，请稍后重试')
    assert.equal(s.starting,false)
  }
})
