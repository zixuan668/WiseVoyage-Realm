// Actual SDK PCM processor + live MediaStream output, with synthetic samples.
// Verifies the audio graph in Chrome; iPhone audibility still needs a device.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),vm=require('node:vm'),assert=require('node:assert/strict')
const {chromium}=require('playwright-core')
const root=path.resolve(__dirname,'..'),out=path.resolve(root,'../work_dirs/iphone-test')
fs.mkdirSync(out,{recursive:true})
const helper=fs.readFileSync(path.join(root,'common/avatar-audio.js'),'utf8').replace(/export /g,'')
const sdk=fs.readFileSync(path.join(root,'static/sdk/xmov-avatar-2.4.1-compatible.js'),'utf8')
const literal=sdk.match(/var pcm_audio_script=("(?:\\.|[^"\\])*"),pcm_capture_script/)[1]
const processor=vm.runInNewContext('('+literal+')')
const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end('<button id="start">Start stream</button>')})
async function run(){
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--autoplay-policy=user-gesture-required']})
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message))
  await page.goto('http://127.0.0.1:'+server.address().port)
  await page.addScriptTag({content:helper})
  await page.evaluate(async processor=>{
   const Original=window.AudioContext,originalConnect=AudioNode.prototype.connect
   const controller=createAvatarAudioController(window,document,()=>{},{streamOutput:true})
   const ctx=new AudioContext({sampleRate:24000})
   const url=URL.createObjectURL(new Blob([processor],{type:'text/javascript'}))
   await ctx.audioWorklet.addModule(url);URL.revokeObjectURL(url)
   const pcm=new AudioWorkletNode(ctx,'pcm-audio-processor');pcm.connect(ctx.destination)
   const media=document.querySelector('audio'),monitor=new Original(),source=monitor.createMediaStreamSource(media.srcObject),analyser=monitor.createAnalyser(),silent=monitor.createGain()
   silent.gain.value=0;source.connect(analyser);analyser.connect(silent);silent.connect(monitor.destination)
   const samples=new Uint8Array(48000),values=new DataView(samples.buffer)
   for(let i=0;i<24000;i++)values.setInt16(i*2,Math.round(Math.sin(2*Math.PI*440*i/24000)*16000),true)
   window.audioTest={ctx,pcm,media,monitor,analyser,controller,originalConnect}
   document.querySelector('#start').onclick=()=>{
    controller.unlock();monitor.resume();pcm.port.postMessage({type:'start'});pcm.port.postMessage({type:'pcm',pcmData:samples},[samples.buffer])
   }
  },processor)
  await page.click('#start')
  await page.waitForFunction(()=>{const s=window.audioTest,b=new Float32Array(s.analyser.fftSize);s.analyser.getFloatTimeDomainData(b);const peak=Math.max(...b.map(Math.abs));if(peak>.1){s.peak=peak;return true}return false},null,{timeout:5000})
  const result=await page.evaluate(async()=>{
   const s=window.audioTest,result={running:s.ctx.state==='running',playing:!s.media.paused,peak:s.peak,liveStream:s.media.srcObject instanceof MediaStream,fileSource:s.media.getAttribute('src'),sdkSampleRate:s.ctx.sampleRate}
   s.pcm.port.postMessage({type:'pause'});s.pcm.disconnect();await s.ctx.close();s.controller.release();await s.monitor.close()
   result.cleaned=document.querySelectorAll('audio').length===0&&AudioNode.prototype.connect===s.originalConnect
   return result
  })
  assert.equal(result.running,true);assert.equal(result.playing,true);assert.ok(result.peak>.1);assert.equal(result.liveStream,true);assert.equal(result.fileSource,null);assert.equal(result.cleaned,true);assert.deepEqual(errors,[])
  fs.writeFileSync(path.join(out,'stream-audio-browser-results.json'),JSON.stringify({passed:true,iPhoneVerified:false,...result},null,2))
  console.log(JSON.stringify(result))
 }finally{await browser.close();server.close()}
}
run().catch(error=>{console.error(error);process.exitCode=1;server.close()})
