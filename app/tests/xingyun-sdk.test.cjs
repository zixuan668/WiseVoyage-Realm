const {test}=require('node:test')
const assert=require('node:assert/strict')
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..')
const sdk=fs.readFileSync(path.join(root,'static/sdk/xmov-avatar-2.4.1-compatible.js'),'utf8')

test('Android accepts actual decoded hardware frames and still rejects decoding failures',async()=>{
  const start=sdk.indexOf('checkVideoDecodeDetailed=function'),end=sdk.indexOf(',checkWebCodecsDetailed=function',start)
  assert.ok(start>0&&end>start)
  let result={supported:true,frames:3,primaryConfig:{hardwareAcceleration:'prefer-hardware',supported:true}}
  const context={window:{VideoDecoder:function(){}},isAndroidPlatform:()=>true,streamingVideo:{workerURL:'test'},probeVideoDecode:async()=>result,_catch$2:(run,failed)=>Promise.resolve().then(run).catch(failed)}
  vm.runInNewContext('var '+sdk.slice(start,end),context)
  assert.equal((await context.checkVideoDecodeDetailed('prefer-hardware')).supported,true)
  result={supported:false,frames:0,reason:'No decoded frames'}
  const failed=await context.checkVideoDecodeDetailed('prefer-hardware')
  assert.equal(failed.supported,false);assert.equal(failed.severity,'fatal')
  assert.ok(!sdk.includes("let config = isAndroid ? { ...defaultConfig, hardwareAcceleration: 'prefer-software' }"))
})

function loaderHarness(){
  const nodes=[],runtimeWindow={},document={createElement:()=>({remove(){this.removed=true}}),head:{appendChild:node=>nodes.push(node)}}
  const context={setTimeout,clearTimeout,Promise}
  vm.createContext(context)
  vm.runInContext(fs.readFileSync(path.join(root,'common/xingyun-sdk.js'),'utf8').replace('export const','const').replace('export function','function')+'\nglobalThis.load=loadXingyunSdk',context)
  return {nodes,window:runtimeWindow,load:()=>context.load(runtimeWindow,document)}
}

test('packaged loader deduplicates its script load',async()=>{
  const h=loaderHarness(),first=h.load(),second=h.load()
  assert.equal(first,second);assert.equal(h.nodes.length,1)
  assert.equal(h.nodes[0].src,'./static/sdk/xmov-avatar-2.4.1-compatible.js')
  h.window.XmovAvatar=function Avatar(){};h.nodes[0].onload()
  assert.equal(await first,h.window.XmovAvatar);assert.equal(await h.load(),h.window.XmovAvatar)
  assert.equal(h.nodes.length,1)
})

test('SDK load failure can be retried and an empty script is not treated as success',async()=>{
  const h=loaderHarness(),first=h.load();h.nodes[0].onerror()
  await assert.rejects(first,/资源加载失败/);assert.equal(h.nodes[0].removed,true)
  const second=h.load();assert.equal(h.nodes.length,2);h.nodes[1].onload()
  await assert.rejects(second,/资源加载失败/)
  const third=h.load();h.window.XmovAvatar=function Avatar(){};h.nodes[2].onload()
  assert.equal(await third,h.window.XmovAvatar)
})

for(const [file,moduleName] of [['tour-xingyun.vue','runtime']]){
  test(file+' initializes its SDK and surfaces failures',async()=>{
    const source=fs.readFileSync(path.join(root,'components',file),'utf8').match(new RegExp('<script module="'+moduleName+'" lang="renderjs">([\\s\\S]*?)<\\/script>'))[1]
    const instances=[],events=[]
    const context={loadXingyunSdk:async()=>{},window:{XmovAvatar:class{
      constructor(options){this.options=options;instances.push(this)}
      async init(options){this.initOptions=options}
      destroy(){}
    }},document:{getElementById:()=>({innerHTML:''}),createElement:()=>({}),head:{appendChild:node=>{if(node.onload)node.onload()}}},setTimeout:()=>1,clearTimeout(){},console:{error(){}}}
    vm.createContext(context)
    vm.runInContext(fs.readFileSync(path.join(root,'common/avatar-audio.js'),'utf8').replace(/export /g,''),context)
    vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.component='),context)
    const owner={callMethod:(method,event)=>events.push(event)}
    await context.component.methods.apply({command:'connect',id:1,gateway:'http://local/session',accessToken:'test',sdkUrl:'http://local/sdk.js',text:'',token:'test'},null,owner)
    assert.equal(instances.length,1)
    assert.equal(instances[0].options.hardwareAcceleration,'prefer-hardware')
    instances[0].options.onMessage({code:1234,message:'Decoder unavailable'})
    assert.equal(events.at(-1).state,'error');assert.match(events.at(-1).message,/Decoder unavailable/)
    context.component.beforeUnmount()
  })
}

 test('tour keeps the native SDK canvas inside the centered display frame',()=>{
 const source=fs.readFileSync(path.join(root,'components/tour-xingyun.vue'),'utf8');
 assert.ok(source.includes(':deep([width][height])'));
 assert.ok(/transform:\s*none!important/.test(source));
 });

test('tour uses the reviewed SDK and a centered wide frame',()=>{
const source=fs.readFileSync(path.join(root,'components/tour-xingyun.vue'),'utf8');
assert.ok(source.includes('transform:translateX(0)'));
assert.ok(!source.includes('script.src=value.sdkUrl'));
assert.ok(source.includes('await loadXingyunSdk()'));
assert.ok(source.includes("hardwareAcceleration:'prefer-hardware'"));
assert.ok(fs.readFileSync(path.join(root,'pages/tour/tour.vue'),'utf8').includes('aspect-ratio:16/9'));
});

for(const [file,moduleName] of [['tour-xingyun.vue','runtime']]){
 test(file+' serializes a pending destroy across rapid reconnects',async()=>{
  let releaseOld;const instances=[]
  const c={Promise,loadXingyunSdk:async()=>{},setTimeout:()=>1,clearTimeout(){},console,document:{getElementById:()=>({innerHTML:''})},window:{XmovAvatar:class{
   constructor(){instances.push(this)}
   init(){return Promise.resolve()}
   destroy(){return instances.indexOf(this)===0?new Promise(r=>{releaseOld=r}):Promise.resolve()}
  }}}
  vm.createContext(c)
  vm.runInContext(fs.readFileSync(path.join(root,'common/avatar-audio.js'),'utf8').replace(/export /g,''),c)
  const source=fs.readFileSync(path.join(root,'components',file),'utf8').match(new RegExp('<script module="'+moduleName+'" lang="renderjs">([\\s\\S]*?)<\\/script>'))[1]
  vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.component='),c)
  const apply=c.component.methods.apply,owner={callMethod(){}}
  await apply({gateway:'initial',command:'connect'},null,owner)
  const first=apply({gateway:'first',command:'connect'},null,owner)
  const second=apply({gateway:'second',command:'connect'},null,owner)
  await new Promise(r=>setImmediate(r))
  assert.equal(instances.length,1,'no new SDK before old destroy resolves')
  releaseOld();await Promise.all([first,second])
  assert.equal(instances.length,2,'only the newest connection survives')
  await apply({command:'close'},null,owner)
 })
}
