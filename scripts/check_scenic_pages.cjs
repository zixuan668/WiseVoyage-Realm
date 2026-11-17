// Real backend/browser checks. Does not create scenic selections or cloud sessions.
const {chromium}=require('playwright-core')
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict')
async function main(){
 const origin='http://127.0.0.1:5173',backend='http://127.0.0.1:18000'
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true})
 const checks=[],errors=[]
 const record=message=>{checks.push(message);console.log(message)}
 try{
  const page=await browser.newPage({viewport:{width:412,height:915}})
  page.on('pageerror',e=>errors.push(e.message))
  const catalog=await(await fetch(backend+'/tour-experience/scenic-catalog')).json()
  const covers=JSON.parse(fs.readFileSync(path.join(__dirname,'../frontend/src/data/scenicCoverImages.json'),'utf8'))
  for(const spot of catalog){
   const cover=covers[spot.name]?.url;assert.ok(cover,'missing cover '+spot.name)
   for(const url of [origin+cover,backend+'/api/v1/files'+cover]){
    const res=await fetch(url);assert.equal(res.status,200,url);assert.ok(res.headers.get('content-type')?.startsWith('image/'),url)
   }
  }
  record('17 real scenic cover images: frontend and backend return image content')
  await page.goto(origin+'/app/scenic/1');await page.locator('.spot-strip').waitFor()
  await page.getByRole('button',{name:'全部景点',exact:true}).click()
  await page.locator('.catalog-panel').waitFor()
  assert.equal(await page.locator('.catalog-grid button').count(),catalog.length)
  await page.getByRole('button',{name:'返回',exact:true}).click()
  await page.locator('.catalog-panel').waitFor({state:'detached'})
  assert.equal(new URL(page.url()).searchParams.has('view'),false)
  record('all scenic spots panel returns to scenic introduction')
  await page.getByRole('button',{name:'去规划',exact:true}).click()
  await page.locator('.route-plan-panel').waitFor()
  await page.getByRole('button',{name:'返回',exact:true}).click()
  await page.locator('.route-plan-panel').waitFor({state:'detached'})
  record('route plan returns to scenic introduction')
  await page.getByRole('button',{name:'长廊',exact:true}).click()
  await page.waitForURL('**/app/scenic/2')
  assert.equal(await page.locator('.intro__title').innerText(),'长廊')
  record('switching scenic spots returns correct database content')
  await page.goto(origin+'/login');await page.goto(origin+'/app/scenic/1')
  await page.locator('.spot-strip').waitFor()
  await page.getByRole('button',{name:'返回',exact:true}).click()
  await page.waitForURL('**/login')
  record('browser return button restores previous page')
  assert.deepEqual(errors,[])
  const report={checked_at:new Date().toISOString(),catalog_count:catalog.length,checks,errors,native_device_verified:false}
  fs.mkdirSync(path.join(__dirname,'../outputs'),{recursive:true})
  fs.writeFileSync(path.join(__dirname,'../outputs/scenic-page-checks.json'),JSON.stringify(report,null,2))
  console.log(JSON.stringify(report,null,2))
 }finally{await browser.close()}
}
main().catch(e=>{console.error(e.message);process.exitCode=1})
