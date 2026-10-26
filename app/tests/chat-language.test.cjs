const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
function helper(){const c={};vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../common/chat-language.js'),'utf8').replace(/export /g,''),c);return c.localizeChatMessages}
function context(storage=new Map()){const c={uni:{getStorageSync:key=>storage.get(key),setStorageSync:(key,value)=>storage.set(key,value)}};vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../common/chat-language.js'),'utf8').replace(/export /g,''),c);return c}
test('background preparation retains visible Chinese and cached English applies synchronously',async()=>{
 const c=context(),cache=c.getChatTranslationCache('id:17'),message={role:'ai',content:'预备的讲解'},options={lists:[[message]],field:'content',cache,isCurrent:()=>true,translate:async(texts,target)=>{assert.equal(target,'en');return ['Prepared narration.']}}
 await c.warmChatTranslations(options);assert.equal(message.content,'预备的讲解');assert.equal(message.translations.en,'Prepared narration.')
 const pending=c.localizeChatMessages({...options,target:'en',translate:()=>assert.fail('switch must read cache')});assert.equal(message.content,'Prepared narration.');await pending
})
test('a language switch joins background work without submitting duplicate translation',async()=>{
 const c=context(),cache=new Map(),message={content:'提前翻译'},options={lists:[[message]],field:'content',cache,isCurrent:()=>true};let resolve,calls=0
 const warm=c.warmChatTranslations({...options,translate:()=>{calls++;return new Promise(r=>resolve=r)}})
 const display=c.localizeChatMessages({...options,target:'en',translate:()=>assert.fail('duplicate request')});assert.equal(calls,1);resolve(['Translate in advance.']);await Promise.all([warm,display]);assert.equal(message.content,'Translate in advance.')
})
test('persisted bilingual cache survives reopening and remains isolated by account',async()=>{
 const storage=new Map(),c=context(storage),cache=c.getChatTranslationCache('id:17'),options={lists:[[{content:'保存的讲解'}]],field:'content',cache,isCurrent:()=>true,translate:async()=>['Saved narration.']}
 await c.warmChatTranslations(options);const reopened=context(storage),same=reopened.getChatTranslationCache('id:17'),other=reopened.getChatTranslationCache('id:18')
 assert.equal(same.get('保存的讲解').en,'Saved narration.');assert.equal(other.size,0)
})
test('a superseded request is retried for a still-current caller instead of leaving its text untranslated',async()=>{
 const c=context(),cache=new Map(),message={content:'新的讲解'};let current=true,release
 const old=c.localizeChatMessages({lists:[[message]],field:'content',cache,target:'en',isCurrent:()=>current,translate:()=>new Promise(r=>release=r)})
 const next=c.localizeChatMessages({lists:[[message]],field:'content',cache,target:'en',isCurrent:()=>true,translate:async()=>['New narration.']})
 current=false;release(['Old result.']);await Promise.all([old,next]);assert.equal(message.content,'New narration.')
})
test('a failed shared request stays handled while a separate translation is still running',async()=>{
 const c=context(),cache=new Map(),first={content:'共享消息'},second={content:'另一条消息'};let fail,finish
 const options={field:'content',cache,target:'en',isCurrent:()=>true}
 const warm=c.localizeChatMessages({...options,lists:[[first]],translate:()=>new Promise((yes,no)=>fail=no)})
 const display=c.localizeChatMessages({...options,lists:[[first,second]],translate:()=>new Promise(yes=>finish=yes)})
 const checks=[assert.rejects(warm,/offline/),assert.rejects(display,/offline/)]
 fail(new Error('offline'));await new Promise(r=>setImmediate(r));finish(['Another message.']);await Promise.all(checks)
})
test('ready current messages apply without waiting for slower archived translation batches',async()=>{
 const c=context(),cache=new Map(),messages=Array.from({length:5},(_,i)=>({content:'讲解'+i}));let release
 const pending=c.localizeChatMessages({lists:[messages],field:'content',cache,target:'en',concurrency:2,isCurrent:()=>true,translate:async texts=>{if(texts.length===1)return new Promise(r=>release=r);return Array.from(texts,()=> 'Ready message.')}})
 await new Promise(r=>setImmediate(r));assert.equal(messages[0].content,'Ready message.');assert.equal(messages[4].content,'讲解4');release(['Last message.']);await pending
})
test('current and history questions and answers translate once and restore exact originals',async()=>{
 const localize=helper(),cache=new Map(),a={role:'user',content:'介绍仁寿殿'},b={role:'ai',content:'仁寿殿是理政中心。',segments:[{t:'旧文本'}],cursor:true},history={...b};let calls=0
 const options={lists:[[a,b],[a,history]],field:'content',cache,isCurrent:()=>true,target:'en',translate:async texts=>{calls++;assert.deepEqual(Array.from(texts).map(JSON.parse),['介绍仁寿殿','仁寿殿是理政中心。']);return ['Introduce the Hall of Benevolence and Longevity.','The hall was a center of government.']}}
 await localize(options);assert.equal(calls,1);assert.equal(b.content,history.content);assert.equal(b.segments,undefined);assert.equal(b.cursor,false)
 await localize({...options,target:'zh',translate:()=>assert.fail('must restore cache')});assert.equal(a.content,'介绍仁寿殿');assert.equal(b.content,'仁寿殿是理政中心。')
 const refreshed={role:'ai',message:'仁寿殿是理政中心。'};await localize({...options,lists:[[refreshed]],field:'message',translate:()=>assert.fail('reuse cached tour reply')});assert.equal(refreshed.message,'The hall was a center of government.')
})
test('superseded language and account requests cannot alter chat or cache',async()=>{
 const localize=helper(),cache=new Map(),m={content:'原文'};let current=true,resolve
 const pending=localize({lists:[[m]],field:'content',target:'en',cache,isCurrent:()=>current,translate:()=>new Promise(r=>resolve=r)})
 current=false;resolve(['Translated.']);await pending;assert.equal(m.content,'原文');assert.equal(cache.size,0)
})
test('translation failures preserve original content and allow retry',async()=>{
 const localize=helper(),m={message:'原文'},options={lists:[[m]],field:'message',target:'en',cache:new Map(),isCurrent:()=>true}
 await assert.rejects(localize({...options,translate:async()=>['还是中文']}));assert.equal(m.message,'原文')
 await localize({...options,translate:async()=>['Original text.']});assert.equal(m.message,'Original text.')
})
test('long replies retain every character despite the endpoint input limit',async()=>{
 const localize=helper(),original='长篇讲解😀'.repeat(1000),m={content:original},parts=[]
 await localize({lists:[[m]],field:'content',target:'en',cache:new Map(),isCurrent:()=>true,translate:async texts=>Array.from(texts,text=>{assert.ok(text.length<4000);parts.push(JSON.parse(text));return 'Translated section.'})})
 assert.equal(parts.join(''),original);assert.ok(parts.length>4);assert.equal(m.translations.zh,original);assert.equal(m.content.split('\n').length,parts.length)
})
