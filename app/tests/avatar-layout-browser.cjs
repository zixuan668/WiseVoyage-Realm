// CSS from the App and actual layout methods from its pinned SDK. Synthetic
// canvas content only: no real avatar session or Android device is claimed.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict')
const {chromium}=require('playwright-core')
const root=path.resolve(__dirname,'..'),version=process.env.APP_QA_VERSION||'1.2.8',out=path.join(root,'unpackage/main-d31183c-'+version+'/avatar-layout-results')
fs.mkdirSync(out,{recursive:true})
const component=fs.readFileSync(path.join(root,'components/tour-xingyun.vue'),'utf8')
let css=component.match(/<style scoped>([\s\S]*?)<\/style>/)[1].replace(/:deep\(([^)]+)\)/g,'$1'),scope=''
if(process.env.APP_QA_NATIVE_DIR){css=fs.readFileSync(path.join(process.env.APP_QA_NATIVE_DIR,'pages/tour/tour.css'),'utf8');scope=css.match(/#tour-xingyun-avatar\[([^\]]+)\]/)[1]}
const sdk=fs.readFileSync(path.join(root,'static/sdk/xmov-avatar-2.4.1-compatible.js'),'utf8')
const styleStart=sdk.indexOf('function getStyleStr('),styleEnd=sdk.indexOf('function updateCanvasXOffset(',styleStart)
const layoutStart=sdk.indexOf('e.setCanvasStyle=function')+'e.setCanvasStyle='.length,layoutEnd=sdk.indexOf(',e.setWalkConfig=',layoutStart)
assert.ok(styleStart>0&&styleEnd>styleStart&&layoutEnd>layoutStart)
const pageCss=fs.readFileSync(path.join(root,'pages/tour/tour.vue'),'utf8').match(/\.page \.guide-stage\{([^}]+)\}/)[1].replace(/([\d.]+)rpx/g,(_,n)=>Number(n)/2+'px')
const html='<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'body{margin:0}.guide-stage{'+pageCss+'}</style><div class="guide-stage"><div class="xingyun-stage" '+scope+'><div id="tour-xingyun-avatar" '+scope+'><canvas width="1080" height="1920"></canvas></div></div></div>'
const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(html)})
async function run(){await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser,page;const checks=[]
try{browser=await chromium.launch({executablePath:process.env.APP_QA_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});page=await browser.newPage()
await page.goto('http://127.0.0.1:'+server.address().port)
await page.evaluate(({style,layout})=>{const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');ctx.fillStyle='#6652bd';ctx.fillRect(350,350,380,1300);ctx.fillStyle='#23816b';ctx.beginPath();ctx.arc(540,240,170,0,Math.PI*2);ctx.fill();window.sdkLayout=new Function('getStyleStr','return ('+layout+')')(new Function('return ('+style+')')());window.sdkRenderer={canvas,options:{resourceManager:{getConfig:()=>({resolution:{width:1080,height:1920}})}}}}, {style:sdk.slice(styleStart,styleEnd),layout:sdk.slice(layoutStart,layoutEnd)})
for(const [width,height] of [[320,640],[390,844],[844,390],[768,1024]]){
 await page.setViewportSize({width,height})
 for(const [name,avatar] of [['center',{h_align:'center',v_align:'center',scale:'30vh',offset_x:0,offset_y:0}],['offset-left',{h_align:'left',v_align:'top',scale:1.4,offset_x:90,offset_y:-75}],['offset-right',{h_align:'right',v_align:'bottom',scale:.8,offset_x:-120,offset_y:80}]]){
  const result=await page.evaluate(avatar=>{const frame=document.querySelector('.guide-stage').getBoundingClientRect();sdkLayout.call(sdkRenderer,{container:{size:[frame.width,frame.height]},avatar});const stage=document.querySelector('.guide-stage').getBoundingClientRect(),host=document.getElementById('tour-xingyun-avatar').getBoundingClientRect(),canvas=document.querySelector('canvas'),r=canvas.getBoundingClientRect(),s=getComputedStyle(canvas);return{aspect:stage.width/stage.height,hostDelta:host.x+host.width/2-stage.x-stage.width/2,canvasDelta:r.x+r.width/2-stage.x-stage.width/2,top:r.y-stage.y,width:r.width-stage.width,height:r.height-stage.height,fit:s.objectFit,position:s.objectPosition,transform:s.transform}},avatar)
  assert.ok(Math.abs(result.aspect-16/9)<0.01,'avatar frame stays 16:9')
  assert.ok(Math.abs(result.hostDelta)<1,`avatar host must be centered at ${width}x${height}: `+JSON.stringify(result))
  assert.ok(Math.abs(result.canvasDelta)<1&&Math.abs(result.top)<1&&Math.abs(result.width)<1&&Math.abs(result.height)<1,'SDK offsets must not move or enlarge the display frame: '+JSON.stringify(result))
  assert.equal(result.fit,'contain');assert.equal(result.position,'50% 50%');assert.equal(result.transform,'none');checks.push({width,height,name})
 }
 await page.screenshot({path:path.join(out,width+'x'+height+'.png')})
}
fs.writeFileSync(path.join(out,scope?'compiled-result.json':'result.json'),JSON.stringify({passed:true,compiledNativeCss:!!scope,realSdkLayout:true,syntheticCanvas:true,realAvatarSession:false,phoneVerified:false,checks},null,2));console.log('Avatar layout checks passed across '+checks.length+' viewport/layout cases'+(scope?' with compiled native CSS':''))
}catch(e){if(page)await page.screenshot({path:path.join(out,'failure.png')});throw e}finally{await browser?.close();server.close()}}
run().catch(e=>{console.error(e);process.exitCode=1})
