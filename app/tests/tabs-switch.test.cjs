const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..')
function shell(){
 const calls=[],events={},panels=[0,1,2].map(index=>({$options:Object.fromEntries(['onLoad','onReady','onShow','onHide','onUnload'].map(hook=>[hook,function(){calls.push([index,hook])}]))}))
 const context={TourGuide:{},AiChat:{},Mine:{},TabDock:{},console,Math,Number,String,Object,Array,setTimeout,clearTimeout,uni:{getSystemInfoSync:()=>({windowWidth:393}),hideKeyboard(){},$on:(event,fn)=>events[event]=fn,$off:event=>delete events[event]}}
 vm.createContext(context)
 const source=fs.readFileSync(path.join(root,'pages/tabs/tabs.vue'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
 vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.options='),context)
 const o=context.options,s={$refs:{tour:panels[0],ai:panels[1],mine:panels[2]},$nextTick:fn=>fn()};Object.assign(s,o.data.call(s))
 for(const [key,fn] of Object.entries(o.methods))s[key]=fn.bind(s)
 for(const [key,fn] of Object.entries(o.computed))Object.defineProperty(s,key,{get:fn.bind(s)})
 o.onLoad.call(s,{});o.onShow.call(s);o.mounted.call(s)
 return {s,o,calls,events}
}
const finish=(s,index)=>s.onPagerFinish({detail:{current:index}})

test('page hooks run once on first use and switching waits until the page has settled',()=>{
 const {s,calls}=shell();assert.deepEqual(calls,[[0,'onLoad'],[0,'onReady'],[0,'onShow']])
 s.selectTab(2);assert.equal(s.pagerCurrent,2);assert.equal(s.current,0)
 assert.equal(calls.some(([index,hook])=>index===2&&hook==='onShow'),false)
 finish(s,2);assert.equal(s.current,2);assert.deepEqual(calls.slice(-2),[[0,'onHide'],[2,'onShow']])
 s.selectTab(0);finish(s,0);assert.equal(calls.filter(([i,h])=>i===0&&h==='onLoad').length,1)
})
test('rapid taps use the last requested page without restarting the current animation',()=>{
 const {s,calls}=shell();s.selectTab(2);s.selectTab(1);s.selectTab(0)
 assert.equal(s.pagerCurrent,2);finish(s,2);assert.equal(s.pagerCurrent,0)
 finish(s,2);assert.equal(s.current,2,'stale animation completion must be ignored')
 finish(s,0);assert.equal(s.current,0);assert.equal(s.switching,false)
 assert.equal(calls.some(([i,h])=>i===1&&h==='onShow'),false)
})
test('native swipes use the same completion path and duplicate finish events never repeat hooks',()=>{
 const {s,calls}=shell();s.onPagerChange({detail:{current:1,source:'touch'}});assert.equal(s.pagerCurrent,1);assert.equal(s.current,0)
 finish(s,1);const count=calls.length;finish(s,1);assert.equal(calls.length,count);assert.equal(s.current,1)
 for(const value of [-1,3,NaN,1.5]){s.selectTab(value);s.onPagerChange({detail:{current:value}})}
 assert.equal(s.pagerCurrent,1)
})
test('tapping the in-flight destination cancels a previously queued return',()=>{
 const {s}=shell();s.selectTab(2);s.selectTab(0);s.selectTab(2);finish(s,2)
 assert.equal(s.current,2);assert.equal(s.pagerCurrent,2);assert.equal(s.pendingTab,null);assert.equal(s.switching,false)
})
test('leaving during a transition never starts hidden page work and removes listeners',()=>{
 const {s,o,calls,events}=shell();s.selectTab(1);o.onHide.call(s);finish(s,1)
 assert.equal(calls.some(([i,h])=>i===1&&h==='onShow'),false)
 o.onShow.call(s);assert.deepEqual(calls.at(-1),[1,'onShow'])
 o.onUnload.call(s);assert.equal(Object.keys(events).length,0)
})
