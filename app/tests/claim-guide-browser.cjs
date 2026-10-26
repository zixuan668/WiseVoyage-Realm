// Compiled App pickup flow, mocked API; no real pickup codes or paid avatar sessions.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict'),{chromium}=require('playwright-core')
const root=path.resolve(__dirname,'../..'),out=path.resolve(process.env.APP_QA_OUT||path.join(root,'work_dirs/iphone-test/app-claim-guide-20261026')),dist=path.resolve(process.env.APP_QA_DIST||path.join(out,'h5'))
fs.mkdirSync(out,{recursive:true})
const fixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/public-catalog.json'),'utf8'))
const spots=fixtures.spots.data.spot_list.slice(0,4),guides=fixtures.guides.data.guide_list
const snapshot={guide:{guide_id:1},route:{stops:spots,total_minutes:91},preferences:{language:'zh'}}
const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'}
const server=http.createServer((req,res)=>{let file=path.resolve(dist,'.'+new URL(req.url,'http://local').pathname);if(!file.startsWith(dist+path.sep)){res.writeHead(403).end();return}if(!fs.existsSync(file)||!fs.statSync(file).isFile())file=path.join(dist,'index.html');res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res)})
const ok=data=>({success:true,data}),checks=[],errors=[]
async function run(){
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true})
 try{
  for(const width of (process.env.CLAIM_QA_QUICK?[393]:[320,393,430]))for(const lang of (process.env.CLAIM_QA_QUICK?['zh']:['zh','en'])){
   const context=await browser.newContext({viewport:{width,height:852},isMobile:true,hasTouch:true})
   await context.addInitScript(({lang})=>{for(const[k,data]of Object.entries({'zhiyou.onboarding.v1.completed':true,'zhiyou.app-language':lang,token:'qa-token',login_provider:'password',user_id:17,username:'QA'})){if(localStorage.getItem('qa-no-login')==='1'&&['token','login_provider'].includes(k))continue;localStorage.setItem(k,JSON.stringify({type:typeof data,data}))}},{lang})
   await context.addInitScript(()=>window.addEventListener('unhandledrejection',event=>console.log('QA rejection',JSON.stringify(event.reason))))
   const page=await context.newPage();page.on('console',message=>{if(message.text().startsWith('QA rejection'))console.log(message.text())});page.on('pageerror',e=>errors.push({message:e.message,stack:e.stack,url:page.url()}));let receives=[],rejectGuide=false,empty=false
   await page.route('**/api/v1/**',async route=>{
    const req=route.request(),p=new URL(req.url()).pathname.replace('/api/v1','');let data={}
    if(p.startsWith('/files/')){const base=path.join(root,'static'),file=path.resolve(base,decodeURIComponent(p.slice(7)));if(file.startsWith(base+path.sep)&&fs.existsSync(file)&&fs.statSync(file).isFile())return route.fulfill({body:fs.readFileSync(file),contentType:types[path.extname(file)]||'image/jpeg'});return route.fulfill({status:404,body:''})}
    if(p==='/service-stations/claim/preview-app')return route.fulfill({contentType:'application/json',body:JSON.stringify({snapshot,session_id:null})})
    if(p==='/service-stations/claim/receive-app'){
     const body=req.postDataJSON();receives.push(body)
     if(rejectGuide)return route.fulfill({status:422,contentType:'application/json',body:JSON.stringify({detail:'所选数字人暂不可用，请重新选择'})})
     return route.fulfill({contentType:'application/json',body:JSON.stringify({session_id:77,avatar_access_token:'test-scoped-77'})})
    }
    if(p==='/user/login')return route.fulfill({contentType:'application/json',body:JSON.stringify({access_token:'new-qa-token',token_type:'bearer'})})
    if(p==='/user/me')data={user_id:17,username:'QA'}
    if(p==='/tour-session/guides')data={guide_list:empty?[]:guides}
    if(p==='/tour-session/spots')data={spot_list:spots}
    if(p==='/tour-session/live-info/77')data={session_id:77,name:'领取的路线',guide_info:{...guides.find(g=>g.guide_id===receives.at(-1)?.guide_id),render_mode:'audio'},visitor_preferences:JSON.stringify({spot_ids:spots.map(s=>s.spot_id)}),live_status:1,conversation:[],current_spot_index:0,start_time:'2026-10-26T10:00:00'}
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(ok(data))})
   })
   const open=async suffix=>{await page.goto('http://127.0.0.1:'+server.address().port+'/index.html?case='+Date.now()+'#/pages/claim/claim?claim=ABCD2345EFGH'+(suffix||''),{waitUntil:'networkidle'})}
   await open();await page.locator('.claim-guide').first().waitFor();assert.equal(await page.locator('.claim-guide.selected').count(),0);assert.equal(receives.length,0)
   await page.locator('.claim-primary').evaluate(el=>el.click());assert.equal(receives.length,0)
   await page.screenshot({path:path.join(out,'choose-'+lang+'-'+width+'.png')})
   await page.locator('.claim-guide').nth(1).click();assert.equal(await page.locator('.claim-guide.selected').count(),1)
   assert.equal(await page.locator('.claim-guide-name').first().evaluate(el=>getComputedStyle(el).backgroundColor),'rgba(0, 0, 0, 0)')
   assert.equal(await page.locator('.claim-guide-name').first().evaluate(el=>getComputedStyle(el).color),'rgb(0, 0, 0)')
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
   await page.screenshot({path:path.join(out,'selected-'+lang+'-'+width+'.png')})
   await page.locator('.claim-primary').evaluate(el=>{el.click();el.click()});
   try{await page.waitForURL(/pages\/tour\/tour\?sessionId=77/,{timeout:7000})}catch(e){console.error('Pickup diagnostic',JSON.stringify({width,lang,url:page.url(),receives,text:await page.locator('body').innerText()}));await page.screenshot({path:path.join(out,'failure.png')});throw e}
   assert.equal(receives.length,1);assert.equal(receives[0].guide_id,guides[1].guide_id);checks.push({width,lang,explicitChoice:true,exactGuide:true,noDuplicatePickup:true})
   if(width===393&&lang==='zh'){
    receives=[];rejectGuide=true;await open();await page.locator('.claim-guide').nth(1).click();await page.locator('.claim-primary').click();await page.locator('.claim-error').waitFor();assert.ok(page.url().includes('/pages/claim/claim'));rejectGuide=false
    empty=true;await open();await page.locator('.claim-empty').waitFor();assert.equal(receives.length,1);empty=false;await page.locator('.claim-empty uni-button').click();await page.locator('.claim-guide').first().waitFor();assert.equal(await page.locator('.claim-guide.selected').count(),0)
    await page.evaluate(()=>{localStorage.setItem('qa-no-login','1');localStorage.removeItem('token');localStorage.removeItem('login_provider')});await open();await page.waitForURL(/pages\/auth\/auth/)
    const inputs=page.locator('.nickname-input input');await inputs.nth(0).fill('QA');await inputs.nth(1).fill('mock-password');await page.locator('.primary').click();await page.locator('.claim-guide').first().waitFor();assert.equal(await page.locator('.claim-guide.selected').count(),0);assert.equal(receives.length,1)
    checks.push({unavailableGuide:true,emptyGuidesRetry:true,loginContinuation:true})
   }
   await context.close()
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({passed:true,mockedBackend:true,iPhoneVerified:false,checks,errors},null,2));console.log('Claim guide selection passed six language/viewport cases and failure/login states')
 }finally{await browser.close();server.close()}
}
run().catch(e=>{console.error(e);server.close();process.exitCode=1})
