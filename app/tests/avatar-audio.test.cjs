const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
function harness(){
 const file=path.join(__dirname,'../common/avatar-audio.js')
 assert.ok(fs.existsSync(file),'avatar audio must support gesture-driven playback recovery')
 const handlers=new Map(),instances=[]
 class AudioContext {
  constructor(){this.state='suspended';this.resumeCalls=0;this.events={};instances.push(this)}
  addEventListener(name,fn){this.events[name]=fn}
  removeEventListener(name){delete this.events[name]}
  resume(){this.resumeCalls++;this.state='running';this.events.statechange?.();return Promise.resolve()}
 }
 const win={AudioContext,webkitAudioContext:AudioContext,navigator:{audioSession:{type:'auto'}}}
 const doc={addEventListener:(name,fn)=>handlers.set(name,fn),removeEventListener:(name,fn)=>{if(handlers.get(name)===fn)handlers.delete(name)}}
 const context={console,Promise,Proxy,Reflect,Map,Set,Symbol}
 vm.createContext(context);vm.runInContext(fs.readFileSync(file,'utf8').replace(/export /g,'')+'\nglobalThis.api={createAvatarAudioController,prepareNativeGuideAudio}',context)
 return {win,doc,handlers,instances,Original:AudioContext,...context.api}
}
test('a real touch resumes the suspended SDK context synchronously and selects playback audio',async()=>{
 const h=harness(),blocked=[],controller=h.createAvatarAudioController(h.win,h.doc,value=>blocked.push(value))
 const audio=new h.win.AudioContext();assert.equal(audio.resumeCalls,0);assert.equal(blocked.at(-1),true)
 h.handlers.get('touchend')();assert.equal(audio.resumeCalls,1,'resume must run inside the gesture, before a promise turn')
 await Promise.resolve();assert.equal(h.win.navigator.audioSession.type,'playback');assert.equal(blocked.at(-1),false)
 controller.release();assert.equal(h.win.AudioContext,h.Original);assert.equal(h.handlers.size,0)
})
test('explicit enable-sound retries interrupted audio but skips closed contexts',async()=>{
 const h=harness(),controller=h.createAvatarAudioController(h.win,h.doc,()=>{})
 const interrupted=new h.win.AudioContext(),closed=new h.win.AudioContext();interrupted.state='interrupted';closed.state='closed'
 await controller.unlock();assert.equal(interrupted.resumeCalls,1);assert.equal(closed.resumeCalls,0)
 controller.release()
})
test('one avatar closing does not remove another avatar audio recovery',async()=>{
 const h=harness(),first=h.createAvatarAudioController(h.win,h.doc,()=>{}),second=h.createAvatarAudioController(h.win,h.doc,()=>{})
 first.release();const audio=new h.win.AudioContext();h.handlers.get('click')();assert.equal(audio.resumeCalls,1)
 second.release();assert.equal(h.win.AudioContext,h.Original);assert.equal(h.handlers.size,0)
})
test('iPhone guide playback activates a native playback session without changing Android audio',()=>{
 const h=harness(),calls=[],session={}
 const ios={os:{name:'iOS'},ios:{importClass:()=>({sharedInstance:()=>session}),invoke:(...args)=>calls.push(args)}}
 h.prepareNativeGuideAudio(ios)
 assert.ok(calls.some(args=>args[1]==='setCategory:error:'&&args[2]==='AVAudioSessionCategoryPlayback'))
 assert.ok(calls.some(args=>args[1]==='setActive:error:'&&args[2]===true))
 calls.length=0;h.prepareNativeGuideAudio({...ios,os:{name:'Android'}});assert.equal(calls.length,0)
})

