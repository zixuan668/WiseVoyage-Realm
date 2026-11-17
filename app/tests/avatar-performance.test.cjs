const test=require('node:test'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict')
function loadPerformance(){
 const source=fs.readFileSync(path.resolve(__dirname,'../common/avatar-performance.js'),'utf8').replace(/export const /g,'const ').replace(/export function /g,'function ')
 const context={globalThis:{devicePixelRatio:1}}
 vm.runInNewContext(source+'\nthis.api={rightSizeAvatarCanvas,createAvatarQualityController,AVATAR_QUALITY_STEPS}',context)
 return context.api
}
const makeCanvas=(width=1080,height=1920,cssWidth=215,cssHeight=383)=>({width,height,style:{width:cssWidth+'px',height:cssHeight+'px'},getBoundingClientRect:()=>({width:cssWidth,height:cssHeight})})

test('native avatar clarity is retained even when WebView reports DPR 1',()=>{
 const {rightSizeAvatarCanvas,AVATAR_QUALITY_STEPS}=loadPerformance(),canvas=makeCanvas()
 assert.deepEqual(Array.from(AVATAR_QUALITY_STEPS),[1920,1280,960])
 assert.equal(rightSizeAvatarCanvas(canvas),false)
 assert.deepEqual([canvas.width,canvas.height],[1080,1920])
})
test('quality has a 960-pixel floor and can restore the original canvas without cumulative rounding',()=>{
 const {rightSizeAvatarCanvas}=loadPerformance(),canvas=makeCanvas()
 rightSizeAvatarCanvas(canvas,{maxLongEdge:1280});assert.deepEqual([canvas.width,canvas.height],[720,1280])
 rightSizeAvatarCanvas(canvas,{maxLongEdge:960});assert.deepEqual([canvas.width,canvas.height],[540,960])
 assert.equal(rightSizeAvatarCanvas(canvas,{maxLongEdge:1}),false)
 assert.deepEqual([canvas.width,canvas.height],[540,960])
 rightSizeAvatarCanvas(canvas,{maxLongEdge:1280});assert.deepEqual([canvas.width,canvas.height],[720,1280])
 rightSizeAvatarCanvas(canvas,{maxLongEdge:1920});assert.deepEqual([canvas.width,canvas.height],[1080,1920])
})
test('never upscales a lower-resolution source or modifies canvas CSS framing',()=>{
 const {rightSizeAvatarCanvas}=loadPerformance(),canvas=makeCanvas(360,640),style={...canvas.style}
 assert.equal(rightSizeAvatarCanvas(canvas),false);assert.deepEqual([canvas.width,canvas.height],[360,640]);assert.deepEqual(canvas.style,style)
 assert.equal(rightSizeAvatarCanvas(makeCanvas(1080,1920,0,0)),false)
 const large=makeCanvas(2160,3840);rightSizeAvatarCanvas(large);assert.deepEqual([large.width,large.height],[1080,1920])
})
test('startup and two transient low FPS samples never downgrade clarity',()=>{
 const q=loadPerformance().createAvatarQualityController();q.reset(0)
 for(let t=0;t<=9000;t+=1000)assert.equal(q.sample({current:10},t),0)
 q.sample({current:10},10000);q.sample({current:10},11000);assert.equal(q.step,0)
 for(let t=12000;t<=30000;t+=1000)assert.equal(q.sample({current:24},t),0)
})
test('sustained low FPS downgrades one step after warmup and respects cooldown and the floor',()=>{
 const q=loadPerformance().createAvatarQualityController();q.reset(0)
 for(let t=0;t<18000;t+=1000)assert.equal(q.sample({current:12},t),0)
 assert.equal(q.sample({current:12},18000),1)
 for(let t=19000;t<41000;t+=1000)assert.equal(q.sample({current:12},t),1)
 assert.equal(q.sample({current:12},41000),2)
 for(let t=42000;t<=90000;t+=1000)assert.equal(q.sample({current:12},t),2)
})
test('stable FPS restores high clarity progressively and a new session resets to native quality',()=>{
 const q=loadPerformance().createAvatarQualityController();q.reset(0)
 for(let t=0;t<=41000;t+=1000)q.sample({current:12},t)
 assert.equal(q.step,2)
 for(let t=42000;t<76000;t+=1000)assert.equal(q.sample({current:24},t),2)
 assert.equal(q.sample({current:24},76000),1)
 for(let t=77000;t<=111000;t+=1000)q.sample({current:24},t)
 assert.equal(q.step,0)
 for(let t=112000;t<=150000;t+=1000)q.sample({current:12},t)
 assert.ok(q.step>0);q.reset(150001);assert.equal(q.step,0)
})
test('callback frequency, suspended pages, missing frames and invalid FPS cannot manufacture a streak',()=>{
 const q=loadPerformance().createAvatarQualityController();q.reset(0)
 for(let t=10000;t<=11000;t+=5)q.sample({current:10},t)
 assert.equal(q.step,0)
 for(const t of [20000,24000,28000,32000])q.sample({current:10},t)
 assert.equal(q.step,0)
 for(let t=33000;t<=38000;t+=1000)q.sample({current:10},t)
 q.sample({current:0},39000);q.sample({current:NaN},40000)
 for(let t=41000;t<49000;t+=1000)assert.equal(q.sample({current:10},t),0)
})


test('the avatar component resets quality on reconnect and never measures layout on every FPS callback',async()=>{
 const root=path.resolve(__dirname,'..'),timers=new Map(),instances=[];let clock=0,nextTimer=0,canvas=makeCanvas(),measurements=0
 const makeMeasuredCanvas=()=>{const c=makeCanvas();c.getBoundingClientRect=()=>{measurements++;return {width:215,height:383}};return c}
 canvas=makeMeasuredCanvas()
 const context={Date:{now:()=>clock},loadXingyunSdk:async()=>{},console:{info(){},error(){}},document:{getElementById:()=>({querySelector:()=>canvas,innerHTML:''})},window:{XmovAvatar:class{
  constructor(options){this.options=options;instances.push(this)} async init(){} async destroy(){} speak(){}
 }},setTimeout:fn=>{timers.set(++nextTimer,fn);return nextTimer},clearTimeout:id=>timers.delete(id)}
 vm.createContext(context)
 vm.runInContext(fs.readFileSync(path.join(root,'common/avatar-performance.js'),'utf8').replace(/export /g,''),context)
 const source=fs.readFileSync(path.join(root,'components/tour-xingyun.vue'),'utf8').match(/<script module="runtime" lang="renderjs">([\s\S]*?)<\/script>/)[1]
 vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.component='),context)
 const flush=()=>{while(timers.size){const entries=[...timers.values()];timers.clear();entries.forEach(fn=>fn())}}
 const owner={callMethod(){}}
 await context.component.methods.apply({command:'connect',gateway:'http://local/session'},null,owner)
 instances[0].options.onInitEvent(4000);flush();assert.equal(canvas.height,1920)
 const before=measurements
 for(clock=0;clock<=9000;clock+=1000)instances[0].options.onFPSUpdate({current:24})
 assert.equal(measurements,before)
 for(clock=10000;clock<=41000;clock+=1000){instances[0].options.onFPSUpdate({current:12});flush()}
 assert.equal(canvas.height,960)
 await context.component.methods.apply({command:'close'},null,owner);assert.equal(timers.size,0)
 canvas=makeMeasuredCanvas()
 await context.component.methods.apply({command:'connect',gateway:'http://local/new-session'},null,owner)
 instances[1].options.onInitEvent(4000);flush()
 assert.equal(canvas.height,1920)
 instances[0].options.onFPSUpdate({current:10});flush();assert.equal(canvas.height,1920)
 context.component.beforeUnmount();assert.equal(timers.size,0)
})
