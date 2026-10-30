const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..'),tick=()=>new Promise(r=>setImmediate(r)),plain=x=>JSON.parse(JSON.stringify(x))
function harness(){
 const calls=[],uploads=[],feedback=[],navigations=[],storage=new Map([['user_id',17],['token','mock-17']]),handlers={}
 const uni={getStorageSync:k=>storage.get(k),setStorageSync:(k,v)=>storage.set(k,v),removeStorageSync:k=>storage.delete(k),request:o=>{calls.push(o);return{abort(){}}},uploadFile:o=>{uploads.push(o);return{abort(){}}},showToast:o=>feedback.push(o),reLaunch:o=>navigations.push(o),getRecorderManager:()=>({onStart:fn=>handlers.start=fn,onStop:fn=>handlers.stop=fn,onError:fn=>handlers.error=fn,stop(){},start(){}})}
 const translateTour=(s,language,params={})=>String(s??'').replace(/\{(\w+)\}/g,(m,k)=>params[k]??m)
 const c={uni,console,Promise,Date,Set,Number,Math,JSON,Array,Object,String,setTimeout,clearTimeout,BASE_URL:'http://local/api/v1',NocturneSelect:{},TourXingyun:{},translateTour,LANGUAGE_STORAGE_KEY:'zhiyou.app-language',assetUrl:x=>x,uiToast:o=>feedback.push(o)}
 vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(root,'common/chat-language.js'),'utf8').replace(/export /g,''),c);vm.runInContext(fs.readFileSync(path.join(root,'common/planning-language.js'),'utf8').replace(/^import .*$/gm,'').replace(/export /g,''),c)
 const source=fs.readFileSync(path.join(root,'pages/ai-chat/ai-chat.vue'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
 vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.component='),c)
 const o=c.component,s={tourLanguage:'en',$t:(value,params)=>translateTour(value,'en',params),t:(value,params)=>translateTour(value,'en',params),$nextTick:fn=>fn()};Object.assign(s,o.data.call(s));for(const [k,f] of Object.entries(o.methods))s[k]=f.bind(s)
 for(const [k,f] of Object.entries(o.computed||{}))Object.defineProperty(s,k,{get:()=>f.call(s),configurable:true})
 s.playTTS=()=>{};o.onShow?.call(s)
 return{s,o,uni,calls,uploads,feedback,navigations,storage,handlers,reply(call,data){call.success({statusCode:200,data:{success:true,data}})}}
}
const spots=[{spot_id:7,spot_name:'万寿山',city:'北京'},{spot_id:8,spot_name:'昆明湖',city:'北京'}],guide={guide_id:2,is_enabled:true}
test('language watcher translates the visible streamed chat and restores Chinese without a new request',async()=>{
 const h=harness(),s=h.s;s.msgs=[{role:'user',content:'介绍仁寿殿'},{role:'ai',content:'仁寿殿是理政中心。',segments:[{t:'旧文本'}],cursor:true}];s.historyMsgs=s.msgs.map(m=>({...m}));s.tourLanguage='en'
 h.o.watch.tourLanguage.call(s);const call=h.calls.find(c=>/translate-texts$/.test(c.url));assert.ok(call);h.reply(call,{translations:['Introduce the hall.','The hall was a center of government.']});await tick();await tick()
 assert.equal(s.msgs[1].content,'The hall was a center of government.');assert.equal(s.msgs[1].segments,undefined);assert.equal(s.msgs[1].cursor,false)
 const count=h.calls.length;s.tourLanguage='zh';h.o.watch.tourLanguage.call(s);await tick();assert.equal(s.msgs[1].content,'仁寿殿是理政中心。');assert.equal(h.calls.length,count)
})
test('ordinary scenic questions use chat with language and retain the same conversation',async()=>{
 const h=harness(),s=h.s;assert.equal(s.chatMode,'guide');s.qaSpots=spots;s.qaGuides=[guide];s.qaSpotId=7;s.text='What is its history?'
 const run=s.sendText();await tick();assert.match(h.calls[0].url,/visitor-create/);h.reply(h.calls.shift(),{session_id:70});await tick()
 let ask=h.calls.shift();assert.match(ask.url,/\/tour-session\/chat$/);assert.equal(ask.data.language,'en');assert.equal(ask.data.currentSpotId,7);h.reply(ask,{message:'History answer'});await run
 s.text='Tell me more.';const follow=s.sendText();await tick();ask=h.calls.shift();assert.equal(ask.data.sessionId,70);h.reply(ask,{message:'More history'});await follow;assert.equal(s.msgs.at(-1).content,'More history')
})
test('route preview uses server totals and consecutive walking data',async()=>{
 const h=harness(),s=h.s;s.chatMode='route';s.text='A two hour nature tour';const run=s.sendText();await tick();assert.match(h.calls[0].url,/ai-chat-recommend/)
 h.reply(h.calls.shift(),{spot_ids:[7,8],estimated_time_minutes:91,total_duration:999,score_details:[{spot_id:7},{spot_id:8,walk_from_previous_meters:345,walk_from_previous_minutes:6}],ai_response:'Route'});await run
 assert.equal(s.totalDuration,91);assert.match(s.walkText(spots[0],spots[1]),/345.*6/);assert.doesNotMatch(s.walkText(spots[1],spots[0]),/345/)
})
test('clear ignores late text and catalog responses, including route cache and delayed apply',async()=>{
 const h=harness(),s=h.s;s.chatMode='route';s.text='Plan a trip';const run=s.sendText();const old=h.calls.shift();s.clearHistory();h.reply(old,{spot_ids:[7],estimated_time_minutes:90,ai_response:'Old'});await run
 assert.equal(s.msgs.length,0);assert.equal(s.lastSpotIds.length,0);assert.equal(h.storage.has('ai_spot_ids'),false)
 s.lastSpotIds=[7];s.applyRecommend();s.clearHistory();await new Promise(r=>setTimeout(r,550));assert.equal(h.navigations.length,0)
})
test('clear ignores a late photo and never sends its follow-up question',async()=>{
 const h=harness(),s=h.s;s.pendingPhoto='/photo.jpg';s.text='Where is this?';const run=s.sendPhoto();const upload=h.uploads.shift();s.clearHistory();upload.success({statusCode:200,data:JSON.stringify({success:true,data:{status:'candidate',spot_id:7,spot_name:'万寿山'}})});upload.complete?.();await run;assert.equal(s.msgs.length,0);assert.equal(s.pendingPhoto,'');assert.equal(h.calls.length,0)
})
test('clear ignores late speech recognition and does not auto-send old questions',async()=>{
 const h=harness(),s=h.s;s.initRecorder();h.handlers.stop({tempFilePath:'/speech.mp3',duration:1000});const upload=h.uploads.shift();s.clearHistory();upload.success({statusCode:200,data:JSON.stringify({success:true,data:'old question'})});upload.complete();await tick();assert.equal(h.calls.length,0);assert.equal(s.text,'');assert.equal(s.transcribing,false)
})
test('re-entering an account clears the chat page but keeps that account Q&A history',()=>{
 const h=harness(),s=h.s;s.chatMode='route';s.qaSpotId=7;s.qaSession={session_id:70,guide_id:2};s.pushMsg({role:'user',content:'Private A'});s.recommendedPlan={spot_ids:[7,8],estimated_time_minutes:91};s.saveHistory()
 h.storage.set('user_id',18);h.storage.set('token','mock-18');s.loadHistory();assert.equal(s.historyMsgs.length,0);assert.equal(s.msgs.length,0);assert.equal(s.qaSession,null);assert.equal(s.lastSpotIds.length,0)
 s.pushMsg({role:'user',content:'Private B'});s.saveHistory();h.storage.set('user_id',17);h.storage.set('token','mock-17');s.loadHistory()
 assert.equal(s.msgs.length,0);assert.equal(s.historyMsgs[0].content,'Private A');assert.equal(s.chatMode,'guide');assert.equal(s.qaSession,null);assert.deepEqual(plain(s.lastSpotIds),[])
})
test('input accepts 2000 characters and rejects an overlong programmatic send',async()=>{
 const h=harness(),s=h.s;assert.match(fs.readFileSync(path.join(root,'pages/ai-chat/ai-chat.vue'),'utf8'),/:maxlength="2000"/)
 s.text='a'.repeat(2001);await s.sendText();assert.equal(h.calls.length,0);assert.equal(s.msgs.length,0);assert.equal(h.feedback.length,1)
 s.chatMode='route';s.text='a'.repeat(2000);const run=s.sendText();assert.equal(h.calls.length,1);h.reply(h.calls.shift(),{spot_ids:[],ai_response:'OK'});await run;assert.equal(s.msgs[0].content.length,2000)
})
test('switching accounts during a question ignores its reply and does not overwrite the other history',async()=>{
 const h=harness(),s=h.s;s.chatMode='route';s.text='Account A question';const run=s.sendText(),old=h.calls.shift();h.storage.set('user_id',18);h.storage.set('token','mock-18');s.loadHistory();s.msgs=[{role:'user',content:'Account B'}];s.saveHistory();h.reply(old,{spot_ids:[7],estimated_time_minutes:91,ai_response:'Old A reply'});await run;assert.equal(s.msgs.length,1);assert.equal(s.msgs[0].content,'Account B');assert.equal(s.lastSpotIds.length,0)
})
test('a photo picker returning after clear cannot restore the discarded draft',()=>{
 const h=harness(),s=h.s;let picker;h.uni.chooseImage=options=>{picker=options};s.pickScenicImage('album');s.clearHistory();picker.success({tempFilePaths:['/old-photo.jpg']});assert.equal(s.pendingPhoto,'')
})
test('opening English history quotes questions as translation data and caches the original text',async()=>{
 const h=harness(),s=h.s;s.historyMsgs=[{role:'user',content:'介绍这个景点'},{role:'ai',content:'这座桥始建于乾隆十五年。'}];s.saveHistory()
 s.openHistory();assert.equal(s.showHistory,true);assert.equal(s.historyTranslating,true)
 const call=h.calls.find(c=>/translate-texts$/.test(c.url));assert.ok(call,'translation request');assert.equal(call.data.target,'en');assert.deepEqual(plain(call.data.texts).map(JSON.parse),['介绍这个景点','这座桥始建于乾隆十五年。'])
 call.success({statusCode:200,data:{success:true,data:{translations:['Introduce this attraction.','This bridge was built in the fifteenth year of Qianlong.']}}});await tick();await tick()
 assert.equal(s.historyTranslating,false);assert.equal(s.historyMsgs[0].content,'Introduce this attraction.');assert.equal(s.historyMsgs[1].content,'This bridge was built in the fifteenth year of Qianlong.')
 assert.equal(s.historyMsgs[0].lang,'en');assert.equal(s.historyMsgs[0].translations.zh,'介绍这个景点')
 const saved=JSON.parse(h.storage.get(s.historyKey()));assert.equal(saved.messages[0].content,'Introduce this attraction.')
 s.openHistory();assert.equal(h.calls.filter(c=>/translate-texts$/.test(c.url)).length,1)
})
test('a failed history translation keeps the stored Chinese text for a later retry',async()=>{
 const h=harness(),s=h.s;s.historyMsgs=[{role:'user',content:'介绍这个景点'}];s.saveHistory()
 s.openHistory();const call=h.calls.find(c=>/translate-texts$/.test(c.url));assert.ok(call)
 call.fail({errMsg:'request:fail'});await tick();await tick()
 assert.equal(s.historyTranslating,false);assert.equal(s.historyMsgs[0].content,'介绍这个景点')
})

test('quoting translation data preserves embedded quotes, newlines and the source history',async()=>{
 const h=harness(),s=h.s,source='请介绍“长廊”。\n保留数字728和引号"。';s.historyMsgs=[{role:'user',content:source}]
 const run=s.localizeHistory(),call=h.calls.find(c=>/translate-texts$/.test(c.url))
 assert.equal(JSON.parse(call.data.texts[0]),source);assert.equal(s.historyMsgs[0].content,source)
 h.reply(call,{translations:['Please introduce the Long Corridor.\nKeep the number 728 and the quotation mark ".']});await run
 assert.equal(s.historyMsgs[0].translations.zh,source);assert.match(s.historyMsgs[0].content,/728/)
})

 test('English history rejects untranslated server fallback but keeps readable original text',async()=>{
 const h=harness(),s=h.s;s.historyMsgs=[{role:'user',content:'介绍景点'}];s.openHistory();h.reply(h.calls.find(c=>/translate-texts$/.test(c.url)),{translations:['介绍景点']});await tick();assert.equal(s.historyTranslationFailed,true);assert.equal(s.historyPairs[0].q,'介绍景点');assert.equal(s.historyMsgs[0].content,'介绍景点')
})
 test('history translation processes all records in bounded batches',async()=>{
 const h=harness(),s=h.s;s.historyMsgs=Array.from({length:9},(_,i)=>({role:'user',content:'景点'+i}));s.openHistory();
 for(const size of [4,4,1]){const call=h.calls.shift();assert.equal(call.data.texts.length,size);h.reply(call,{translations:call.data.texts.map(()=> 'An attraction')});await tick()}
 assert.equal(s.historyTranslating,false);assert.ok(s.historyMsgs.every(m=>m.content==='An attraction'))
})

test('clearing history from its panel preserves an in-flight reply and current question',async()=>{
 const h=harness(),s=h.s;s.chatMode='route';s.historyMsgs=[{role:'user',content:'Old question'}];s.text='Current question';const run=s.sendText(),call=h.calls.shift(),epoch=s.requestEpoch;s.showHistory=true;s.clearHistoryFromPanel();assert.equal(s.requestEpoch,epoch);assert.equal(s.loading,true);assert.equal(s.showHistory,false);assert.equal(s.msgs[0].content,'Current question');assert.equal(s.historyMsgs.length,1);assert.equal(s.historyMsgs[0].content,'Current question');h.reply(call,{spot_ids:[],ai_response:'Current answer'});await run;assert.equal(s.msgs.length,2);assert.equal(s.msgs.at(-1).role,'ai');assert.ok(s.msgs.at(-1).content);assert.equal(s.historyMsgs.at(-1).content,s.msgs.at(-1).content);assert.equal(s.loading,false)
})
test('clearing archived history preserves visible conversation and its session',()=>{
 const h=harness(),s=h.s;s.msgs=[{role:'user',content:'Visible question'},{role:'ai',content:'Visible answer'}];s.historyMsgs=s.msgs.slice();s.qaSession={session_id:70};s.clearHistoryFromPanel();assert.equal(s.msgs.length,2);assert.equal(s.qaSession.session_id,70);assert.equal(s.historyMsgs.length,0);assert.equal(JSON.parse(h.storage.get(s.historyKey())).messages.length,0)
})

test('undoing archived history keeps a pending question once and retains its new answer',()=>{
 const {s}=harness();const old={role:'user',content:'Old'},pending={role:'user',content:'Current'};
 s.historyMsgs=[old,pending];s.msgs=[pending];s.loading=true;s.clearHistoryFromPanel();
 s.pushMsg({role:'ai',content:'New answer'});s.undoClear();
 assert.deepEqual(plain(s.historyMsgs.map(m=>m.content)),['Old','Current','New answer']);assert.equal(s.msgs.length,2);s.dismissUndo();
})

test('undo current chat restores its draft and session without restoring an in-flight request',()=>{
 const {s}=harness();s.msgs=[{role:'user',content:'Old question'}];s.historyMsgs=s.msgs.slice();s.text='Draft';s.qaSession={session_id:70};s.clearHistory();const epoch=s.requestEpoch;s.undoClear();
 assert.equal(s.text,'Draft');assert.equal(s.qaSession.session_id,70);assert.equal(s.msgs[0].content,'Old question');assert.equal(s.loading,false);assert.equal(s.requestEpoch,epoch);s.dismissUndo();
})

test('undo after starting a new chat restores archive without replacing the new conversation',()=>{
 const {s}=harness();s.msgs=[{role:'user',content:'Old'}];s.historyMsgs=s.msgs.slice();s.clearHistory();s.pushMsg({role:'user',content:'New'});s.qaSession={session_id:71};s.undoClear();
 assert.deepEqual(plain(s.historyMsgs.map(m=>m.content)),['Old','New']);assert.equal(s.msgs[0].content,'New');assert.equal(s.qaSession.session_id,71);s.dismissUndo();
})

test('undo cannot restore another account or an expired snapshot',()=>{
 const h=harness(),s=h.s;s.historyMsgs=[{role:'user',content:'Private'}];s.clearHistoryFromPanel();h.storage.set('user_id',18);s.undoClear();assert.equal(s.historyMsgs.length,0);
 h.storage.set('user_id',17);s.historyMsgs=[{role:'user',content:'Expired'}];s.clearHistoryFromPanel();s._undoSnapshot.expiresAt=0;s.undoClear();assert.equal(s.historyMsgs.length,0);s.dismissUndo();
})
function audioHarness(){
 const h=harness(),s=h.s,audios=[]
 h.uni.createInnerAudioContext=()=>{
  const a={plays:0,pauses:0,destroyed:false,currentTime:2.5,onPlay:f=>a.played=f,onEnded:f=>a.ended=f,onError:f=>a.error=f,play(){a.plays++},pause(){a.pauses++},destroy(){a.destroyed=true}}
  audios.push(a);return a
 }
 s.playTTS=h.o.methods.playTTS.bind(s)
 return {...h,audios}
}
test('browser replies retain the Edge audio playback path',async()=>{
 const h=audioHarness();h.s.playTTS('English answer',0)
 assert.equal(h.calls.length,1);assert.match(h.calls[0].url,/\/tts\/edge\?/)
 h.reply(h.calls.shift(),'/files/speech.mp3');await tick()
 assert.equal(h.audios.length,1);assert.equal(h.audios[0].plays,1)
 const source=fs.readFileSync(path.join(root,'pages/ai-chat/ai-chat.vue'),'utf8')
 assert.ok(source.includes('playEdgeTTS'))
})
test('native AI replies use the default digital human voice and finish with play',async()=>{
 const h=audioHarness(),s=h.s;s.nativeChatVoice=true
 s.playTTS('欢迎参观',2)
 assert.equal(h.calls[0].url,'http://local/api/v1/xingyun/chat-voice')
 h.calls.shift().success({statusCode:200,data:{guide_id:2,sdk_url:'https://example.invalid/sdk.js'}});await tick()
 assert.equal(s.chatVoicePayload.command,'speak');assert.match(s.chatVoicePayload.gateway,/chat_speech=true/)
 assert.equal(s.chatVoicePayload.text,'欢迎参观');assert.equal(h.audios.length,0)
 s.onChatVoiceState({state:'playing',gateway:s.chatVoicePayload.gateway});assert.equal(s.isReplyPlaying(2),true)
 s.onChatVoiceState({state:'ended',gateway:s.chatVoicePayload.gateway});assert.equal(s.isReplyPlaying(2),false)
 assert.equal(s.chatVoicePayload.command,'close')
})
test('completed AI reply shows play instead of pause',async()=>{
 const h=audioHarness(),s=h.s
 assert.equal(s.isReplyPlaying(0),false)
 s.playTTS('回答',0);h.reply(h.calls.shift(),'/files/speech.mp3');await tick()
 h.audios[0].played();assert.equal(s.isReplyPlaying(0),true)
 h.audios[0].ended();assert.equal(s.isReplyPlaying(0),false)
 assert.equal(s.isReplyPlaying(1),false)
})
test('audio resume preserves the actual position and ignores a late playing event after pause',async()=>{
 const h=audioHarness(),s=h.s;s.playTTS('欢迎参观',0);h.reply(h.calls.shift(),'/files/speech.mp3');await tick()
 const a=h.audios[0];a.played();s.pauseTTS();a.played()
 assert.equal(s.ttsPaused,true);assert.equal(s.speaking,false)
 s.resumeTTS();a.played();assert.equal(a.currentTime,2.5);assert.equal(a.plays,2);assert.equal(h.calls.length,0)
 assert.equal(s.speaking,true);a.ended();s.resumeTTS()
 assert.equal(h.calls.length,0,'resume after completion never requests the full text again')
})
test('pause while audio is loading prevents automatic playback and stale callbacks are ignored',async()=>{
 const h=audioHarness(),s=h.s;s.playTTS('first',0);s.pauseTTS();h.reply(h.calls.shift(),'/files/first.mp3');await tick()
 const old=h.audios[0];assert.equal(old.plays,0);assert.equal(s.ttsPaused,true)
 s.resumeTTS();old.played();assert.equal(old.plays,1)
 s.playTTS('second',1);old.played();old.ended();assert.equal(s.speakingIndex,1);assert.equal(s.ttsLoading,true)
 h.reply(h.calls.shift(),'/files/second.mp3');await tick();assert.equal(h.audios.length,2)
})
// 回归：键盘弹起时欢迎区整块保持原位，不允许再重排（贴顶、隐藏气球/说明、缩小标题、改快捷提问间距）。
test('the welcome block keeps its layout when the keyboard opens',()=>{
 const pageStyle=fs.readFileSync(path.join(root,'pages/ai-chat/ai-chat.vue'),'utf8')
 const rules=[...pageStyle.matchAll(/\.chat-keyboard[^{]*\{([^}]*)\}/g)].map(m=>m[1])
 for(const body of rules){
  assert.doesNotMatch(body,/justify-content:flex-start/,'keyboard state must not top-align the welcome block')
  assert.doesNotMatch(body,/display:none/,'keyboard state must not hide the welcome art or description')
 }
 assert.doesNotMatch(pageStyle,/\.chat-keyboard \.welcome-title\s*\{[^}]*font-size/,'keyboard state must not resize the welcome title')
 assert.doesNotMatch(pageStyle,/\.chat-keyboard \.welcome-topics\s*\{[^}]*margin-top/,'keyboard state must not move the welcome topics')
})

test('selecting a question spot updates context without sending even after a pending shortcut',()=>{
 const {s}=harness();s.qaSpots=spots;s._pendingGuideKind='intro';s.text='my draft';s.showQASpots=true;s.$refs={};let sends=0;s.sendGuideKind=()=>{sends++};s.selectQuestionSpot({detail:{value:1}});assert.equal(s.qaSpotId,8);assert.equal(sends,0);assert.equal(s.text,'my draft');assert.equal(s._pendingGuideKind,'');assert.equal(s.showQASpots,false)
})
