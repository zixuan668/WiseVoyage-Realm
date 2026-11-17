const assert = require('node:assert/strict')
const fs = require('node:fs')
const http = require('node:http')
const path = require('node:path')
const { chromium } = require('playwright-core')

const root = path.resolve(__dirname, '..')
const dist = path.resolve(process.env.APP_QA_DIST || path.join(root,'unpackage/wander-qa/browser'))
const output = path.join(root,'unpackage/wander-qa/screens')
const spots = [
  { spot_id:1, spot_name:'铜牛', tags:'湖景;亲子', city:'北京', latitude:39.9965, longitude:116.2738 },
  { spot_id:2, spot_name:'长廊', tags:'古建;临湖', city:'北京', latitude:39.9966, longitude:116.2659 },
  { spot_id:3, spot_name:'昆明湖', tags:'湖景;摄影', city:'北京', latitude:39.9955, longitude:116.2733 },
  { spot_id:4, spot_name:'仁寿殿', tags:'古建', city:'北京', latitude:39.997, longitude:116.274 },
]
const guide = { guide_id:2, name:'测试导游', render_mode:'audio' }
const route = { route_id:1, city:'北京', name:'皇家园林经典文化线', spot_ids:[1,2,3], estimated_time_minutes:55 }
const entry = [40.0009937,116.268051]
const coords = id => { const s=spots.find(spot=>spot.spot_id===id); return [s.latitude,s.longitude] }
const overviewFor = (ids, options) => ({
  complete:true, walking_meters:460, total_minutes:24,
  stops:ids.map(id=>{const s=spots.find(spot=>spot.spot_id===id);return {...s,access_latitude:s.latitude,access_longitude:s.longitude}}),
  entry_leg:options.start_area==='north'?{available:true,geometry:[entry,coords(ids[0])],meters:140}:null,
  entry_anchor:options.start_area==='north'?{label:'北宫门',latitude:entry[0],longitude:entry[1]}:null,
  legs:ids.slice(1).map((id,i)=>({available:true,from_id:ids[i],to_id:id,geometry:[coords(ids[i]),coords(id)],meters:120})),
})
const types = { '.js':'application/javascript','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2' }

