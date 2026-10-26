const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..')
function environment(){
 const storage={token:'tour-token',user_id:17,username:'visitor'}
 const uni={getStorageSync:k=>storage[k],setStorageSync:(k,v)=>{storage[k]=v}}
 const context={uni,console,JSON}
 vm.createContext(context)
 vm.runInContext(fs.readFileSync(path.join(root,'common/tour-chat-log.js'),'utf8').replace(/^export /gm,''),context)
 return{storage,api:context}
}
test('tour Q&A is appended to the account-scoped AI guide history',()=>{
 const {storage,api}=environment()
 api.appendTourChatMessage('user','玉澜堂有什么历史故事？')
 api.appendTourChatMessage('guide','玉澜堂是光绪帝在颐和园的寝宫。')
 const key='ai_chat_state:'+encodeURIComponent('id:17')
 const state=JSON.parse(storage[key])
 assert.equal(state.messages.length,2)
 assert.deepEqual(state.messages.map(m=>m.role),['user','ai'])
 assert.deepEqual(state.messages.map(m=>m.source),['tour','tour'])
 storage.user_id=18
 api.appendTourChatMessage('user','Another account question')
 assert.equal(JSON.parse(storage['ai_chat_state:'+encodeURIComponent('id:18')]).messages.length,1)
 assert.equal(JSON.parse(storage[key]).messages.length,2)
})
test('blank tour questions and answers are not written to history',()=>{
 const {storage,api}=environment()
 api.appendTourChatMessage('user','   ')
 api.appendTourChatMessage('ai',null)
 assert.equal(storage['ai_chat_state:'+encodeURIComponent('id:17')],undefined)
})
