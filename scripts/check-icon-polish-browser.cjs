// Actual production Web UI and real read-only backend data; station sessions
// are simulated so screenshot work never starts a paid avatar session.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict')
const {chromium}=require(require.resolve('playwright-core',{paths:[path.resolve(__dirname,'../app')]}))
const root=path.resolve(__dirname,'..'),dist=path.join(root,'frontend/dist'),out=path.join(root,'work_dirs/iphone-test/icon-polish/web')
fs.mkdirSync(out,{recursive:true})
const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.svg':'image/svg+xml','.woff2':'font/woff2'}
const api=/^\/(api|user|dashboard|upload|scenic-spots|knowledge-base|tour-routes|tour-session|tour-experience|service-stations|analytics|system|files|xingyun|avatar|digital-guide)(\/|$)/
const server=http.createServer((req,res)=>{
 if(api.test(req.url)&&!req.headers.accept?.includes('text/html')){
  const proxy=http.request({host:'127.0.0.1',port:18000,path:req.url,method:req.method,headers:{...req.headers,host:'127.0.0.1:18000'}},response=>{res.writeHead(response.statusCode,response.headers);response.pipe(res)})
  proxy.on('error',()=>{res.writeHead(502);res.end()});req.pipe(proxy);return
 }
 let file=path.resolve(dist,'.'+decodeURIComponent(new URL(req.url,'http://local').pathname))
 if(!file.startsWith(dist+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())file=path.join(dist,'index.html')
 res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res)
})
async function iconChecks(page){
 return page.locator('svg.ui-icon').evaluateAll(icons=>icons.filter(el=>el.checkVisibility()&&Number(getComputedStyle(el).opacity)>.05).map(el=>({name:el.dataset.icon,stroke:el.getAttribute('stroke'),fill:el.getAttribute('fill'),width:el.getBoundingClientRect().width,height:el.getBoundingClientRect().height})))
}
async function run(){
 const env=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(line=>line.includes('=')&&!line.startsWith('#')).map(line=>{const i=line.indexOf('=');return[line.slice(0,i),line.slice(i+1)]}))
 const login=await fetch('http://127.0.0.1:18000/user/login',{method:'POST',body:new URLSearchParams({username:env.ADMIN_USERNAME,password:env.ADMIN_PASSWORD})})
 assert.equal(login.status,200);const token=await login.json();assert.ok(token.access_token)
 const catalog=await(await fetch('http://127.0.0.1:18000/service-stations/public/summer-palace-east')).json()
 catalog.guide=null
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
 const base='http://127.0.0.1:'+server.address().port,browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true}),errors=[],checks=[]
 try{
  const admin=await browser.newContext({viewport:{width:1600,height:1000}})
  await admin.addInitScript(value=>localStorage.setItem('user-token',JSON.stringify({token:value,userInfo:{username:'admin',role:'admin'}})),token)
  const page=await admin.newPage();page.on('pageerror',error=>errors.push(error.message))
  for(const [route,name]of [['/home','admin-dashboard'],['/scenic-spot/list','admin-attractions']]){
   await page.goto(base+route,{waitUntil:'networkidle'});await page.locator('.layout-container').waitFor();await page.waitForTimeout(200)
   const icons=await iconChecks(page);assert.ok(icons.length>=6);for(const icon of icons){assert.equal(icon.stroke,'currentColor');assert.equal(icon.fill,'none');assert.ok(icon.width>=12&&icon.width<80,JSON.stringify(icon))}
   await page.screenshot({path:path.join(out,name+'.png')});checks.push({screen:name,icons:icons.length})
  }
  const toggle=page.locator('.collapse-trigger');await toggle.hover();await toggle.focus()
  const before=await page.locator('.collapse-icon .icon-current').getAttribute('data-icon');await toggle.click()
  const animations=await page.locator('.collapse-icon').evaluate(el=>el.getAnimations({subtree:true}).map(animation=>{animation.updatePlaybackRate(.1);return animation.playState}))
  await page.waitForTimeout(1800)
  assert.notEqual(await page.locator('.collapse-icon .icon-current').getAttribute('data-icon'),before)
  assert.equal(await page.locator('.collapse-icon .icon-current').evaluate(el=>getComputedStyle(el).opacity),'1')
  await page.locator('.collapse-trigger').click();await page.waitForTimeout(250)
  checks.push({screen:'admin-icon-states',keyboardFocus:true,hover:true,slowMotion:.1,animationsObserved:animations.length})
  const station=await browser.newContext({viewport:{width:1600,height:1000}})
  await station.route('**/service-stations/public/summer-palace-east',route=>route.fulfill({json:catalog}))
  await station.route('**/service-stations/public/summer-palace-east/heartbeat',route=>route.fulfill({json:{revision:catalog.station.revision,network_version:catalog.network_version,catalog_version:catalog.catalog_version}}))
  await station.route('**/service-stations/public/summer-palace-east/visits',route=>route.fulfill({json:{visit_id:'icons-preview',access_token:'icons-preview',expires_at:new Date(Date.now()+3600000).toISOString()}}))
  await station.route('**/service-stations/visits/icons-preview/**',route=>route.fulfill({json:{status:'waiting'}}))
  const terminal=await station.newPage();terminal.on('pageerror',error=>errors.push(error.message))
  await terminal.goto(base+'/station/summer-palace-east',{waitUntil:'networkidle'});await terminal.locator('.station-task-area').waitFor();await terminal.waitForTimeout(200)
  assert.ok((await iconChecks(terminal)).length>=4)
  await terminal.locator('.station-task-area').screenshot({path:path.join(out,'station-services.png')})
  await terminal.getByRole('button',{name:'景点与设施',exact:true}).first().click();await terminal.waitForTimeout(500)
  await terminal.locator('.station-task-area').screenshot({path:path.join(out,'station-attractions.png')});checks.push({screen:'station-services',catalog:true,cloudAvatarStarted:false,icons:(await iconChecks(terminal)).length})
  const disabled=await terminal.locator('.station-home-button').evaluate(button=>{button.disabled=true;const opacity=Number(getComputedStyle(button.querySelector('.ui-icon')).opacity);button.disabled=false;return opacity})
  assert.ok(disabled<1);checks.push({screen:'disabled-controls',simulated:true,iconOpacity:disabled})
  assert.deepEqual(errors,[])
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({passed:true,simulatedStationVisit:true,checks,errors},null,2));console.log(JSON.stringify({passed:true,checks}))
  await admin.close();await station.close()
 }finally{await browser.close();server.close()}
}
run().catch(error=>{console.error(error.message);process.exitCode=1;server.close()})
