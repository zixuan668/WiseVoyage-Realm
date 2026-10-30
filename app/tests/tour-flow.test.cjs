const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..')
function component(file){
 const storage={user_id:17,token:'test'},toasts=[],calls=[],navigation=[]
 const c={getCurrentPages:()=>[{route:"pages/mine/history"},{route:"pages/tour-summary/tour-summary"}],console,Date,Promise,setTimeout,clearTimeout,setInterval,clearInterval,BASE_URL:'http://local/api/v1',LANGUAGE_STORAGE_KEY:'language',assetUrl:x=>x,isBeijingCity:()=>true,selectedOrder:(order,ids)=>order.filter(id=>ids[id]),previewOptions:ids=>({spot_ids:ids}),roadMap:()=>null,FloatingTourButton:{},RouteTiming:{},ScenicSheet:{},NocturneConfirm:{},TourXingyun:{},TourXfyun:{},RouteOverview:{},TourRouteRepair:{},uni:{getStorageSync:k=>storage[k],setStorageSync:(k,v)=>{storage[k]=v},showToast:o=>toasts.push(o),getSystemInfoSync:()=>({}),request:o=>{calls.push(o)},reLaunch:o=>navigation.push(o),navigateTo:o=>navigation.push(o),navigateBack:()=>navigation.push({back:true})}}
 c.AuthPage={}
 vm.createContext(c)
 vm.runInContext(fs.readFileSync(path.join(root,'common/avatar-audio.js'),'utf8').replace(/export /g,''),c)
 vm.runInContext(fs.readFileSync(path.join(root,'common/chat-language.js'),'utf8').replace(/export /g,''),c)
 const source=fs.readFileSync(path.join(root,file),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
 vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.options='),c)
 const o=c.options,s={t:x=>x,$nextTick:fn=>fn?.()};Object.assign(s,o.data.call(s));for(const [k,f] of Object.entries(o.methods))s[k]=f.bind(s);for(const [k,f] of Object.entries(o.computed||{}))Object.defineProperty(s,k,{get:()=>f.call(s)})
 return{s,o,storage,toasts,calls,navigation,uni:c.uni}
}

test('summary analyzes the tour without requesting or exposing an end-of-tour quiz',()=>{
 const {s,calls}=component('pages/tour-summary/tour-summary.vue');s.sid=77;s.conversation=[{role:'user',message:'问题'},{role:'guide',message:'回答'}];s.tryAISummary()
 assert.equal(calls.length,1);assert.match(calls[0].url,/\/analyze\/77$/)
 const source=fs.readFileSync(path.join(root,'pages/tour-summary/tour-summary.vue'),'utf8');assert.doesNotMatch(source,/\/tour-session\/quiz|class="hero"/);assert.match(source,/route-heading/)
})
test('tour chat translates both roles and restores original messages without changing server data',async()=>{
 const {s,calls}=component('pages/tour/tour.vue');s.tourLanguage='en';s.msgs=[{role:'user',message:'请介绍景点'},{role:'guide',message:'这是仁寿殿。'}]
 const pending=s.localizeChat();assert.equal(calls.length,1);calls[0].success({statusCode:200,data:{data:{translations:['Introduce this attraction.','This is the Hall of Benevolence and Longevity.']}}});await pending
 assert.equal(s.msgs[0].message,'Introduce this attraction.');assert.equal(s.msgs[1].message,'This is the Hall of Benevolence and Longevity.')
 s.tourLanguage='zh';await s.localizeChat();assert.equal(s.msgs[1].message,'这是仁寿殿。');assert.equal(calls.length,1)
})
test('language settings ignore old account responses and never overwrite a newer chat history',()=>{
 for(const change of ['account','history','language']){
  const {s,storage,calls}=component('pages/mine/mine.vue'),key='ai_chat_state:id%3A17';s.tourLanguage='en';storage[key]=JSON.stringify({messages:[{role:'user',content:'原文'}]});s.translateAiChatHistory('en')
  if(change==='account')storage.user_id=18
  if(change==='history')storage[key]=JSON.stringify({messages:[{role:'user',content:'新问题'}]})
  if(change==='language')s.tourLanguage='zh'
  const before=storage[key];calls[0].success({statusCode:200,data:{data:{translations:['Original.']}}});assert.equal(storage[key],before)
 }
})

test('language settings quote history as translation data and preserve the source for switching back',async()=>{
 for(const [target,source,translated] of [['en','请介绍颐和园的历史。','Please introduce the history of the Summer Palace.'],['zh','Please tell me about the history of the Summer Palace.','请告诉我颐和园的历史。']]){
  const {s,storage,calls}=component('pages/mine/mine.vue'),key='ai_chat_state:'+encodeURIComponent('id:17')
  s.tourLanguage=target
  storage[key]=JSON.stringify({messages:[{role:'user',content:source}]})
  const pending=s.translateAiChatHistory(target);const call=calls.find(c=>/translate-texts$/.test(c.url))
  assert.equal(call.data.target,target);assert.equal(JSON.parse(call.data.texts[0]),source)
  call.success({statusCode:200,data:{success:true,data:{translations:[translated]}}})
  await pending
  const message=JSON.parse(storage[key]).messages[0]
  assert.equal(message.content,translated);assert.equal(message.lang,target);assert.equal(message.translations[target==='en'?'zh':'en'],source)
 }
})
test('view itinerary is the only forward step; returning preserves stops, order, guide and route scroll',()=>{
 const {s,o}=component('pages/tour-guide/tour-guide.vue');s.pickedIds={12:true,3:true};s.orderedIds=[12,3];s.pickedGuide={guide_id:2};s.pickedRouteId=8;s.onPlanningScroll({detail:{scrollTop:840}})
 s.goSelectGuide();assert.equal(s.tab,'personal');assert.equal(s.planningScrollTop,0);assert.deepEqual(Array.from(s.selectedIds),[12,3]);s.onPlanningScroll({detail:{scrollTop:200}})
 assert.equal(o.onBackPress.call(s),true);assert.equal(s.tab,'route');assert.equal(s.planningScrollTop,840);assert.equal(s.pickedGuide.guide_id,2);assert.equal(s.pickedRouteId,8)
 s.goSelectGuide();assert.equal(s.tab,'personal');s.showItinerary=true;o.onBackPress.call(s);assert.equal(s.tab,'personal');assert.equal(s.showItinerary,false)
})
test('empty selection and in-flight tour creation cannot enter another planning step',()=>{
 const {s}=component('pages/tour-guide/tour-guide.vue');s.goSelectGuide();assert.equal(s.tab,'route');s.pickedIds={3:true};s.orderedIds=[3];s.starting=true;s.goSelectGuide();assert.equal(s.tab,'route')
})

test('category filters and search preserve the whole itinerary and category totals',()=>{
 const {s}=component('pages/tour-guide/tour-guide.vue');s.spots=[{spot_id:1,spot_name:'仁寿殿',city:'北京',category:'historical'},{spot_id:2,spot_name:'昆明湖',city:'北京',category:'natural'},{spot_id:3,spot_name:'长廊',city:'北京',category:'cultural'},{spot_id:4,spot_name:'园中景点',city:'北京',category:'natural'}];s.pickedIds={1:true,3:true};s.orderedIds=[3,1];s.pickedRouteId=8
 s.spotCat='natural';assert.deepEqual(Array.from(s.filteredSpots,x=>x.spot_id),[2,4]);assert.equal(s.pickedCount,2);assert.deepEqual(Array.from(s.selectedIds),[3,1]);assert.equal(s.pickedRouteId,8)
 s.keyword=' 昆明 ';assert.deepEqual(Array.from(s.filteredSpots,x=>x.spot_id),[2]);assert.deepEqual(Array.from(s.spotCats,x=>[x.value,x.count]),[['all',4],['historical',1],['natural',2],['cultural',1]])
 s.spotCat='all';s.keyword='文化古迹';assert.deepEqual(Array.from(s.filteredSpots,x=>x.spot_id),[3]);s.keyword='';assert.equal(s.filteredSpots.length,4);assert.deepEqual(Array.from(s.selectedIds),[3,1])
})

test('category search supports translated labels, missing categories and array tags',()=>{
 const {s}=component('pages/tour-guide/tour-guide.vue');s.t=value=>({'自然风光':'Nature','昆明湖':'Kunming Lake','其他':'Other'}[value]||value);s.spots=[{spot_id:2,spot_name:'昆明湖',category:'natural',tags:['湖水','摄影']},{spot_id:5,spot_name:'景点甲'},{spot_id:6,spot_name:'景点乙',category:''},{spot_id:7,spot_name:'新景点',category:'new-kind'}]
 s.keyword='nature';assert.equal(s.filteredSpots[0].spot_id,2);s.keyword='kunming';assert.equal(s.filteredSpots[0].spot_id,2);s.keyword='摄影';assert.equal(s.filteredSpots[0].spot_id,2)
 s.keyword='';s.spotCat='other';assert.deepEqual(Array.from(s.filteredSpots,x=>x.spot_id),[5,6]);assert.equal(s.catLabel(null),'Other');assert.equal(s.catLabel('new-kind'),'new-kind');assert.equal(s.spotCats.find(x=>x.value==='other').count,2)
})
test('local ratings persist per signed-in account and per tour and can be updated',()=>{
 const {s,storage}=component('pages/tour-summary/tour-summary.vue');s.sid=71;s.ratingOwner=s.ratingAccount();s.sessionData={status:{live_status:2}};s.ratingScore=4;s.saveRating();assert.equal(s.savedRating,4);s.loadRating();assert.equal(s.ratingScore,4)
 s.ratingScore=5;s.saveRating();s.loadRating();assert.equal(s.savedRating,5)
 s.sid=72;s.loadRating();assert.equal(s.ratingScore,0);s.sid=71;storage.user_id=18;s.ratingOwner=s.ratingAccount();s.loadRating();assert.equal(s.ratingScore,0)
 storage.user_id=17;s.ratingOwner=s.ratingAccount();s.loadRating();assert.equal(s.ratingScore,5)
})
test('active tours, invalid ratings, account switches and failed storage never claim a saved rating',()=>{
 const {s,storage,uni,toasts}=component('pages/tour-summary/tour-summary.vue');s.sid=71;s.ratingOwner=s.ratingAccount();s.sessionData={status:{live_status:1}};s.ratingScore=5;s.saveRating();assert.equal(s.savedRating,0)
 s.sessionData.status.live_status=2;for(const value of [0,6,2.5,'5']){s.ratingScore=value;s.saveRating();assert.equal(s.savedRating,0)}
 s.ratingScore=5;storage.user_id=18;s.saveRating();assert.equal(s.savedRating,0);assert.match(toasts.at(-1).title,/账号已变化/)
 storage.user_id=17;uni.setStorageSync=()=>{throw Error('full')};s.saveRating();assert.equal(s.savedRating,0);assert.match(toasts.at(-1).title,/保存失败/)
})
test('ending a tour opens summary only after server confirmation, deduplicates and allows retry on failure',async()=>{
 const {s,calls}=component('pages/tour/tour.vue');s.sid=71;const left=[];s.leaveTour=url=>left.push(url)
 const first=s.endTour();s.endTour();assert.equal(calls.length,1);assert.equal(left.length,0);calls[0].success({statusCode:200,data:{success:false}});await first;assert.equal(left.length,0);assert.equal(s.endingTour,false)
 const retry=s.endTour();calls[1].success({statusCode:200,data:{success:true}});await retry;assert.equal(left[0],'/pages/tour-summary/tour-summary?sessionId=71')
})

test('avatar connecting indicator stops on success, error and page exit and resumes on retry',()=>{
 const {s}=component('pages/tour/tour.vue');s.guideProvider='xingyun';s.tourVisible=true;s.leavingTour=false;s.xingyunConnected=false;s.xingyunFailed=false
 assert.equal(s.avatarConnecting,true);s.xingyunActive=true;assert.equal(s.avatarConnecting,true)
 s._xingyunGateway='mock-gateway';s.onXingyunState({state:'connected',gateway:'other-gateway'});assert.equal(s.avatarConnecting,true)
 s.onXingyunState({state:'connected',gateway:'mock-gateway'});assert.equal(s.avatarConnecting,false)
 s.onXingyunState({state:'error',gateway:'mock-gateway'});assert.equal(s.avatarConnecting,false)
 s.xingyunFailed=false;assert.equal(s.avatarConnecting,true)
 s.leavingTour=true;assert.equal(s.avatarConnecting,false);s.leavingTour=false;s.tourVisible=false;assert.equal(s.avatarConnecting,false)
 s.tourVisible=true;s.guideProvider='audio';assert.equal(s.avatarConnecting,false)
})

test('real live-info contract exposes ended status at the root, without nested status or end_time',()=>{
 const {s}=component('pages/tour-summary/tour-summary.vue');s.sessionData={session_id:147,live_status:2,start_time:'2026-10-20T12:00:00',current_spot_index:0};s.sid=147;s.ratingOwner=s.ratingAccount();assert.equal(s.tourEnded,true);s.ratingScore=4;s.saveRating();assert.equal(s.savedRating,4)
 s.sessionData={live_status:1,status:{live_status:2}};assert.equal(s.tourEnded,false)
 s.sessionData={live_status:0};assert.equal(s.tourEnded,false)
})

test('tour history shows existing ratings by account and tour, and refreshes updated scores',()=>{
 const {s,storage,navigation}=component('pages/mine/history.vue');storage['tour_rating:v1:id%3A17:71']={score:3};storage['tour_rating:v1:id%3A17:72']={score:5};s.list=[{session_id:71,live_status:2},{session_id:72,live_status:2},{session_id:73,live_status:2},{session_id:74,live_status:1}];s.refreshRatings();assert.equal(s.ratings[71],3);assert.equal(s.ratings[72],5);assert.equal(s.ratings[73],undefined);assert.equal(s.ratings[74],undefined)
 s.openRating(s.list[0]);assert.equal(navigation[0].url,'/pages/tour-summary/tour-summary?sessionId=71');storage['tour_rating:v1:id%3A17:71']={score:4};s.refreshRatings();assert.equal(s.ratings[71],4)
 storage.user_id=18;s.refreshRatings();assert.equal(Object.keys(s.ratings).length,0)
 storage.user_id=17;storage['tour_rating:v1:id%3A17:71']={score:6};s.refreshRatings();assert.equal(s.ratings[71],undefined)
})
test('history reload joins the saved rating after the authenticated tour response arrives',async()=>{
 const {s,storage,calls}=component('pages/mine/history.vue');storage['tour_rating:v1:id%3A17:71']={score:3};const loading=s.loadData();calls.find(c=>c.url.endsWith('/tour-session/my-history')).success({statusCode:200,data:{success:true,data:{session_list:[{session_id:71,live_status:2,city:'北京'}]}}});calls.find(c=>c.url.endsWith('/spot-favorites/history')).success({statusCode:200,data:{success:true,data:{spot_list:[]}}});await loading;assert.equal(s.ratings[71],3);assert.equal(s.loading,false)
})

test('a rating opened from history returns to that history instead of replacing it with the home page',()=>{
 const {s,navigation}=component('pages/tour-summary/tour-summary.vue');s.goBack();assert.equal(navigation.length,1);assert.equal(navigation[0].back,true)
})

test('pausing an old reply does not mute the next reply',()=>{
 const {s}=component('pages/tour/tour.vue')
 s.xingyunActive=true;s._xingyunGateway='gateway'
 s.msgs=[{role:'guide',message:'上一条'},{role:'guide',message:'下一条'}]
 s.speakAnswer('上一条',0);s.speaking=true;s.toggleVoiceMute(s.msgs[0],0)
 assert.equal(s.speechPaused,true)
 s.stopPlayback();s.speakAnswer('下一条',1)
 assert.equal(s.voiceMuted,false);assert.equal(s.speechPaused,false)
 assert.equal(s.xingyunPayload.command,'speak');assert.equal(s.xingyunPayload.text,'下一条')
 assert.equal(s.isMessagePlaying(0),false);assert.equal(s.isMessagePlaying(1),true)
})
test('selecting another reply does not resume the previous reply text or audio',()=>{
 const {s}=component('pages/tour/tour.vue')
 s.xingyunActive=true;s._xingyunGateway='gateway'
 const a={message:'旧回答'},b={message:'新回答'}
 s.speakAnswer(a.message,0);s.speaking=true;s.toggleVoiceMute(a,0)
 s.toggleVoiceMute(b,1)
 assert.equal(s.xingyunPayload.text,b.message);assert.equal(s.activeSpeechIndex,1)
 s.speaking=true;s.toggleVoiceMute(b,1)
 assert.equal(s.speechPaused,true);assert.equal(s.isMessagePlaying(0),false)
})
test('tour resume at the estimated end never restarts the entire answer',()=>{
 const {s}=component('pages/tour/tour.vue'),spoken=[]
 s._xingyunFullText='欢迎参观';s._xingyunOffset=4;s.xingyunActive=true;s.speechPaused=true;s.voiceMuted=true;s.speakAnswer=t=>spoken.push(t);s.speakXingyun=t=>spoken.push(t)
 s.resumeSpeech('欢迎参观');assert.equal(spoken.length,0);assert.equal(s.speaking,false)
 s._xingyunOffset=2;s.resumeSpeech('欢迎参观');assert.deepEqual(spoken,['参观'])
})
test('completed digital guide speech returns its button to play',()=>{
 const {s}=component('pages/tour/tour.vue');s._xingyunGateway='gateway';s.xingyunActive=true
 s.speakAnswer('回答',0);s.onXingyunState({state:'playing',gateway:'gateway'})
 assert.equal(s.isMessagePlaying(0),true)
 s.onXingyunState({state:'ended',gateway:'gateway'})
 assert.equal(s.isMessagePlaying(0),false)
})
test('tour pause survives late playing callbacks',()=>{
 const {s}=component('pages/tour/tour.vue');s._xingyunGateway='gateway';s.speechPaused=true;s.voiceMuted=true
 s.onXingyunState({state:'playing',gateway:'gateway'})
 assert.equal(s.speechPaused,true);assert.equal(s.speaking,false)
})
test('anonymous tour and summary requests carry the scoped token',()=>{
 for(const file of ['pages/tour/tour.vue','pages/tour-summary/tour-summary.vue']){
  const {s,storage,calls}=component(file);storage.token='';storage['xingyun-tour-77']='capability';s.sid=77
  if(file.includes('summary'))s.loadData();else s.refresh()
  assert.equal(calls[0].header['X-Tour-Access'],'capability')
 }
})

test('iPhone and Android keep speech and animation in the same SDK session',()=>{
 for(const platform of ['ios','android']){
  const {s,uni,calls}=component('pages/tour/tour.vue');s.appXingyun=true;s.guideProvider='xingyun';uni.getSystemInfoSync=()=>({platform})
  const visual=[],audio=[];s.speakXingyun=text=>visual.push(text);s.playAudio=url=>audio.push(url)
  s.speakAnswer('欢迎游览','/files/other-voice.wav')
  assert.deepEqual(visual,['欢迎游览']);assert.deepEqual(audio,[]);assert.equal(calls.length,0)
 }
})

test('iPhone SDK voice events control playback state and respect pause',()=>{
 const {s,uni}=component('pages/tour/tour.vue');s.appXingyun=true;s.guideProvider='xingyun';s._xingyunGateway='gateway';uni.getSystemInfoSync=()=>({platform:'ios'})
 s.onXingyunState({state:'playing',gateway:'gateway'});assert.equal(s.speaking,true)
 s.onXingyunState({state:'ended',gateway:'gateway'});assert.equal(s.speaking,false)
 s.pauseSpeech();s.onXingyunState({state:'playing',gateway:'gateway'});assert.equal(s.speaking,false)
})
