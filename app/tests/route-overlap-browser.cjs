// Real Leaflet/SVG renderer; only base-map images are simulated. No phone claim.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict')
const {chromium}=require('playwright-core')
const root=path.resolve(__dirname,'..'),version=process.env.APP_QA_VERSION||'1.2.7',out=path.join(root,'unpackage/main-d31183c-'+version+'/overlap-results')
fs.mkdirSync(out,{recursive:true})
const html=`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}#map{width:390px;height:340px}</style><div id="map"></div><script type="module">
import {createRouteMap,loadRouteLibrary} from '/common/route-map-runtime.js';
await loadRouteLibrary(window,document,'/static/vendor/leaflet/');
const original=L.map;L.map=(...args)=>window.testMap=original(...args);
window.events=[];window.controller=createRouteMap(document.getElementById('map'),e=>events.push(e));window.ready=true;
</script>`
const server=http.createServer((req,res)=>{if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return}const name=new URL(req.url,'http://local').pathname,file=path.resolve(root,'.'+name);if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404).end();return}res.setHeader('Content-Type',name.endsWith('.js')?'application/javascript':name.endsWith('.css')?'text/css':'application/octet-stream');fs.createReadStream(file).pipe(res)})
const A={latitude:40,longitude:116},B={latitude:40.004,longitude:116.004},C={latitude:40.006,longitude:116.001},D={latitude:40.001,longitude:116.007}
const data={points:[A,B,C,D],markers:[],polyline:[{points:[A,B,C]},{points:[B,A,D]}],legIndexes:[0,2]}
async function run(){await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser,page
try{browser=await chromium.launch({executablePath:process.env.APP_QA_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});page=await browser.newPage({viewport:{width:390,height:640}})
await page.route('https://webrd01.is.autonavi.com/**',r=>r.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#f0f2f7"/></svg>'}))
await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForFunction(()=>window.ready)
const paint=async(activeLeg,original=false)=>page.evaluate(async args=>{window.payload={data:args.data,activeLeg:args.activeLeg,original:args.original,markerLabels:{},fitCounter:0,assetBase:'/static/vendor/leaflet/'};await controller.update(payload)}, {data,activeLeg,original})
const sharedPoint=()=>page.evaluate(()=>{const p=testMap.latLngToContainerPoint([40.002,116.002]),r=document.getElementById('map').getBoundingClientRect();return{x:r.x+p.x,y:r.y+p.y}})
for(const leg of [0,2,0,2,0]){
 await paint(leg);const point=await sharedPoint(),top=await page.evaluate(({x,y})=>document.elementsFromPoint(x,y).find(e=>e.tagName.toLowerCase()==='path')?.getAttribute('stroke'),point)
 assert.equal(top,'#513dbe','shared road must remain dark purple when leg '+leg+' is selected '+JSON.stringify(await page.locator('path').evaluateAll(xs=>xs.map(x=>({stroke:x.getAttribute('stroke'),d:x.getAttribute('d')})))))
 await page.mouse.click(point.x,point.y);assert.equal(await page.evaluate(()=>events.filter(e=>e.state==='leg').at(-1)?.index),leg,'overlap click preserves selected leg')
}
await page.screenshot({path:path.join(out,'selected-overlap.png')})
await paint(0,true);assert.equal(await page.locator('path[stroke="#8b96ac"]').count(),2)
await paint(0);const nonshared=await page.evaluate(()=>{const p=testMap.latLngToContainerPoint([40.0005,116.0035]),r=document.getElementById('map').getBoundingClientRect();return{x:r.x+p.x,y:r.y+p.y}});await page.mouse.click(nonshared.x,nonshared.y)
assert.equal(await page.evaluate(()=>events.filter(e=>e.state==='leg').at(-1)?.index),2,'non-overlap road can still select another leg')
fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({passed:true,realLeaflet:true,mockedTiles:true,phoneVerified:false,checks:['opposite-direction shared road remains dark','repeated selection preserves draw order','overlap click retains selected road','missing leg geometry retains correct index','before view stays gray','other leg remains selectable']},null,2));console.log('Overlapping route browser regression passed')
}catch(e){if(page)await page.screenshot({path:path.join(out,'failure.png')});throw e}finally{await browser?.close();server.close()}}
run().catch(e=>{console.error(e);process.exitCode=1})
