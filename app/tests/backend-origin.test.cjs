const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
function config(platform,mode='development',saved='',releaseOrigin=''){
  const source=fs.readFileSync(path.join(__dirname,'../common/config.js'),'utf8')
    .replace(/\/\/ #ifdef H5[\s\S]*?\/\/ #endif/g,'')
    .replace(/import\.meta\.env\.MODE/g,JSON.stringify(mode)).replace(/import\.meta\.env\.VITE_APP_SERVER_ORIGIN/g,JSON.stringify(releaseOrigin)).replace(/export /g,'')
  const storage=new Map([['station-server-origin',saved],['token','old-token'],['login_provider','password']])
  const context={uni:{getSystemInfoSync:()=>({platform}),getStorageSync:k=>storage.get(k),setStorageSync:(k,v)=>storage.set(k,v),removeStorageSync:k=>storage.delete(k)}}
  vm.createContext(context);vm.runInContext(source+'\nglobalThis.result={SERVER_ORIGIN,BASE_URL,LAN_SERVER_ORIGIN,assetUrl,normalizeServiceOrigin,setServiceOrigin}',context)
  context.result.storage=storage
  return context.result
}
test('iPhone development connects to the computer LAN address rather than its own loopback',()=>{
  const c=config('ios');assert.equal(c.SERVER_ORIGIN,c.LAN_SERVER_ORIGIN);assert.doesNotMatch(c.SERVER_ORIGIN,/localhost|127\.0\.0\.1/)
  assert.equal(c.BASE_URL,c.LAN_SERVER_ORIGIN+'/api/v1')
  assert.equal(c.assetUrl('http://127.0.0.1:18000/api/v1/files/photo.jpg'),c.LAN_SERVER_ORIGIN+'/api/v1/files/photo.jpg')
})
test('Android development retains USB reverse forwarding',()=>{assert.equal(config('android').SERVER_ORIGIN,'http://127.0.0.1:18000')})
test('production builds use the configured LAN address on both native platforms',()=>{
  for(const platform of ['android','ios']){const c=config(platform,'production');assert.equal(c.SERVER_ORIGIN,c.LAN_SERVER_ORIGIN)}
})
test('an explicitly chosen service-station server stays selected on iPhone',()=>{
  const c=config('ios','development','http://192.168.1.20:18000');assert.equal(c.SERVER_ORIGIN,'http://192.168.1.20:18000')
})

test('release service origin can use HTTPS and rejects credentials, paths and public plain HTTP',()=>{
 const c=config('ios','production','','https://guide.example.org');assert.equal(c.SERVER_ORIGIN,'https://guide.example.org')
 for(const invalid of ['https://user:pass@example.org','https://example.org/path','https://example.org?token=secret','http://example.org','https://example.org:70000'])assert.equal(c.normalizeServiceOrigin(invalid),'')
 assert.equal(c.normalizeServiceOrigin(' https://guide.example.org/ '),'https://guide.example.org')
 assert.equal(c.normalizeServiceOrigin('http://192.168.1.2:18000'),'http://192.168.1.2:18000')
})

test('changing the service signs out the old service account, while the same origin keeps it',()=>{
 const c=config('ios','production','','https://guide.example.org');c.setServiceOrigin('https://guide.example.org/');assert.equal(c.storage.get('token'),'old-token')
 c.setServiceOrigin('http://192.168.1.2:18000');assert.equal(c.storage.has('token'),false);assert.equal(c.storage.has('login_provider'),false);assert.equal(c.storage.get('station-server-origin'),'http://192.168.1.2:18000')
})
