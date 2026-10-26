// Collect local application copy without touching user records or source code.
const fs=require('node:fs'),path=require('node:path'),ts=require('typescript')
const {parse}=require('@vue/compiler-sfc'),{baseParse}=require('@vue/compiler-dom')
const root=path.resolve(__dirname,'../src'),copy=new Set(),han=/[\u3400-\u9fff]/
function collect(text){
 const sf=ts.createSourceFile('copy.ts',text,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS)
 function walk(n){
  if((ts.isStringLiteral(n)||ts.isNoSubstitutionTemplateLiteral(n))&&han.test(n.text))copy.add(n.text)
  if(ts.isTemplateExpression(n)&&han.test(n.getText(sf))){let key=n.head.text;n.templateSpans.forEach((s,i)=>key+='{p'+i+'}'+s.literal.text);copy.add(key)}
  ts.forEachChild(n,walk)
 }walk(sf)
}
function dir(folder){for(const entry of fs.readdirSync(folder,{withFileTypes:true})){
 const file=path.join(folder,entry.name)
 if(entry.isDirectory()){if(!['__tests__','style','assets','i18n'].includes(entry.name))dir(file);continue}
 if(!/\.(vue|ts)$/.test(file))continue
 const text=fs.readFileSync(file,'utf8')
 if(file.endsWith('.ts')){collect(text);continue}
 const {descriptor}=parse(text)
 for(const b of [descriptor.script,descriptor.scriptSetup])if(b)collect(b.content)
 if(descriptor.template){const walk=function(n){if(n.type===2&&han.test(n.content))copy.add(n.content.trim());if(n.type===5)collect(n.content.content);if(n.type===1)for(const p of n.props){if(p.type===6&&p.value&&han.test(p.value.content))copy.add(p.value.content);if(p.type===7&&p.exp)collect(p.exp.content)}for(const c of n.children||[])walk(c)};walk(baseParse(descriptor.template.content))}
}}
dir(root)
const output=path.resolve(__dirname,'../../work_dirs/ui-source-catalog.json')
fs.mkdirSync(path.dirname(output),{recursive:true})
fs.writeFileSync(output,JSON.stringify([...copy].sort(),null,2))
console.log('Collected',copy.size,'entries')
