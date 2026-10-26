const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
function page(file){
 const storage=new Map([['user_id',17],['token','old-token']]),calls=[],origins=[],nav=[]
 const uni={getStorageSync:k=>storage.get(k),setStorageSync:(k,v)=>storage.set(k,v),removeStorageSync:k=>storage.delete(k),request:o=>{calls.push(o);return{abort(){}}},navigateBack:()=>nav.push('back'),showToast(){},getSystemInfoSync:()=>({})}
 uni.reLaunch=o=>nav.push(o.url);uni.navigateTo=o=>nav.push(o.url)
 const c={uni,console,Date,Promise,setTimeout,clearTimeout,BrandLogo:{},AuthPage:{},NocturneConfirm:{},BASE_URL:'http://old/api/v1',SERVER_ORIGIN:'http://192.168.1.2:18000',LOGIN_PROVIDER:'password',assetUrl:x=>x,isBeijingCity:()=>true,isLocalStationOrigin:x=>/^http:\/\/192\.168\.1\.\d+:18000$/.test(x),translateTour:x=>x,LANGUAGE_STORAGE_KEY:'language',normalizeServiceOrigin:x=>/^(https:\/\/[a-z.]+|http:\/\/192\.168\.1\.\d+:18000)$/.test(x)?x:''}
 c.setServiceOrigin=origin=>{origins.push(origin);c.SERVER_ORIGIN=origin;storage.delete('token')}
 vm.createContext(c)
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../common/station-claim.js'),'utf8').replace(/export /g,''),c)
 const source=fs.readFileSync(path.join(__dirname,'..',file),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
 vm.runInContext(source.replace(/^import .*$/gm,'').replace('export default','globalThis.options='),c)
 const o=c.options,s={t:x=>x,$nextTick:f=>f()};Object.assign(s,o.data.call(s));for(const [k,f]of Object.entries(o.methods))s[k]=f.bind(s)
 return{s,o,storage,calls,origins,nav,uni}
}

test('expired-session sign-in explains why login is needed without retrying the stale credential',()=>{
 const h=page('pages/auth/auth.vue');h.o.onLoad.call(h.s,{expired:'1'})
 assert.equal(h.s.error,'登录已过期，请重新输入账号密码');assert.equal(h.calls.length,0)
})
test('tour conversation opens immediately and back preserves its underlying list',()=>{
 const h=page('pages/mine/history.vue'),list=[{session_id:1},{session_id:2}];h.s.list=list;h.s.openSession(list[0]);assert.equal(h.s.selected,list[0]);assert.equal(h.s.messagesLoading,true)
 h.s.goBack();assert.equal(h.s.selected,null);assert.equal(h.s.list,list);assert.equal(h.nav.length,0);h.s.goBack();assert.equal(h.nav.length,1)
})
test('closed or switched conversations ignore late replies, including account changes',()=>{
 const h=page('pages/mine/history.vue');h.s.openSession({session_id:1});const old=h.calls.shift();h.s.openSession({session_id:2});old.success({statusCode:200,data:{success:true,data:{messages:['old']}}});assert.equal(h.s.messages.length,0)
 const current=h.calls.shift();h.storage.set('user_id',18);current.success({statusCode:200,data:{success:true,data:{messages:['private']}}});assert.equal(h.s.messages.length,0)
 h.s.closeSession();current.complete();assert.equal(h.s.selected,null)
})
test('failed connection probes keep the current server and account unchanged',async()=>{
 const h=page('pages/auth/auth.vue');h.s.serviceAddress='https://guide.example.org';const run=h.s.connectService();assert.equal(h.calls[0].header,undefined,'probe sends no existing account credentials');h.calls[0].success({statusCode:503,data:{}});await run
 assert.equal(h.origins.length,0);assert.equal(h.storage.get('token'),'old-token');assert.ok(h.s.serviceError);assert.equal(h.s.connecting,false)
})
test('successful connection replaces the server only after the public probe succeeds',async()=>{
 const h=page('pages/auth/auth.vue');h.s.serviceAddress='https://guide.example.org';h.s.password='old-password';const run=h.s.connectService();assert.equal(h.origins.length,0)
 h.calls[0].success({statusCode:200,data:{success:true}});await run;assert.deepEqual(h.origins,['https://guide.example.org']);assert.equal(h.storage.has('token'),false);assert.equal(h.s.password,'');assert.ok(h.s.serviceNotice)
})
test('leaving sign-in during a probe cannot replace the selected server',async()=>{
 const h=page('pages/auth/auth.vue');h.s.serviceAddress='https://guide.example.org';const run=h.s.connectService();h.o.onUnload.call(h.s);h.calls[0].success({statusCode:200,data:{success:true}});await run;assert.equal(h.origins.length,0)
})
test('sign-in cannot race an active server connection probe',()=>{
 const h=page('pages/auth/auth.vue');h.s.connecting=true;h.s.account='name';h.s.password='secret';h.s.beginLogin();h.s.sendEmailCode();assert.equal(h.calls.length,0)
})

test('scanning a station route probes its origin and keeps the pickup code for sign-in',async()=>{
 const h=page('pages/auth/auth.vue'),token='a'.repeat(32),origin='http://192.168.1.44:18000';let scanner;h.uni.scanCode=o=>scanner=o;h.s.scanService();scanner.success({result:'zhiyouguide://claim?claim='+token+'&server='+encodeURIComponent(origin)});
 assert.equal(h.calls[0].url,origin+'/api/v1/tour-session/spots');h.calls[0].success({statusCode:200,data:{success:true}});await new Promise(r=>setImmediate(r));assert.equal(h.storage.get('station-pending-claim').token,token);assert.equal(h.storage.get('station-pending-claim').origin,origin)
})

test('sending an email code prevents a simultaneous service switch',()=>{
 const h=page('pages/auth/auth.vue');h.s.sendingCode=true;h.s.serviceAddress='https://guide.example.org';h.s.toggleConnection();h.s.connectService();assert.equal(h.s.showConnection,false);assert.equal(h.calls.length,0)
})

test('scanned pickup reads route and guides without consuming the code or defaulting the station guide',async()=>{
 const h=page('pages/claim/claim.vue');h.s.code='ABCD2345EFGH';h.s.scanned=true
 const run=h.s.prepare();assert.equal(h.calls.length,2);assert.ok(h.calls.some(c=>c.url.endsWith('/claim/preview-app')));assert.ok(h.calls.every(c=>!c.url.endsWith('/claim/receive-app')))
 h.calls.find(c=>c.url.endsWith('/claim/preview-app')).success({statusCode:200,data:{snapshot:{guide:{guide_id:1},route:{stops:[{spot_id:3,spot_name:'仁寿殿'}],total_minutes:30}}}})
 h.calls.find(c=>c.url.includes('/guides?')).success({statusCode:200,data:{success:true,data:{guide_list:[{guide_id:1,name:'站内接待员'},{guide_id:2,name:'另一位导游'}]}}});await run
 assert.equal(h.s.pickedGuideId,0);assert.equal(h.nav.length,0)
 await h.s.beginTour();assert.equal(h.calls.length,2);assert.equal(h.s.error,'请先选择数字人')
 h.s.pickedGuideId=2;const start=h.s.beginTour(),call=h.calls.at(-1);assert.equal(call.data.guide_id,2);assert.ok(call.url.endsWith('/claim/receive-app'));call.success({statusCode:200,data:{session_id:77,avatar_access_token:'scoped-77'}});await start
 assert.equal(h.storage.get('xingyun-tour-77'),'scoped-77');assert.equal(h.storage.has('station-pending-claim'),false);assert.equal(h.nav.at(-1),'/pages/tour/tour?sessionId=77')
})

test('pickup waits for sign-in while retaining the scanned route',async()=>{
 const h=page('pages/claim/claim.vue');h.storage.delete('token');h.s.code='ABCD2345EFGH';await h.s.prepare();assert.equal(h.calls.length,0);assert.equal(h.storage.get('station-pending-claim').token,'ABCD2345EFGH');assert.equal(h.nav.at(-1),'/pages/auth/auth')
})

test('Mine scanner opens guide selection instead of silently receiving a default tour',()=>{
 const h=page('pages/mine/mine.vue');let scanner;h.uni.scanCode=o=>scanner=o;h.s.scanRoute();scanner.success({result:'ABCD2345EFGH'});scanner.complete();assert.equal(h.calls.length,0);assert.match(h.nav.at(-1),/^\/pages\/claim\/claim\?claim=ABCD2345EFGH/)
})
