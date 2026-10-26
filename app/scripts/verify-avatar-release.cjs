// Release gate for the retained Android decoder and centered wide avatar.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict')
const root=path.resolve(__dirname,'..'),read=file=>fs.readFileSync(path.join(root,file),'utf8'),hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex')
const sdk=fs.readFileSync(path.join(root,'static/sdk/xmov-avatar-2.4.1-compatible.js'))
assert.equal(hash(sdk),'6a82d4311c8f3d7403b914a8daa8db16ae85f567ba3a2754c30cfc01c8b182fd','Unreviewed SDK')
for(const file of ['components/tour-xingyun.vue']){
 const source=read(file);assert.ok(source.includes('await loadXingyunSdk()'));assert.ok(source.includes("hardwareAcceleration:'prefer-hardware'"));assert.ok(!source.includes('script.src=value.sdkUrl'))
}
assert.ok(read('components/tour-xingyun.vue').includes('transform:translateX(0)'),'Avatar must be centered')
assert.ok(read('pages/tour/tour.vue').includes('aspect-ratio:16/9'),'Use a wide upper-body viewport')
assert.ok(!/<chat-voice|<ChatVoice/.test(read('pages/ai-chat/ai-chat.vue')),'Audio-only entry must not decode hidden video')
assert.ok(!read('pages/ai-chat/ai-chat.vue').includes("request({url:'/xingyun/chat-voice'"))
assert.ok(read('pages/tour/tour.vue').includes("command:'connect',text:''"),'Pending speech must dispatch once after connection')
const index=process.argv.indexOf('--compiled');let compiledChecked=false
if(index>=0){const dir=process.argv[index+1],render=fs.readFileSync(path.join(dir,'app-renderjs.js'),'utf8');assert.ok(render.includes('xmov-avatar-2.4.1-compatible.js')&&render.includes('prefer-hardware'));assert.ok(fs.readFileSync(path.join(dir,'static/sdk/xmov-avatar-2.4.1-compatible.js')).equals(sdk));compiledChecked=true}
console.log(JSON.stringify({passed:true,compatibleSdk:true,centeredWideAvatar:true,audioOnlyChat:true,compiledChecked}))