function streamHarness(){
 const h=harness(),nodes=[],connections=[],disconnects=[],tracks=[]
 class AudioNode {
  connect(target,...ports){connections.push([this,target,...ports]);return target}
  disconnect(...args){disconnects.push([this,...args])}
 }
 h.win.AudioNode=AudioNode
 h.Original.prototype.createMediaStreamDestination=function(){const track={stopped:false,stop(){this.stopped=true}};tracks.push(track);const output=new AudioNode();output.stream={getTracks:()=>[track]};return output}
 const Original=h.win.AudioContext
 h.win.AudioContext=class extends Original{constructor(...args){super(...args);this.destination=new AudioNode()}}
 h.win.webkitAudioContext=h.win.AudioContext
 h.doc.body={appendChild:node=>nodes.push(node)}
 h.doc.createElement=()=>({paused:true,srcObject:null,plays:0,events:{},setAttribute(){},style:{},addEventListener(name,fn){this.events[name]=fn},removeEventListener(name){delete this.events[name]},play(){this.plays++;this.paused=false;this.events.play?.();return Promise.resolve()},pause(){this.paused=true},remove(){this.removed=true}})
 return {...h,nodes,connections,disconnects,tracks,AudioNode}
}

test('iPhone streams the original SDK output to a media element without a second audio connection',async()=>{
 const h=streamHarness(),originalConnect=h.AudioNode.prototype.connect
 const c=h.createAvatarAudioController(h.win,h.doc,()=>{},{streamOutput:true})
 const ctx=new h.win.AudioContext(),source=new h.AudioNode();source.context=ctx
 const returned=source.connect(ctx.destination)
 assert.equal(h.nodes.length,1);assert.equal(h.connections.length,1)
 assert.equal(returned,ctx.destination);assert.notEqual(h.connections[0][1],ctx.destination)
 assert.equal(h.nodes[0].srcObject,h.connections[0][1].stream);assert.equal(h.nodes[0].src,undefined)
 source.disconnect(ctx.destination);assert.equal(h.disconnects[0][1],h.connections[0][1])
 c.release();assert.equal(h.AudioNode.prototype.connect,originalConnect);assert.equal(h.nodes[0].srcObject,null);assert.equal(h.nodes[0].removed,true);assert.equal(h.tracks[0].stopped,true)
})

test('one gesture resumes SDK time and starts the streaming media output synchronously',async()=>{
 const h=streamHarness(),blocked=[],c=h.createAvatarAudioController(h.win,h.doc,value=>blocked.push(value),{streamOutput:true})
 const ctx=new h.win.AudioContext();assert.equal(blocked.at(-1),true)
 h.handlers.get('click')();assert.equal(ctx.resumeCalls,1);assert.equal(h.nodes[0].plays,1)
 await Promise.resolve();assert.equal(blocked.at(-1),false)
 c.release()
})

test('default audio output keeps the SDK destination unchanged',()=>{
 const h=streamHarness(),c=h.createAvatarAudioController(h.win,h.doc,()=>{})
 const ctx=new h.win.AudioContext(),source=new h.AudioNode();source.context=ctx;source.connect(ctx.destination)
 assert.equal(h.nodes.length,0);assert.equal(h.connections[0][1],ctx.destination);c.release()
})

test('blocked stream playback remains retryable after a rejected play request',async()=>{
 const h=streamHarness(),blocked=[],c=h.createAvatarAudioController(h.win,h.doc,value=>blocked.push(value),{streamOutput:true})
 new h.win.AudioContext();const media=h.nodes[0],play=media.play
 media.play=()=>Promise.reject(new Error('NotAllowedError'))
 await c.unlock();assert.equal(blocked.at(-1),true)
 media.play=play;await c.unlock();assert.equal(blocked.at(-1),false);c.release()
})

test('streaming does not redirect an existing unrelated context',()=>{
 const h=streamHarness(),existing=new h.win.AudioContext(),c=h.createAvatarAudioController(h.win,h.doc,()=>{},{streamOutput:true})
 const source=new h.AudioNode();source.connect(existing.destination)
 assert.equal(h.connections[0][1],existing.destination);assert.equal(h.nodes.length,0);c.release()
})
