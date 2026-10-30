<template>
  <view v-if="ready" class="tour-orb" :class="{dragging,snapping}" :style="{left:x+'px',top:y+'px'}" role="button" :aria-label="label || t('开始导览')" @touchstart.stop="start" @touchmove.stop.prevent="move" @touchend.stop="end" @touchcancel.stop="cancel" @tap.stop="activate">
    <image class="orb-pin" src="/static/tour-orb-pin.svg" mode="aspectFit" aria-hidden="true" />
  </view>
</template>
<script>
export default {
  props:{count:Number,label:{type:String,default:''},icon:{type:String,default:'▶'},variant:{type:String,default:'light'}},emits:['activate','dragging'],
  data(){return{ready:false,snapping:false,x:12,y:400,width:375,height:750,top:20,bottom:0,side:'right',dragging:false}},
  mounted(){this.layout();this.ready=true;this._resize=()=>{this.cancel();this.layout()};uni.onWindowResize?.(this._resize)},
  beforeUnmount(){clearTimeout(this._snapTimer);clearTimeout(this._hold);uni.offWindowResize?.(this._resize);this.$emit('dragging',false)},
  methods:{
    clampY(y){return Math.max(this.top+12,Math.min(y,Math.max(this.top+12,this.height-this.bottom-164)))},
    layout(){const i=uni.getWindowInfo?uni.getWindowInfo():uni.getSystemInfoSync();const first=!this._laidOut;this.width=i.windowWidth;this.height=i.windowHeight;this.top=i.safeAreaInsets?.top||i.statusBarHeight||0;this.bottom=i.safeAreaInsets?.bottom||0;this.x=this.side==='left'?12:Math.max(12,this.width-86);this.y=this.clampY(first?this.height-this.bottom-180:this.y);this._laidOut=true},
    start(e){if(!e.touches?.length)return;clearTimeout(this._snapTimer);this.snapping=false;clearTimeout(this._hold);const p=e.touches[0];this._touch={x:p.clientX,y:p.clientY,left:this.x,top:this.y};this._hold=setTimeout(()=>{if(!this._touch)return;this.dragging=true;this._block=Date.now()+600;this.$emit('dragging',true);try{uni.vibrateShort({type:'light'})}catch(_){}},240)},
    move(e){if(!this._touch||!e.touches?.length)return;const p=e.touches[0],dx=p.clientX-this._touch.x,dy=p.clientY-this._touch.y;if(!this.dragging){if(Math.abs(dx)+Math.abs(dy)>10){clearTimeout(this._hold);this._block=Date.now()+600}return}this.x=Math.max(12,Math.min(this.width-86,this._touch.left+dx));this.y=this.clampY(this._touch.top+dy)},
    end(){clearTimeout(this._hold);if(this.dragging){this.side=this.x+37<this.width/2?'left':'right';this.dragging=false;this.snapping=true;this._snapTimer=setTimeout(()=>{this.snapping=false},400);this.x=this.side==='left'?12:Math.max(12,this.width-86);this._block=Date.now()+600}this._touch=null;this.$emit('dragging',false)},
    cancel(){this.end();this._block=Date.now()+600},
    activate(){if(this.dragging||Date.now()<(this._block||0))return;this.$emit('activate')},
  },
}
</script>
<style scoped>
.tour-orb{position:fixed!important;width:74px;height:74px;box-sizing:border-box;border-radius:50%;z-index:990!important;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.22);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.48);box-shadow:0 0 20px rgba(139,92,246,.15),0 5px 16px rgba(121,82,213,.12);touch-action:none;user-select:none;transition:transform 180ms,box-shadow 180ms}
.orb-pin{width:36px;height:36px;pointer-events:none}
.tour-orb:active{transform:scale(.95)}
.tour-orb.dragging{transition:none;transform:scale(1.06);box-shadow:0 0 24px rgba(139,92,246,.22),0 9px 22px rgba(121,82,213,.16)}
.tour-orb.snapping{transition:left 360ms cubic-bezier(.2,1.25,.35,1),top 360ms cubic-bezier(.2,1.25,.35,1),transform 180ms,box-shadow 180ms}
</style>
