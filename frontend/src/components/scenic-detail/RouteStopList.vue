<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'
import { Close } from '@/icons'
type Stop={spot_id:number;spot_name:string;visit_minutes:number}
const props=defineProps<{stops:Stop[];disabled:boolean}>()
const emit=defineEmits<{reorder:[ids:number[]];remove:[id:number]}>()
const rows=ref<Stop[]>([])
const root=ref<HTMLElement|null>(null), grabbed=ref<number|null>(null)
let timer:ReturnType<typeof setTimeout>|undefined, original:number[]=[],startX=0,startY=0,mouseTarget:HTMLElement|null=null
watch(()=>props.stops,value=>{if(grabbed.value===null)rows.value=[...value]},{immediate:true})
function cancel(){
 clearTimeout(timer);timer=undefined;grabbed.value=null;mouseTarget=null
 rows.value=[...props.stops]
}
function begin(id:number,x:number,y:number){
 if(props.disabled)return
 clearTimeout(timer);startX=x;startY=y;original=rows.value.map(s=>s.spot_id)
 timer=setTimeout(()=>{grabbed.value=id;timer=undefined},220)
}
function move(x:number,y:number,event:Event){
 if(grabbed.value===null){
  if(Math.hypot(x-startX,y-startY)>8){clearTimeout(timer);timer=undefined}
  return
 }
 if(event.cancelable)event.preventDefault()
 const elements=[...root.value!.querySelectorAll<HTMLElement>('[data-stop]')]
 const index=elements.findIndex(e=>y<e.getBoundingClientRect().top+e.getBoundingClientRect().height/2)
 const to=index<0?rows.value.length-1:index
 const from=rows.value.findIndex(s=>s.spot_id===grabbed.value)
 if(from!==to){const next=[...rows.value];next.splice(to,0,...next.splice(from,1));rows.value=next}
 const scroll=root.value?.closest<HTMLElement>('.route-body')
 if(scroll){const bounds=scroll.getBoundingClientRect();if(y>bounds.bottom-40)scroll.scrollTop+=12;else if(y<bounds.top+40)scroll.scrollTop-=12}
}
function finish(){
 clearTimeout(timer);timer=undefined
 if(grabbed.value!==null){
  const ids=rows.value.map(s=>s.spot_id)
  grabbed.value=null
  if(ids.join(',')!==original.join(','))emit('reorder',ids)
 }
}
function touchStart(id:number,e:TouchEvent){if((e.target as HTMLElement).closest('button'))return;const p=e.touches[0];if(p)begin(id,p.clientX,p.clientY)}
function pointerStart(id:number,e:PointerEvent){
 if(e.pointerType!=='mouse'||(e.target as HTMLElement).closest('button'))return
 mouseTarget=e.currentTarget as HTMLElement;mouseTarget.setPointerCapture(e.pointerId);begin(id,e.clientX,e.clientY)
}
function keyMove(index:number,direction:number){
 if(props.disabled)return
 const next=[...rows.value],target=index+direction
 if(target<0||target>=next.length)return
 next.splice(target,0,...next.splice(index,1));rows.value=next;emit('reorder',next.map(s=>s.spot_id))
}
onBeforeUnmount(cancel)
</script>
<template>
 <ol ref="root" class="editable-stops" aria-label="长按景点拖动排序"><TransitionGroup name="stop-order">
  <li v-for="(stop,index) in rows" :key="stop.spot_id" :data-stop="stop.spot_id" :class="{grabbed:grabbed===stop.spot_id}"
    tabindex="0" :aria-label="stop.spot_name+'，长按拖动或使用上下方向键排序'"
    @touchstart.passive="touchStart(stop.spot_id,$event)" @touchmove="e=>{const p=e.touches[0];if(p)move(p.clientX,p.clientY,e)}"
    @touchend="finish" @touchcancel="cancel" @contextmenu.prevent
    @pointerdown="pointerStart(stop.spot_id,$event)" @pointermove="e=>{if(e.pointerType==='mouse')move(e.clientX,e.clientY,e)}"
    @pointerup="e=>{if(e.pointerType==='mouse')finish()}" @pointercancel="e=>{if(e.pointerType==='mouse')cancel()}"
    @keydown.up.prevent="keyMove(index,-1)" @keydown.down.prevent="keyMove(index,1)">
   <i>{{index+1}}</i><strong>{{stop.spot_name}}</strong><span>{{stop.visit_minutes}} 分钟</span>
   <button :disabled="disabled||grabbed!==null" :aria-label="'删除'+stop.spot_name" @click="emit('remove',stop.spot_id)"><Close :size="17"/></button>
  </li>
 </TransitionGroup></ol>
</template>
<style scoped>
.editable-stops{list-style:none;padding:0 10px;margin:0 12px;background:#fff;border-radius:16px;user-select:none;-webkit-user-select:none;-webkit-touch-callout:none}
li{display:flex;align-items:center;gap:10px;min-height:60px;padding:0 3px;border-bottom:1px solid #f0edf7;touch-action:pan-y;transition:transform 200ms cubic-bezier(.2,.8,.2,1),box-shadow 200ms,background 200ms;will-change:transform}
li:last-child{border:0}
li.grabbed{background:#f1ecff;border-radius:12px;touch-action:none;position:relative;z-index:2;transform:scale(1.02);box-shadow:0 8px 22px rgba(80,60,150,.18);transition:box-shadow 160ms,background 160ms}
i{display:grid;place-items:center;width:26px;height:26px;flex:none;border-radius:50%;background:linear-gradient(135deg,rgba(255,255,255,.96),rgba(242,238,252,.92));border:1px solid rgba(120,100,190,.2);box-shadow:inset 0 1px 0 #fff,0 3px 8px -6px rgba(40,30,70,.32);color:#3a3150;font-size:13px;font-weight:600;font-style:normal}
strong{flex:1;font-size:16px;font-weight:500}span{font-size:13px;color:#80798a}
button{width:36px;height:44px;display:grid;place-items:center;border:0;background:transparent;color:#80798a;-webkit-tap-highlight-color:transparent}
.stop-order-move{transition:transform 220ms cubic-bezier(.2,.8,.2,1)}
@media(prefers-reduced-motion:reduce){.stop-order-move{transition:none}}
</style>
