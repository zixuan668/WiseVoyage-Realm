const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..')
function dock(props={}){
  const c={console,Date,Promise,setTimeout,clearTimeout,Math,Number,String,Object,Array}
  vm.createContext(c)
  const source=fs.readFileSync(path.join(root,'components/TabDock.vue'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
  vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.options='),c)
  const o=c.options,s={...props,t:x=>x};Object.assign(s,o.data.call(s))
  for(const [k,f] of Object.entries(o.methods||{}))s[k]=f.bind(s)
  for(const [k,g] of Object.entries(o.computed||{}))Object.defineProperty(s,k,{get:(typeof g==='function'?g:g.get).bind(s),configurable:true})
  s.$emit=()=>{}
  return s
}
test('the dock only switches with the tab, and never moves while a page is sliding',()=>{
  // AI 页：整条隐藏，样式是瞬时值，没有过渡。
  const onAi=dock({aiHidden:true,current:1,progress:1,hidden:false})
  assert.equal(onAi.hideAmount,1)
  assert.match(onAi.dockStyle.transform,/translate3d\(0,108%,0\)/)
  assert.ok(Math.abs(Number(onAi.dockStyle.opacity)-0.34)<1e-9)
  assert.equal(onAi.dockStyle.pointerEvents,'none')
  // 普通页滑动过程中：无论 progress 走到哪，Tab 栏都原地不动。
  for (const p of [0,0.25,0.5,0.75,1,1.5,2]) {
    const s=dock({aiHidden:false,current:0,progress:p,hidden:false})
    assert.equal(s.hideAmount,0,('progress '+p))
    assert.match(s.dockStyle.transform,/translate3d\(0,0%,0\) scale\(1\)/)
  }
})
test('keyboard and itinerary still could hide the dock while normal pages keep it visible',()=>{
  assert.equal(dock({aiHidden:false,hidden:true}).hideAmount,1)
  assert.equal(dock({aiHidden:false,current:2,progress:2,hidden:false}).hideAmount,0)
  assert.equal(dock({aiHidden:true,current:2,progress:2,hidden:false}).hideAmount,1)
})

test('tapping the highlighted destination can cancel an older queued tab selection',()=>{
  const s=dock({current:2,progress:2}),selected=[]
  s.$emit=(event,index)=>selected.push([event,index])
  s.pick(2)
  assert.deepEqual(selected,[['select',2]])
})
