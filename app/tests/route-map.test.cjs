const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm')
const root=path.resolve(__dirname,'..')
test('scrolling route detail uses a DOM map instead of an overlapping native map layer',()=>{
  const overview=fs.readFileSync(path.join(root,'components/RouteOverview.vue'),'utf8')
  assert.doesNotMatch(overview,/<map\s/,'Native map must not be embedded in the route scroll panel')
  assert.match(overview,/<RouteRoadMap\s/)
})
function renderer(){
  const fits=[],lines=[],observers=[],maps=[]
  const map={invalidateSize(){},stop(){},closePopup(){},fitBounds(bounds,options){fits.push({bounds,options})},remove(){this.removed=true}}
  const L={map(){maps.push(map);return map},control:{zoom:()=>({addTo(){}})},tileLayer:()=>({addTo(){return this},on(){return this}}),layerGroup:()=>({addTo(){return this},clearLayers(){}}),polyline(points,style){lines.push({points,style});return{on(){return this},addTo(){return this},bringToFront(){}}},divIcon:o=>o,marker:()=>({bindPopup(){return this},addTo(){}}),latLngBounds:points=>points}
  class Observer{constructor(callback){this.callback=callback;observers.push(this)}observe(){}disconnect(){this.disconnected=true}}
  const win={L,__zhiyouLeafletReady:true,ResizeObserver:Observer,MutationObserver:Observer,requestAnimationFrame:()=>1,cancelAnimationFrame(){}},doc={body:{},createElement:()=>({textContent:''})}
  const context={Promise,setTimeout,clearTimeout,JSON,Number};vm.createContext(context)
  vm.runInContext(fs.readFileSync(path.join(root,'common/route-map-runtime.js'),'utf8').replace(/export /g,'')+'\nglobalThis.api={createRouteMap,routeLineStyle}',context)
  const element={isConnected:true,addEventListener(){},removeEventListener(){}},events=[],controller=context.api.createRouteMap(element,e=>events.push(e),win,doc)
  const points=[{latitude:40,longitude:116},{latitude:40.07,longitude:116.03},{latitude:40.01,longitude:116.01}]
  const payload={data:{points,markers:[],polyline:[{points}],legIndexes:[0]},markerLabels:{},activeLeg:0,original:false,fitCounter:0}
  return{controller,payload,fits,lines,observers,maps,map,element,api:context.api,events}
}
test('all road bends and stops determine padded bounds; choosing another leg preserves manual zoom',async()=>{
  const h=renderer();await h.controller.update(h.payload)
  assert.equal(h.fits.length,1);assert.equal(h.fits[0].bounds.length,3);assert.equal(h.fits[0].bounds[1][0],40.07)
  assert.deepEqual(Array.from(h.fits[0].options.padding),[28,28]);assert.equal(h.fits[0].options.maxZoom,17)
  await h.controller.update({...h.payload,activeLeg:1});assert.equal(h.fits.length,1)
  await h.controller.update({...h.payload,fitCounter:1});assert.equal(h.fits.length,2)
})
test('map strokes match the Web round caps, highlight and original-route colors',()=>{
  const h=renderer(),active=h.api.routeLineStyle(false,true),normal=h.api.routeLineStyle(false,false),original=h.api.routeLineStyle(true,false)
  assert.equal(active.color,'#513dbe');assert.equal(active.weight,6);assert.equal(active.lineCap,'round');assert.equal(active.lineJoin,'round')
  assert.equal(normal.color,'#a69acb');assert.equal(normal.weight,4);assert.equal(normal.opacity,.7);assert.equal(original.color,'#8b96ac')
  h.controller.destroy()
})
test('removing a scrolled dialog disposes its map and ignores a late renderer update',async()=>{
  const h=renderer();await h.controller.update(h.payload);h.element.isConnected=false;h.observers[0].callback()
  assert.equal(h.map.removed,true);assert.ok(h.observers.every(o=>o.disconnected));await h.controller.update(h.payload);assert.equal(h.maps.length,1)
})