async function run() {
  fs.mkdirSync(output,{recursive:true})
  const server=http.createServer((req,res)=>{
    const file=path.resolve(dist,'.'+new URL(req.url,'http://localhost').pathname)
    if(file!==dist && !file.startsWith(dist+path.sep))return res.writeHead(403).end()
    const target=fs.statSync(file,{throwIfNoEntry:false})?.isFile()?file:path.join(dist,'index.html')
    res.setHeader('Content-Type',types[path.extname(target)]||'text/html')
    fs.createReadStream(target).pipe(res)
  })
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
  let browser,page
  const calls=[],errors=[]
  try {
    browser=await chromium.launch({executablePath:process.env.APP_QA_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true})
    const context=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true,
      permissions:['geolocation'],geolocation:{latitude:entry[0],longitude:entry[1],accuracy:8}})
    await context.addInitScript(()=>{
      localStorage.setItem('zhiyou.onboarding.v1.completed','true')
      localStorage.setItem('token',JSON.stringify({type:'string',data:'fixture-token'}))
      localStorage.setItem('login_provider',JSON.stringify({type:'string',data:'password'}))
    })
    page=await context.newPage()
    page.on('pageerror',error=>errors.push(error.stack || error.message))
    await context.route('https://tile.openstreetmap.org/**',r=>r.abort())
    let ids=[], preferences='', activeOverview=null, sessionPlanning=null
    await context.route('**/api/v1/**',async req=>{
      const request=req.request(),url=new URL(request.url()),endpoint=url.pathname.replace('/api/v1','')
      const options=request.postDataJSON()||{}
      calls.push({endpoint,options})
      let data={}
      if(endpoint==='/user/login')return req.fulfill({json:{access_token:'fixture-token',token_type:'bearer'}})
      if(endpoint==='/tour-session/routes')data={route_list:[route]}
      if(endpoint==='/tour-session/spots')data={spot_list:spots}
      if(endpoint==='/tour-session/guides')data={guide_list:[guide]}
      if(endpoint==='/tour-routes/recommend'){
        const candidates=[[1,2,3],[2,3],[3]]
        const spotIds=candidates.find(candidate=>candidate.every(id=>!options.excluded_spot_ids?.includes(id)))||[]
        data={spot_ids:spotIds,name:'沿湖路线',score_details:spotIds.slice(0,1).map(spot_id=>({spot_id,reason:'沿湖步道适合观水'}))}
      }
      if(endpoint==='/tour-experience/route-preview')activeOverview=data=overviewFor(options.spot_ids,options)
      if(endpoint==='/tour-experience/optimize-order')data={spot_ids:options.spot_ids.slice().reverse()}
      if(endpoint==='/tour-session/visitor-create'){
        ids=JSON.parse(url.searchParams.get('spot_ids'));preferences=url.searchParams.get('visitor_preferences')
        sessionPlanning=JSON.parse(url.searchParams.get('planning'))
        data={session_id:77}
      }
      if(endpoint==='/tour-session/live-info/77')data={live_status:1,guide_info:guide,route_overview:activeOverview,route_spots:spots,
        visitor_preferences:JSON.stringify({spot_ids:ids,preferences:preferences.split(',')}),conversation:[]}
      if(endpoint==='/avatar/capabilities/2')data={realistic:{ready:false}}
      await req.fulfill({status:200,json:{success:true,code:0,data},headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*'}})
    })
    const tap=label=>page.getByText(label,{exact:true}).last().locator('xpath=ancestor-or-self::uni-button[1]').tap()
    const expect=label=>page.getByText(label,{exact:true}).last().waitFor()
    const openFromPark=()=>page.locator('.park-actions').getByText('随心逛',{exact:true}).locator('xpath=ancestor::uni-button[1]').tap()
    const shot=async name=>{
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
      await page.screenshot({path:path.join(output,name+'.png')})
    }
    await page.goto('http://127.0.0.1:'+server.address().port+'/#/pages/tabs/tabs')
    await page.locator('.park-route').first().tap()
    await expect('选择此路线')
    await page.getByRole('button',{name:'返回'}).tap()
    await openFromPark()
    await expect('这次想怎么逛？')
    assert.ok(await page.evaluate(async()=>((await document.fonts.load('400 16px "Source Han Sans CN"','随心逛'))[0]?.status==='loaded')))
    await shot('01-逛法')
    await tap('沿湖看水');await tap('选择游览时长')
    await expect('半小时');await expect('1 小时');await expect('2 小时');await shot('06-选择时间')
    assert.equal(await page.locator('.stage-time uni-picker').count(),0)
    await tap('半小时');await expect('游览时长')
    assert.equal(await page.locator('#wander-time-30').getAttribute('aria-pressed'),'true')
    assert.ok(!calls.some(c=>c.endpoint==='/tour-routes/recommend'))
    await tap('下一步');await expect('推荐路线')
    assert.equal(await page.locator('.stage-settings').count(),0)
    assert.equal(await page.locator('.stage-recommended').getByText('查看路线详情',{exact:true}).count(),0)
    await page.locator('.wander-road .wander-context-label').first().waitFor({state:'attached'})
    const mappedStops=await page.locator('.wander-road .route-order-marker').evaluateAll(pins=>pins.map(pin=>pin.title))
    assert.deepEqual(mappedStops,['第 1 站','第 2 站','第 3 站'])
    await page.setViewportSize({width:390,height:660})
    const mapBounds=await page.locator('.wander-map-frame').boundingBox()
    const cdp=await context.newCDPSession(page)
    const x=Math.round(mapBounds.x+mapBounds.width/2),y=Math.round(mapBounds.y+mapBounds.height*.8)
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]})
    for(let offset=20;offset<=180;offset+=20)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:y-offset}]})
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]})
    await page.waitForFunction(()=>Array.from(document.querySelectorAll('.wander-scroll .uni-scroll-view')).some(scroll=>scroll.scrollTop>24))
    await cdp.detach()
    await page.setViewportSize({width:390,height:844})
    assert.equal(await page.locator('.candidate-option').count(),3)
    assert.match(await page.locator('.candidate-option').first().innerText(),/经过铜牛，.*沿湖步道适合观水。/)
    assert.ok((await page.locator('.candidate-option').allInnerTexts()).every(text=>text.endsWith('。')))
    const firstRecommendation=calls.find(c=>c.endpoint==='/tour-routes/recommend').options
    assert.deepEqual(firstRecommendation.preferences,['nature'])
    assert.equal(firstRecommendation.time_budget_minutes,30)
    assert.equal(firstRecommendation.start_area,'north')
    assert.equal(firstRecommendation.pace,'standard')
    assert.ok(firstRecommendation.excluded_spot_ids.includes(4))
    const candidatePreviews=calls.slice(calls.findIndex(c=>c.endpoint==='/tour-routes/recommend')).filter(c=>c.endpoint.endsWith('route-preview'))
    assert.equal(candidatePreviews.length,3)
    assert.ok(candidatePreviews.every(c=>!c.options.avoid_steps && c.options.start_area==='north'),JSON.stringify(candidatePreviews))
    await tap('台阶图层')
    await page.locator('.wander-road path[stroke="#b84758"]').first().waitFor({state:'attached'})
    await shot('07-推荐路线')
    await tap('选这条路线');await expect('路线结果');await shot('03-路线结果')
    assert.equal(await page.locator('.stage-preview').getByText('地图步行',{exact:true}).count(),0)
    await page.getByRole('button',{name:'增加人数'}).tap()
    await tap('有老人');await expect('路线结果')
    assert.equal(await page.locator('.stage-preview').getByText('调整景点',{exact:true}).count(),0)
    assert.equal(await page.getByRole('button',{name:'加入路线'}).count(),0)
    const confirmed=[1,2,3]
    assert.deepEqual(calls.findLast(c=>c.endpoint.endsWith('route-preview')).options.spot_ids,confirmed)
    await tap('开始游览');await expect('选择伴游')
    assert.match(await page.locator('.companion-summary').innerText(),/2 人[\s\S]*有老人[\s\S]*避开台阶/)
    assert.equal(calls.some(c=>c.endpoint.endsWith('visitor-create')),false)
    await shot('08-选择伴游')
    await page.locator('.planning-back').tap();await expect('路线结果');await expect('开始游览')
    await tap('开始游览');await expect('选择伴游')
    await page.locator('.guide-grid .guide-card').tap()
    await tap('确认伴游');await page.locator('.bottom-bar').waitFor()
    assert.deepEqual(ids,confirmed)
    assert.ok(preferences.includes('app-party-senior'))
    assert.equal(sessionPlanning.pace,'relaxed')
    assert.equal(sessionPlanning.avoid_steps,true)
    assert.equal(sessionPlanning.start_area,'north')
    await page.locator('.msg-input textarea').fill('调整路线')
    await page.locator('.send-btn:not(.disabled)').tap()
    await expect('游览开始后，路线已锁定')
    assert.ok(!calls.some(call=>call.endpoint.includes('tour-adaptive')))
    await page.goto('http://127.0.0.1:'+server.address().port+'/#/pages/tabs/tabs')
    await page.reload()
    await openFromPark()
    await tap('随机盲盒');await tap('选择游览时长');await tap('1 小时');await tap('下一步');await expect('盲盒路线预览')
    const names=await page.locator('.candidate-option > uni-view:nth-child(2) uni-text:first-child').allInnerTexts()
    assert.deepEqual(names,['临湖','古建','摄影点'])
    assert.doesNotMatch(await page.locator('.wander-recommendation').innerText(),/先保留目的地|24 分钟|查看路线详情/)
    assert.equal(await page.locator('.wander-map-frame').count(),0)
    assert.equal(await page.getByText('台阶图层',{exact:true}).count(),0)
    await shot('09-盲盒预览')
    await page.locator('.candidate-option').first().tap();await expect('路线结果')
    await page.locator('.wander-road path[stroke="#513dbe"]').first().waitFor({state:'attached'})
    assert.equal(await page.locator('.wander-road path[fill="#bddae3"]').count(),1)
    assert.equal(await page.locator('.wander-road path[fill="#d9d3c8"]').count(),1)
    assert.ok((await page.locator('.wander-road .route-order-marker').evaluateAll(pins=>pins.map(pin=>pin.title))).every(title=>/^第 \d+ 站$/.test(title)))
    assert.ok(!(await page.locator('.wander-road .route-order-marker').allInnerTexts()).includes('3'))
    const mapCard=await page.locator('.wander-road .route-dom-map').evaluate(element=>({
      height:element.getBoundingClientRect().height,radius:parseFloat(getComputedStyle(element).borderRadius)
    }))
    assert.ok(mapCard.height>=150 && mapCard.height<=195)
    assert.ok(mapCard.radius>=16)
    await shot('10-盲盒结果')
    assert.deepEqual(errors,[])
    console.log('Wander browser flow and companion handoff passed with simulated service.')
  } catch(error) {
    if(page){await page.screenshot({path:path.join(output,'failure.png')});console.error(await page.locator('body').innerText())}
    throw error
  } finally { await browser?.close();server.close() }
}
run().catch(error=>{console.error(error);process.exitCode=1})
