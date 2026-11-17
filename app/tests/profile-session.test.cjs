const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path')
function page(){
 const storage={token:'old-token',username:'old-user',user_id:1},requests=[]
 const uni={getStorageSync:k=>storage[k],setStorageSync:(k,v)=>storage[k]=v,removeStorageSync:k=>delete storage[k],request:r=>requests.push(r),showToast(){},reLaunch(){}}
 const context={uni,NocturneConfirm:{},AuthPage:{},BASE_URL:'',assetUrl:v=>v,translateTour:v=>v,console}
 vm.createContext(context)
 const src=fs.readFileSync(path.join(__dirname,'../pages/mine/mine.vue'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
 vm.runInContext(src.replace(/^import .*$/gm,'').replace('export default','globalThis.options='),context)
 const o=context.options,s=o.data();for(const[k,f]of Object.entries(o.methods))s[k]=f.bind(s)
 s.translateAiChatHistory=()=>{};return {o,s,storage,requests}
}
test('profile never renders an unverified cached account',()=>{const {s}=page();assert.equal(s.username,'');assert.equal(s.userId,'')})
test('a late response from a previous account cannot overwrite current account',()=>{
 const {s,o,storage,requests}=page();o.onShow.call(s);storage.token='new-token';o.onShow.call(s)
 requests[1].success({statusCode:200,data:{success:true,data:{username:'new-user',user_id:2,user_no:'0002'}}})
 requests[0].success({statusCode:200,data:{success:true,data:{username:'old-user',user_id:1}}})
 assert.equal(s.username,'new-user');assert.equal(storage.username,'new-user');assert.equal(s.userId,'0002')
})
test('an expired old request cannot clear a new login',()=>{
 const {s,o,storage,requests}=page();o.onShow.call(s);storage.token='new-token'
 requests[0].success({statusCode:401});assert.equal(storage.token,'new-token')
})
