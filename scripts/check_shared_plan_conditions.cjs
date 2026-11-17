const {chromium}=require('playwright-core'),assert=require('node:assert/strict')
async function main(){
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true})
 try{
  const page=await browser.newPage({viewport:{width:412,height:915}})
  const origin='http://127.0.0.1:5173'
  let saved=page.waitForResponse(r=>r.url().includes('/scenic-settings')&&r.request().method()==='PUT'&&r.status()===200)
  await page.goto(origin+'/app/scenic?view=plan&spotIds=1&elderly=0&children=0&avoidSteps=0&startArea=east&endArea=auto')
  await saved
  await page.locator('.exit-trigger').click()
  saved=page.waitForResponse(r=>r.url().includes('/scenic-settings')&&r.request().method()==='PUT'&&r.status()===200)
  await page.getByRole('dialog',{name:'选择离园出口'}).getByRole('button',{name:'东宫门',exact:true}).click()
  await saved
  await page.waitForFunction(()=>document.querySelector('.exit-trigger')?.textContent.includes('东宫门'))
  const settings=await(await page.request.get(origin+'/tour-experience/scenic-settings')).json()
  assert.equal(settings.end_area,'east')
  console.log('PASS changing exit persists and updates UI')
  await page.route('**/tour-experience/scenic-settings',route=>route.request().method()==='GET'
   ?route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'conditions unavailable'})}):route.continue())
  await page.reload()
  await page.locator('.route-empty').waitFor()
  assert.equal(await page.locator('.family-row').count(),0)
  assert.ok((await page.locator('.route-empty').innerText()).includes('路线加载失败'))
  console.log('PASS failed conditions show an error instead of a default route')
 }finally{await browser.close()}
}
main().catch(error=>{console.error(error.message);process.exitCode=1})
