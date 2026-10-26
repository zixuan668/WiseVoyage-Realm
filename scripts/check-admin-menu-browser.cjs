// Actual compiled administrator UI, read-only backend requests, no business saves.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict')
const {chromium}=require(require.resolve('playwright-core',{paths:[path.resolve(__dirname,'../app')]}))
const root=path.resolve(__dirname,'..'),dist=path.join(root,'frontend/dist'),out=path.join(root,'work_dirs/admin-menu-20261026')
fs.mkdirSync(out,{recursive:true})
const api=/^\/(api|user|dashboard|upload|scenic-spots|knowledge-base|tour-routes|tour-session|tour-experience|service-stations|analytics|system|files|xingyun|avatar|digital-guide)(\/|$)/
const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.woff2':'font/woff2'}
const server=http.createServer((req,res)=>{
 if(api.test(req.url)&&!req.headers.accept?.includes('text/html')){
  const proxy=http.request({host:'127.0.0.1',port:18000,path:req.url,method:req.method,headers:{...req.headers,host:'127.0.0.1:18000'}},r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res)})
  proxy.on('error',()=>res.writeHead(502).end());req.pipe(proxy);return
 }
 let f=path.resolve(dist,'.'+decodeURIComponent(new URL(req.url,'http://local').pathname));if(!f.startsWith(dist+path.sep)||!fs.existsSync(f)||!fs.statSync(f).isFile())f=path.join(dist,'index.html')
 res.setHeader('Content-Type',mime[path.extname(f)]||'application/octet-stream');fs.createReadStream(f).pipe(res)
})
async function run(){
 const env=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(s=>s.includes('=')&&!s.startsWith('#')).map(s=>{const i=s.indexOf('=');return[s.slice(0,i),s.slice(i+1)]}))
 const login=await fetch('http://127.0.0.1:18000/user/login',{method:'POST',body:new URLSearchParams({username:env.ADMIN_USERNAME,password:env.ADMIN_PASSWORD})});assert.equal(login.status,200);const token=await login.json();assert.ok(token.access_token)
 const catalog=await(await fetch('http://127.0.0.1:18000/service-stations/public/summer-palace-east')).json();catalog.guide=null
 await new Promise(r=>server.listen(0,'127.0.0.1',r))
 const base='http://127.0.0.1:'+server.address().port,browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true})
 const errors=[],writes=[],checks=[]
 let page
 try{
  const context=await browser.newContext({viewport:{width:1600,height:1000}})
  await context.addInitScript(value=>{localStorage.setItem('user-token',JSON.stringify({token:value,userInfo:{username:'admin',role:'admin'}}));localStorage.setItem('zhiyou.app-language','zh')},token)
  await context.route('**/service-stations/public/summer-palace-east',r=>r.fulfill({json:catalog}))
  await context.route('**/service-stations/public/summer-palace-east/heartbeat',r=>r.fulfill({json:{revision:catalog.station.revision,network_version:catalog.network_version,catalog_version:catalog.catalog_version}}))
  await context.route('**/service-stations/public/summer-palace-east/visits',r=>r.fulfill({json:{visit_id:'admin-menu-qa',access_token:'admin-menu-qa',expires_at:new Date(Date.now()+3600000).toISOString()}}))
  await context.route('**/service-stations/visits/admin-menu-qa/**',r=>r.fulfill({json:{status:'waiting'}}))
  await context.route(/\/(?:api\/v1\/)?files\//,r=>{
   const pathname=new URL(r.request().url()).pathname,relative=decodeURIComponent(pathname.slice(pathname.indexOf('/files/')+7)),base=path.join(root,'static'),f=path.resolve(base,relative)
   if(f.startsWith(base+path.sep)&&fs.existsSync(f)&&fs.statSync(f).isFile())return r.fulfill({body:fs.readFileSync(f),contentType:mime[path.extname(f)]||'image/jpeg'})
   return r.continue()
  })
  page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',req=>{if(!['GET','HEAD','OPTIONS'].includes(req.method())&&!req.url().includes('/service-stations/'))writes.push({method:req.method(),path:new URL(req.url()).pathname})})
  await page.goto(base+'/scenic-spot/list',{waitUntil:'networkidle'});await page.locator('.menu-active-indicator.ready').waitFor();await page.waitForTimeout(350)
  await page.evaluate(()=>{window.adminRouter=document.getElementById('app').__vue_app__.config.globalProperties.$router;window.originalIndicator=document.querySelector('.menu-active-indicator')})
  const marker=page.locator('.menu-active-indicator')
  async function markerAligned(selector){
   await page.waitForFunction(selector=>{const a=document.querySelector('.menu-active-indicator')?.getBoundingClientRect(),b=document.querySelector(selector)?.getBoundingClientRect();return a&&b&&Math.abs(a.top-b.top)<2&&Math.abs(a.width-b.width)<2},selector,{timeout:5000})
  }
  await markerAligned('[data-admin-path="/scenic-spot/list"]');await page.screenshot({path:path.join(out,'admin-sidebar.png')})
  await page.evaluate(()=>{window.markerMotion=[];document.querySelector('.menu-active-indicator').addEventListener('transitionrun',event=>{if(event.propertyName==='transform'){window.markerMotion.push(performance.now());if(window.slowMarker)event.target.getAnimations().forEach(a=>a.updatePlaybackRate(.1))}});window.slowMarker=true})
  const initial=await marker.boundingBox();await page.locator('.enterprise-menu [data-admin-path="/knowledge/list"]').click();await page.waitForURL('**/knowledge/list');await page.waitForFunction(()=>window.markerMotion.length>0);await page.waitForTimeout(150)
  const halfway=await marker.boundingBox(),destination=await page.locator('.enterprise-menu [data-admin-path="/knowledge/list"]').boundingBox();assert.ok(Math.abs(halfway.y-destination.y)>1,'10% motion remains in flight');assert.ok(Math.abs(halfway.y-initial.y)<Math.abs(destination.y-initial.y)+1)
  await page.screenshot({path:path.join(out,'admin-highlight-motion.png')})
  await page.evaluate(()=>{window.slowMarker=false;document.querySelector('.menu-active-indicator').getAnimations().forEach(a=>a.updatePlaybackRate(1))})
  await page.locator('.enterprise-menu [data-admin-path="/stations"]').click();await page.waitForURL('**/stations');await markerAligned('[data-admin-path="/stations"]')
  assert.equal(await page.evaluate(()=>window.originalIndicator===document.querySelector('.menu-active-indicator')),true);checks.push('persistent active marker, 10% motion and interrupted navigation')
  for(const group of ['/personalization','/analytics','/scenic-spot']){
   await page.locator(`[data-admin-group="${group}"] > .el-sub-menu__title`).click();await page.waitForTimeout(360);assert.equal(await page.locator('.enterprise-menu .el-sub-menu.is-opened').count(),1)
  }
  checks.push('one in-place submenu group, following rows reflow')
  await page.locator('.enterprise-menu [data-admin-path="/knowledge/list"]').click();await page.waitForURL('**/knowledge/list');await markerAligned('[data-admin-path="/knowledge/list"]')
  await page.locator('[data-admin-group="/personalization"] > .el-sub-menu__title').click();await page.waitForTimeout(450);await markerAligned('[data-admin-group="/scenic-spot"] > .el-sub-menu__title')
  await page.locator('[data-admin-path="/tour-route/list"]').click();await page.waitForURL('**/tour-route/list');await markerAligned('[data-admin-path="/tour-route/list"]');await page.screenshot({path:path.join(out,'admin-route-menu.png')});checks.push('closed active group highlights its parent; route opens the correct group')
  await page.locator('.collapse-trigger').click();await page.waitForTimeout(400);assert.ok((await page.locator('.layout-aside').boundingBox()).width<74);await markerAligned('[data-admin-group="/personalization"] > .el-sub-menu__title')
  await page.locator('.collapse-trigger').click();await page.waitForTimeout(400);await markerAligned('[data-admin-path="/tour-route/list"]');checks.push('expanded and collapsed navigation')
  await page.evaluate(async()=>{await window.adminRouter.push('/scenic-spot/3/edit')});await markerAligned('[data-admin-path="/scenic-spot/list"]');checks.push('edit page keeps its parent menu highlighted')
  await page.evaluate(async()=>{await window.adminRouter.push('/scenic-spot/list')});await page.locator('.topbar-actions').getByRole('button',{name:'English',exact:true}).click();await page.waitForTimeout(350);await markerAligned('[data-admin-path="/scenic-spot/list"]');await page.screenshot({path:path.join(out,'admin-sidebar-en.png')})
  await page.setViewportSize({width:900,height:900});await page.waitForTimeout(400);assert.ok((await page.locator('.layout-aside').boundingBox()).width<74);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);await page.screenshot({path:path.join(out,'admin-narrow.png')});checks.push('English labels, wrapping and narrow collapsed sidebar')
  await page.emulateMedia({reducedMotion:'reduce'});assert.ok(await marker.evaluate(el=>parseFloat(getComputedStyle(el).transitionDuration)<.02));checks.push('reduced motion')
  assert.equal(await page.locator('#admin-command-trigger').count(),0);assert.equal(await page.locator('.admin-command-panel').count(),0);checks.push('no command search or added header UI')
  await page.evaluate(()=>window.adminRouter.push('/station/summer-palace-east'));await page.locator('.station-task-area').waitFor();assert.equal(await page.locator('.admin-navigation').count(),0);checks.push('station has no new sidebar UI')
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
  fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({passed:true,checks,errors,businessWrites:writes,stationVisitSimulated:true},null,2));console.log(JSON.stringify({passed:true,checks}))
 }catch(e){if(page)await page.screenshot({path:path.join(out,'failure.png')});throw e}finally{await browser.close();server.close()}
}
run().catch(e=>{console.error(e);server.close();process.exitCode=1})
