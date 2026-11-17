const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),ts=require('../../frontend/node_modules/typescript')
const source=fs.readFileSync('frontend/src/views/scenic-app/ScenicDetailView.vue','utf8')
const defer=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve}}
function harness(){
 const calls=[],pending={},c={catalog:{value:[]},stops:{value:[]},ready:{value:false},catalogError:{value:''},elderly:{},children:{},fewSteps:{},startArea:{},endArea:{},coverMap:{},endpoint:'/tour-experience/scenic-selection',waitForAppToken:()=>new Promise(()=>{}),applyRequestedSpots:async()=>false,writeScenicCatalog(){},Image:class{},request_handler:{get(url){calls.push(url);pending[url]=defer();return pending[url].promise}}}
 vm.createContext(c)
 vm.runInContext(ts.transpileModule(source.slice(source.indexOf('async function refresh()'),source.indexOf('async function changeStop')), {compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText,c)
 return{c,calls,pending}
}
test('catalog request starts immediately without waiting for app authentication',()=>{const h=harness();void h.c.refresh();assert.ok(h.calls.includes('/tour-experience/scenic-catalog'))})
test('catalog renders while personal selection and settings are still loading',async()=>{
 const h=harness();void h.c.refresh();assert.ok(h.pending['/tour-experience/scenic-catalog'])
 h.pending['/tour-experience/scenic-catalog'].resolve({data:[{id:51,name:'仁寿殿',park:'summer-palace'}]})
 await new Promise(r=>setImmediate(r));assert.equal(h.c.catalog.value[0]?.name,'仁寿殿')
})
test('background refresh retains the ready screen',()=>{const h=harness();h.c.ready.value=true;void h.c.refresh();assert.equal(h.c.ready.value,true)})
