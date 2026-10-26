// Real tour CSS with a native-style full-width scroll host; simulated messages.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{chromium}=require('playwright-core')
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'pages/tour/tour.vue'),'utf8')
const css=source.match(/<style scoped>([\s\S]*?)<\/style>/)[1],globalCss=fs.readFileSync(path.join(root,'common/soft-ui.css'),'utf8')
const out=path.resolve(root,'../work_dirs/iphone-test/chat-layout');fs.mkdirSync(out,{recursive:true})
async function run(){
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true})
 const page=await browser.newPage();const checks=[]
 try{
  for(const [width,height] of [[320,640],[390,844],[393,852],[430,932]]){
   await page.setViewportSize({width,height})
   const convert=value=>value.replace(/([\d.]+)rpx/g,(_,n)=>Number(n)*width/750+'px').replace(/(?<![.\w-])page\b/g,'body')
   const messages=Array.from({length:8},(_,i)=>`<div class="msg-row ${i%2?'msg-l':'msg-r'}"><div class="msg-bubble ${i%2?'guide':'user'}"><span class="msg-text">${i%2?('玉带桥位于昆明湖西堤，介绍景点的长回复。\n\n'.repeat(7)+'A'.repeat(130)):'这里有什么好玩的？'} </span><span class="msg-time">14:18</span></div></div>`).join('')
   await page.setContent(`<style>html,body{margin:0;padding:0}div,span{box-sizing:content-box}.chat-area{width:100%;height:100%;overflow-y:auto;display:block}.nav{height:70px;flex-shrink:0}.spot-switch{height:54px} ${convert(globalCss)} ${convert(css)}</style><div class="page"><div class="nav"></div><div class="guide-stage"></div><div class="spot-switch"></div><div class="chat-area"><div class="chat-content">${messages}<div id="bottom" style="height:12px"></div></div></div><div class="bottom-bar"><div class="input-row" style="height:44px"></div></div></div>`)
   const result=await page.evaluate(()=>{
    const chat=document.querySelector('.chat-area'),bar=document.querySelector('.bottom-bar');chat.scrollTop=chat.scrollHeight
    const rect=chat.getBoundingClientRect(),footer=bar.getBoundingClientRect(),last=document.querySelector('#bottom').getBoundingClientRect()
    return {bubbles:[...document.querySelectorAll('.msg-bubble')].map(el=>{const r=el.getBoundingClientRect();return{left:r.left,right:r.right,scroll:el.scrollWidth,width:el.clientWidth}}),chatHeight:rect.height,chatBottom:rect.bottom,footerTop:footer.top,footerBottom:footer.bottom,lastBottom:last.bottom,scrollable:chat.scrollHeight>chat.clientHeight,bodyWidth:document.documentElement.scrollWidth}
   })
   for(const bubble of result.bubbles){assert.ok(bubble.left>=7&&bubble.right<=width-7,'messages stay inside phone edges: '+JSON.stringify(result));assert.ok(bubble.scroll<=bubble.width+1,'unbroken text wraps inside the bubble')}
   assert.ok(result.chatHeight>80&&result.scrollable,'chat has a bounded independently scrolling viewport: '+JSON.stringify(result))
   assert.ok(result.chatBottom<=result.footerTop+1,'input bar never covers the chat viewport')
   assert.ok(result.lastBottom<=result.footerTop+1,'last message is reachable above the input bar')
   assert.ok(result.footerBottom<=height+1&&result.bodyWidth<=width+1,'page stays inside the phone')
   await page.screenshot({path:path.join(out,`${width}x${height}.png`)});checks.push({width,height})
  }
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({passed:true,simulatedMessages:true,nativePhoneVerified:false,checks},null,2));console.log('Tour chat layout passed '+checks.length+' phone viewport cases')
 }catch(error){await page.screenshot({path:path.join(out,'failure.png')});throw error}finally{await browser.close()}
}
run().catch(error=>{console.error(error.message);process.exitCode=1})
