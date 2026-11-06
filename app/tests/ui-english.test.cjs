const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path')
const root=path.resolve(__dirname,'..'),cjk=/[\u4e00-\u9fff]/
const english=require(path.join(root,'common/ui.en.json'))
const locations=JSON.parse(fs.readFileSync(path.join(root,'..','data','summer_palace_locations.json'),'utf8'))
// 英文界面下的景点名称来自 common/ui.en.json；缺少条目时界面会回退成中文。
// 当前内容包只包含颐和园目录中的景点。

test('connection, pickup and failure recovery controls have readable English labels',()=>{
 const vm=require('node:vm'),context={appUiEnglish:english,webEnglish:require(path.join(root,'../frontend/src/i18n/en.json'))}
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'common/tour-language.js'),'utf8').replace(/^import .*$/gm,'').replace(/export /g,'')+'\nglobalThis.translate=translateTour',context)
 for(const key of ['连接服务站','连接成功，请登录','服务地址','扫码连接','领取电脑上的路线','输入12位领取码','扫描路线二维码','领取路线','稍后领取','领取码格式不正确','收藏状态加载失败','浏览记录保存失败','收藏失败，请重试','景点加载失败，请检查网络后重试','撤销','已清除历史记录','已清空当前对话'])assert.doesNotMatch(context.translate(key,'en'),cjk,'missing English for '+key)
})
test('every scenic stop offered to visitors has a Chinese-free English name',()=>{
 const names=Object.keys(locations.spots)
 assert.equal(names.length,16)
 for(const name of names){
  const value=english[name]
  assert.ok(value,'missing English name for '+name)
  assert.doesNotMatch(value,cjk,'English name for '+name+' still contains Chinese characters')
 }
})
