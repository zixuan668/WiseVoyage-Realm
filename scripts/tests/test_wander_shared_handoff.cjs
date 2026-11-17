const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs')
const file='D:/桌面/数字人项目/WiseVoyage-Realm-main/app/common/wander-handoff.js'
async function load(){return import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(file)).toString('base64'))}
test('shared plan preserves real route order and walking conditions',async()=>{
 const {sharedPlanUrl}=await load()
 const url=sharedPlanUrl({ids:[3,1],senior:false,child:true,planning:{start_area:'east',end_area:'north',avoid_steps:true}})
 const query=new URL(url,'http://test').searchParams
 assert.equal(query.get('view'),'plan');assert.equal(query.get('spotIds'),'3,1')
 assert.equal(query.get('children'),'1');assert.equal(query.get('elderly'),'0')
 assert.equal(query.get('avoidSteps'),'1');assert.equal(query.get('startArea'),'east');assert.equal(query.get('endArea'),'north')
})
test('invalid scenic IDs cannot enter the shared plan',async()=>{
 const {sharedPlanUrl}=await load()
 for(const ids of [[],[1,1],[-1],[1.2],['1'],Array.from({length:21},(_,i)=>i+1)])assert.throws(()=>sharedPlanUrl({ids}))
})
test('successful recommendations enter shared planning without rendering the old recommendation page',async()=>{
 const vm=require('node:vm')
 const source=fs.readFileSync('D:/桌面/数字人项目/WiseVoyage-Realm-main/app/components/WanderPlanner.vue','utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
 const component=vm.runInNewContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.component=')+';component',{WanderIcon:{},RouteRoadMap:{},assetUrl:x=>x,walkingDistance(){}})
 const events=[],state={mode:'time',stage:'time',ids:[3,1],planning:{avoid_steps:true},senior:false,child:true,
  arrange:async(_work,next)=>{state.stage=next;return true},$emit:(...args)=>events.push(args)}
 await component.methods.generate.call(state)
 assert.equal(state.stage,'loading');assert.equal(events.length,1);assert.equal(events[0][0],'plan')
 assert.deepEqual([...events[0][1].ids],[3,1]);assert.equal(events[0][1].child,true)
})
