const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path')
const root=path.resolve(__dirname,'../..')
function vueFiles(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(item=>item.isDirectory()?vueFiles(path.join(dir,item.name)):item.name.endsWith('.vue')?[path.join(dir,item.name)]:[])}

test('every App functional icon resolves a local vector mask without a font download',()=>{
 const css=fs.readFileSync(path.join(root,'app/static/iconfont/iconfont-inline.css'),'utf8')
 assert.ok(!/@font-face|data:font|\.woff2?/.test(css),'icons should not download a font')
 assert.match(css,/-webkit-mask-image/);assert.match(css,/background-color:currentColor/)
 const defined=new Set([...css.matchAll(/\.(icon-[\w-]+)\s*\{/g)].map(match=>match[1]))
 for(const file of [...vueFiles(path.join(root,'app/pages')),...vueFiles(path.join(root,'app/components'))]){
  for(const match of fs.readFileSync(file,'utf8').matchAll(/(?<![\w-])(icon-[\w-]+)/g))assert.ok(defined.has(match[1]),`${path.relative(root,file)} uses missing ${match[1]}`)
 }
})

test('the shared icon subset contains only local, recolorable vector primitives',()=>{
 const catalog=JSON.parse(fs.readFileSync(path.join(root,'shared/ui-icons.json'),'utf8'))
 assert.equal(catalog.source.library,'Lucide');assert.ok(Object.keys(catalog.icons).length<100)
 for(const [name,nodes] of Object.entries(catalog.icons)){
  assert.ok(nodes.length>0,name)
  for(const [tag,attributes] of nodes){assert.ok(['path','circle','line','polyline','polygon','rect','ellipse'].includes(tag),name);for(const [key,value] of Object.entries(attributes)){assert.doesNotMatch(key,/^on|href|style/i);assert.doesNotMatch(String(value),/https?:|javascript:/i)}}
 }
})
