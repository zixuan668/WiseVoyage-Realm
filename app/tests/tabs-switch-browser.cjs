// Runs the compiled uni-app pager with mocked read-only API responses.
// Browser rendering checks do not substitute for iPhone frame-rate testing.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict')
const {chromium}=require('playwright-core')
const base=path.resolve(__dirname,'../../work_dirs/iphone-test/tab-switch')
const out=path.resolve(process.env.APP_QA_OUT||base),dir=path.resolve(process.env.APP_QA_DIST||path.join(base,'h5'))
fs.mkdirSync(out,{recursive:true})
const fixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/public-catalog.json'),'utf8'))
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2','.ttf':'font/ttf'}
const server=http.createServer((req,res)=>{
 const file=path.resolve(dir,'.'+decodeURIComponent(req.url.split('?')[0]||'/'))
 if(!file.startsWith(dir+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end();return}
 res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res)
})
function snapshot(){
 let vm=document.querySelector('.tabs-shell').__vueParentComponent
 while(vm&&!('pagerCurrent' in vm.proxy))vm=vm.parent
 if(!vm)throw Error('Pager instance not found')
 window.testPager=vm.proxy
 const panels=[...document.querySelectorAll('.panel-slot')].map(el=>{const r=el.getBoundingClientRect();return {left:r.left,width:r.width}})
 return {current:vm.proxy.current,target:vm.proxy.pagerCurrent,switching:vm.proxy.switching,panels,width:innerWidth}
}
async function run(){
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true})
 const checks=[]
 try{
  for(const width of [320,393,430]){
   const context=await browser.newContext({viewport:{width,height:852},hasTouch:true,isMobile:true})
   const page=await context.newPage(),errors=[]
   page.on('pageerror',error=>errors.push(error.message))
   await page.addInitScript(()=>{
    for(const [key,data] of Object.entries({token:'browser-layout-test',user_id:17,username:'测试用户',language:'zh'}))localStorage.setItem(key,JSON.stringify({type:typeof data,data}))
   })
   await page.route('**/api/v1/**',route=>{
    const pathname=new URL(route.request().url()).pathname
    if(pathname.startsWith('/api/v1/files/')){
     const staticRoot=path.resolve(__dirname,'../../static'),file=path.resolve(staticRoot,decodeURIComponent(pathname.slice('/api/v1/files/'.length)))
     if(file.startsWith(staticRoot+path.sep)&&fs.existsSync(file)&&fs.statSync(file).isFile())return route.fulfill({status:200,contentType:types[path.extname(file)]||'image/jpeg',body:fs.readFileSync(file)})
     return route.fulfill({status:404,body:''})
    }
    let data={success:true,data:{}}
    for(const key of ['spots','guides','routes'])if(pathname.endsWith('/tour-session/'+key))data=fixtures[key]
    if(pathname.endsWith('/user/me'))data={success:true,data:{username:'测试用户',user_id:17,user_no:'TEST17'}}
    route.fulfill({status:200,contentType:'application/json',headers:{'Access-Control-Allow-Origin':'*'},body:JSON.stringify(data)})
   })
   await page.goto('http://127.0.0.1:'+server.address().port+'/index.html#/pages/tabs/tabs')
   await page.waitForSelector('.tabs-shell');await page.waitForTimeout(500)
   await page.evaluate(snapshot)
   async function settled(index){
    try {
     await page.waitForFunction(index=>window.testPager.current===index&&!window.testPager.switching,index,{timeout:5000})
    } catch (error) {
     console.error('Pager diagnostic',JSON.stringify({expected:index,state:await page.evaluate(snapshot),routeBox:await page.locator('.route-carousel').boundingBox()}))
     await page.screenshot({path:path.join(out,'failure-'+width+'.png')})
     throw error
    }
    const result=await page.evaluate(snapshot)
    assert.ok(Math.abs(result.panels[index].left)<1,'selected page aligns to the viewport: '+JSON.stringify(result))
    assert.ok(Math.abs(result.panels[index].width-width)<1,'page fills exactly one viewport')
   }
   async function select(index){await page.evaluate(i=>window.testPager.selectTab(i),index);await settled(index)}
   await settled(0)
   const cdp=await context.newCDPSession(page)
   async function swipe(x1,x2,y){
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:x1,y}]})
    for(let i=1;i<=8;i++){await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x1+(x2-x1)*i/8,y}]});await page.waitForTimeout(14)}
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
    await page.waitForTimeout(350)
   }
   const routeBox=await page.locator('.route-carousel').boundingBox()
   if(routeBox){
    // Keep the carousel gesture inside its content, clear of the 44px arrow buttons.
    const startX=routeBox.x+routeBox.width*.7,endX=routeBox.x+routeBox.width*.3,y=routeBox.y+routeBox.height*.6
    assert.ok(await page.evaluate(({x,y})=>!!document.elementFromPoint(x,y)?.closest('.route-carousel'),{x:startX,y}),'nested swipe starts on carousel content')
    await swipe(startX,endX,y);await settled(0)
   }
   await select(2);await page.screenshot({path:path.join(out,'mine-'+width+'.png')});await select(0)
   assert.equal(await page.locator('.route-carousel').count(),1,'cached route banner remains mounted')
   await page.evaluate(()=>{window.testPager.selectTab(2);window.testPager.selectTab(1);window.testPager.selectTab(0)})
   await settled(0)
   await page.evaluate(()=>document.querySelectorAll('.dock-item')[2].click())
   await page.waitForFunction(()=>window.testPager.pagerCurrent===2)
   await page.evaluate(()=>{document.querySelectorAll('.dock-item')[0].click();document.querySelectorAll('.dock-item')[2].click()})
   await settled(2);await select(0)
   await swipe(width*.85,width*.15,550);await settled(1)
   await page.screenshot({path:path.join(out,'ai-'+width+'.png')})
   await swipe(width*.15,width*.85,550);await settled(0)
   await page.screenshot({path:path.join(out,'pager-'+width+'.png')})
   assert.deepEqual(errors,[])
   checks.push({width,rapidTaps:true,nestedCarousel:true,swipeBack:true});await context.close()
  }
  fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({passed:true,iPhoneVerified:false,checks},null,2))
  console.log('Compiled tab pager passed '+checks.length+' phone viewport cases')
 }finally{await browser.close();server.close()}
}
run().catch(error=>{console.error(error);process.exitCode=1;server.close()})
