const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm')
const source=fs.readFileSync('frontend/src/views/scenic-app/ScenicDetailView.vue','utf8')
function state(place,catalog=[],coverMap={}){
 const c={current:{value:place},catalog:{value:catalog},coverMap,bridge:{name:'十七孔桥',hero:{src:'/bridge.jpg'},gallery:[{src:'/bridge.jpg'}],audio:{seconds:100}},computed:fn=>({get value(){return fn()}})}
 vm.createContext(c);vm.runInContext(source.slice(source.indexOf('const spot = computed'),source.indexOf('function choosePlace'))+'\nglobalThis.result={spot,galleryPhotos}',c);return c.result
}
test('empty catalog never exposes the default bridge text or image',()=>{const s=state();assert.equal(s.spot.value.name,'');assert.equal(s.spot.value.hero.src,'');assert.equal(s.galleryPhotos.value.length,0)})
test('a scenic place without its own cover never borrows a bridge photo',()=>{const p={id:51,name:'仁寿殿',description:'真实介绍'};const s=state(p,[p]);assert.equal(s.galleryPhotos.value[0].src,'')})
test('loading cannot mount scenic hero or intro content',()=>{assert.match(source,/v-if="current" class="intro__hero"/);assert.match(source,/v-if="current" class="intro__sheet"/)})
