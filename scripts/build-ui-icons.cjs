// Rebuild the small local icon subset; no network or icon package is needed.
const fs=require('node:fs'),path=require('node:path')
const root=path.resolve(__dirname,'..'),catalog=JSON.parse(fs.readFileSync(path.join(root,'shared/ui-icons.json'),'utf8'))
const escape=value=>String(value).replace(/&/g,'&amp;').replace(/"/g,'&quot;')
function svg(name,filled=false){
 const nodes=catalog.icons[name];if(!nodes)throw Error('Unknown icon: '+name)
 const body=nodes.map(([tag,attrs])=>'<'+tag+' '+Object.entries(attrs).map(([key,value])=>key+'="'+escape(value)+'"').join(' ')+'/>').join('')
 return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="'+(filled?'currentColor':'none')+'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'+body+'</svg>'
}
const mask=(name,filled)=>'url("data:image/svg+xml,'+encodeURIComponent(svg(name,filled)).replace(/[!'()*]/g,char=>'%'+char.charCodeAt(0).toString(16).toUpperCase())+'")'
const css=[
 '/* Generated from the locally bundled Lucide subset; see shared/ui-icons.json and LICENSE. */',
 '.iconfont{display:inline-flex;align-items:center;justify-content:center;width:1em;height:1em;line-height:1;vertical-align:-.125em;flex-shrink:0;font-family:inherit!important;font-style:normal;}',
 '.iconfont::before{content:""!important;display:block;width:1em;height:1em;background-color:currentColor;-webkit-mask-image:var(--ui-icon-mask);mask-image:var(--ui-icon-mask);-webkit-mask-size:contain;mask-size:contain;-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;-webkit-mask-position:center;mask-position:center;}',
 ...Object.entries(catalog.appAliases).map(([alias,name])=>'.'+alias+'{--ui-icon-mask:'+mask(name)+';}'),
 '.rating-star.selected .icon-star{--ui-icon-mask:'+mask('star',true)+';}',
 '.c-like.liked .icon-huore{--ui-icon-mask:'+mask('heart',true)+';}',
]
const cssPath=path.join(root,'app/static/iconfont/iconfont-inline.css')
fs.writeFileSync(cssPath,css.join('\n')+'\n')
const indexPath=path.join(root,'frontend/src/icons/index.ts'),index=fs.readFileSync(indexPath,'utf8'),start=index.indexOf('\nexport const '),end=index.indexOf('// Leaflet markers')
if(start<0||end<start)throw Error('Icon export block not found')
const iconExports=Object.entries(catalog.webAliases).map(([alias,name])=>`export const ${alias} = createIcon('${name}', '${alias}')`).join('\n')
fs.writeFileSync(indexPath,index.slice(0,start)+'\n'+iconExports+'\n\n'+index.slice(end))
console.log(`Generated ${Object.keys(catalog.icons).length} bundled vector icons.`)
