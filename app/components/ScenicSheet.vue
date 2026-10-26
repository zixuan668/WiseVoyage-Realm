<template>
  <view class="scenic-sheet-overlay" @tap="close">
    <view class="scenic-sheet-shade" @tap.stop="close" :style="{opacity:progress,transition:dragging?'none':undefined}"></view>
    <view class="scenic-sheet-panel" :class="{fit: fitContent}" :style="panelStyle" @tap.stop="" @touchstart="start" @touchmove="move" @touchend="end" @touchcancel="cancel">
      <view class="scenic-sheet-drag-zone" @touchstart.stop="start($event,true)" @touchmove.stop.prevent="move" @touchend.stop="end" @touchcancel.stop="cancel"><view class="scenic-sheet-grip"></view></view>
      <slot></slot>
    </view>
  </view>
</template>
<script>
export default {
  emits:['progress','closed','dragging'],
  props:{fitContent:{type:Boolean,default:false}},
  data(){return {visible:false,drag:0,dragging:false,startY:0,lastY:0,lastTime:0,velocity:0,height:0,scrollTop:0,canDrag:false,fromHandle:false,closing:false,closeTimer:null,openTimer:null}},
  computed:{
    progress(){return this.visible?Math.max(0,1-Math.max(0,this.drag)/(this.height||600)):0},
    panelStyle(){return {transform:this.visible?'translateY('+this.drag+'px)':'translateY(110%)',transition:this.dragging?'none':'transform 400ms cubic-bezier(.22,1.18,.36,1)'}}
  },
  mounted(){this.$nextTick(()=>{uni.createSelectorQuery().in(this).select('.scenic-sheet-panel').boundingClientRect(r=>{if(r)this.height=r.height}).exec();this.openTimer=setTimeout(()=>{this.visible=true;this.$emit('progress',1)},24)})},
  beforeUnmount(){clearTimeout(this.openTimer);clearTimeout(this.closeTimer)},
  methods:{
    setScroll(e){this.scrollTop=e.detail.scrollTop},
    close(){if(this.closing)return;this.closing=true;this.dragging=false;this.$emit('dragging',false);this.visible=false;this.$emit('progress',0);this.closeTimer=setTimeout(()=>this.$emit('closed'),400)},
    start(e,fromHandle=false){if(this.closing)return;const y=e.touches[0].clientY;this.startY=this.lastY=y;this.lastTime=Date.now();this.velocity=0;this.dragging=false;this.fromHandle=fromHandle;this.canDrag=fromHandle||this.scrollTop<=0},
    move(e){if(!this.canDrag||this.closing)return;const y=e.touches[0].clientY,now=Date.now(),delta=y-this.startY;if(delta<0&&!this.fromHandle&&!this.dragging)return;this.velocity=(y-this.lastY)/Math.max(1,now-this.lastTime);this.lastY=y;this.lastTime=now;this.dragging=true;this.$emit('dragging',true);this.drag=delta<0?-36*(1-Math.exp(delta/90)):delta;if(e.preventDefault)e.preventDefault();this.$emit('progress',this.progress)},
    end(){if(!this.dragging)return;this.dragging=false;if(this.drag>(this.height||600)/3||(this.drag>24&&this.velocity>.65&&Date.now()-this.lastTime<100)){this.close();return}this.cancel()},
    cancel(){this.dragging=false;this.$emit('dragging',false);this.drag=0;this.$emit('progress',1)}
  }
}
</script>
<style scoped>
.scenic-sheet-overlay{position:fixed!important;top:0;right:0;bottom:0;left:0;z-index:1200!important;overflow:hidden;display:flex;align-items:flex-end}
.scenic-sheet-shade{position:absolute;inset:0;background:rgba(18,17,35,.42);transition:opacity 400ms cubic-bezier(.22,1,.36,1)}
.scenic-sheet-panel{position:relative;width:100%;height:50vh;max-height:50vh;display:flex;flex-direction:column;box-sizing:border-box;padding:0;border-radius:36rpx 36rpx 0 0;background:#fff;overscroll-behavior:none;overflow:visible;box-shadow:0 -16px 50px rgba(20,15,50,.15);will-change:transform}
.scenic-sheet-panel.fit{height:auto;max-height:60vh}
.scenic-sheet-panel::after{content:"";position:absolute;left:0;right:0;top:calc(100% - 1px);height:80px;background:#fff;pointer-events:none}
.scenic-sheet-drag-zone{position:absolute;top:0;left:0;right:0;z-index:5;height:24px;display:flex;align-items:flex-start;justify-content:center;flex-shrink:0;touch-action:none}
.scenic-sheet-grip{margin-top:10px;width:66rpx;height:8rpx;border-radius:8rpx;background:rgba(255,255,255,.8);box-shadow:0 1px 4px rgba(30,25,50,.25);position:relative;z-index:2}
</style>
