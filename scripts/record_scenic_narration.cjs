// Actual Xingyun audio capture. No synthetic fixture data or alternate TTS.
const {chromium}=require('playwright-core')
async function main(){
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--autoplay-policy=no-user-gesture-required']})
 try{
  const page=await browser.newPage()
  page.on('console',message=>{if(message.text().startsWith('REC:'))console.log(message.text())})
  page.on('pageerror',()=>console.error('录制页面发生运行错误'))
  const localOrigin='http://127.0.0.1:'+process.argv[2]
  await page.route(localOrigin+'/**',route=>route.continue({headers:{...route.request().headers(),'X-Record-Token':process.env.SCENIC_RECORD_TOKEN}}))
  page.setDefaultTimeout(240000)
  await page.goto(localOrigin)
  const result=await page.evaluate(async(token)=>{
   const headers={'X-Record-Token':token}
   const jobs=await(await fetch('/jobs',{headers})).json()
   let failure=null, started=false, ended=false, captured=[[]], accepting=false, lastChunk=0, chunkCount=0
   const avatar=new window.XmovAvatar({containerId:'#avatar',appId:'server-proxy',appSecret:'server-proxy',
    gatewayServer:location.origin+'/session',headers,hardwareAcceleration:'prefer-software',
    onMessage:e=>{if(e.code&&e.code!==4000){failure='星云错误 '+e.code;console.log('REC: SDK event '+e.code)}},
    onStateChange:s=>console.log('REC: state '+s),
    onVoiceStateChange:s=>{console.log('REC: voice '+s);if(s.includes('start')){started=true;ended=false}if(s.includes('end'))ended=true},
    onAudioPlaybackData:chunk=>{
     if(!accepting||!chunk.data?.byteLength)return
     if(chunk.isFirstChunk&&captured.at(-1).length)captured.push([])
     captured.at(-1).push(chunk.data.slice(0));lastChunk=Date.now();chunkCount++
     if(chunkCount%300===0)console.log('REC: captured '+(chunkCount/10).toFixed(0)+' seconds of speech')
    },
    proxyWidget:{subtitle_on:()=>{},subtitle_off:()=>{}}})
   const sleep=ms=>new Promise(r=>setTimeout(r,ms))
   async function until(test,ms){const end=Date.now()+ms;while(!test()){if(failure)throw Error(failure);if(Date.now()>end)throw Error('星云录制超时');await sleep(100)}}
   try{
    let initTimer
    try{await Promise.race([avatar.init({onDownloadProgress:()=>{}}),new Promise((_,reject)=>{initTimer=setTimeout(()=>reject(Error('星云初始化超时')),180000)})])}
    finally{clearTimeout(initTimer)}
    await avatar.enableAudioPlaybackCapture()
    // init() resolves after resources load; the speech socket may connect later.
    // sendText silently drops text until that socket is connected.
    await until(()=>avatar.ttsa?.getStatus(),45000)
    avatar.ttsa.ws.onAny((event,data)=>{
     if(['error','message','tts_error','speak_error','text_response','send_text_response'].includes(event))console.log('REC: server event '+event+', fields '+Object.keys(data||{}).join(','))
    })
    avatar.interactiveidle()
    await sleep(700)
    console.log('REC: initialized, speech socket connected, audio capture enabled')
    for(const job of jobs){
     started=false;ended=false;failure=null;captured=[[]];accepting=true;lastChunk=0;chunkCount=0
     try{
      console.log('REC: narrating spot '+job.id+', '+job.script.length+' characters')
      avatar.speak(job.script,true,true)
      await until(()=>started,45000)
      await until(()=>ended&&lastChunk&&Date.now()-lastChunk>1500,Math.max(120000,job.script.length*600))
      await sleep(700) // Let the SDK finish its asynchronous Opus encoding queue.
      accepting=false
      if(failure)throw Error(failure)
      if(!captured[0].length)throw Error('星云未返回实际音轨，拒绝替换音色')
      const context=new AudioContext({sampleRate:16000})
      let duration, blob
      try{
       const parts=[]
       for(const segment of captured){
        if(segment.length)parts.push(await context.decodeAudioData(await new Blob(segment,{type:'audio/webm'}).arrayBuffer()))
       }
       const rate=parts[0].sampleRate
       if(parts.some(p=>p.sampleRate!==rate))throw Error('音轨采样率不一致')
       const length=parts.reduce((n,p)=>n+p.length,0)
       duration=length/rate
       if(duration<job.script.length/8)throw Error('音轨长度异常，可能缺失部分讲解')
       const bytes=new ArrayBuffer(44+length*2),view=new DataView(bytes)
       const ascii=(offset,text)=>{for(let i=0;i<text.length;i++)view.setUint8(offset+i,text.charCodeAt(i))}
       ascii(0,'RIFF');view.setUint32(4,36+length*2,true);ascii(8,'WAVE');ascii(12,'fmt ')
       view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true)
       view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true)
       ascii(36,'data');view.setUint32(40,length*2,true)
       let offset=44,audible=false
       for(const part of parts){
        const samples=part.getChannelData(0)
        for(const sample of samples){
         if(Math.abs(sample)>.0001)audible=true
         view.setInt16(offset,Math.round(Math.max(-1,Math.min(1,sample))*32767),true);offset+=2
        }
       }
       if(!audible)throw Error('录音为静音，拒绝保存')
       blob=new Blob([bytes],{type:'audio/wav'})
       console.log('REC: decoded '+parts.length+' segments, '+duration.toFixed(1)+' seconds')
      }finally{await context.close()}
      const response=await fetch('/record/'+job.id+'?duration='+duration,{method:'POST',headers,body:blob})
      if(!response.ok)throw Error('保存录音失败 '+response.status)
     }finally{accepting=false}
    }
    return jobs.length
   }finally{
    let stopTimer
    try{await Promise.race([Promise.resolve(avatar.destroy()),new Promise(resolve=>{stopTimer=setTimeout(resolve,10000)})])}
    finally{clearTimeout(stopTimer)}
   }
  },process.env.SCENIC_RECORD_TOKEN)
  console.log('已完成真实星云录音：'+result)
 }finally{await browser.close()}
}
main().catch(e=>{console.error(String(e.message).replace(/https?:\/\/\S+/g,'[服务地址]'));process.exitCode=1})
