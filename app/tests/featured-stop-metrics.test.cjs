// 路线详情弹层每站右侧的“步行时间 · 距离”来自 /tour-session/routes 的 walking_legs；
// 这里直接加载页面脚本的方法，避免依赖真机或编译产物。
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..')
const source=fs.readFileSync(path.join(root,'pages/featured/featured.vue'),'utf8')
const script=source.match(/<script>([\s\S]*?)<\/script>/)[1]
const code=script.replace(/^import .*$/gm,'').replace('export default','module.exports =')
function loadPage(){
  const context={module:{exports:{}},uni:{getSystemInfoSync:()=>({statusBarHeight:20}),request(){},navigateTo(){},navigateBack(){},reLaunch(){}},PageDock:{}}
  vm.createContext(context);vm.runInContext(code,context)
  return context.module.exports
}
const page=loadPage()
const detail={spot_names:['长廊','昆明湖','十七孔桥'],spot_ids:[52,54,55],walking_legs:[
  {from_id:52,to_id:54,meters:935,minutes:13,available:true},
  {from_id:54,to_id:55,meters:961,minutes:13,available:true},
]}
const vm_this=t=>({t,detail,formatMeters:page.methods.formatMeters})

test('route detail marks time and distance to the next stop, and the final stop',()=>{
  const self=vm_this(key=>key)
  assert.equal(page.methods.stopMetric.call(self,0),'步行 13分钟 · 935 m')
  assert.equal(page.methods.stopMetric.call(self,1),'步行 13分钟 · 961 m')
  assert.equal(page.methods.stopMetric.call(self,2),'终点')
})

test('route detail degrades when the walking leg is unavailable',()=>{
  const missing=vm_this(key=>key)
  missing.detail={...detail,walking_legs:[{available:false,meters:null,minutes:null}]}
  assert.equal(page.methods.stopMetric.call(missing,0),'暂无步行数据')
  const absent=vm_this(key=>key)
  absent.detail={spot_names:['长廊','昆明湖']}
  assert.equal(page.methods.stopMetric.call(absent,0),'暂无步行数据')
})

test('walking legs of one kilometre or more use kilometres',()=>{
  assert.equal(page.methods.formatMeters(999),'999 m')
  assert.equal(page.methods.formatMeters(1896),'1.9 km')
})

test('the new labels have English translations',()=>{
  const context={appUiEnglish:require(path.join(root,'common/ui.en.json')),webEnglish:require(path.join(root,'../frontend/src/i18n/en.json'))}
  vm.createContext(context)
  vm.runInContext(fs.readFileSync(path.join(root,'common/tour-language.js'),'utf8').replace(/^import .*$/gm,'').replace(/export /g,'')+'\nglobalThis.translate=translateTour',context)
  const cjk=/[\u4e00-\u9fff]/
  for(const key of ['步行','分钟','终点','暂无步行数据'])assert.doesNotMatch(context.translate(key,'en'),cjk,'missing English for '+key)
})
