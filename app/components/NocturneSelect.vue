<template>
  <view class="select-overlay" @tap="requestClose">
    <view class="select-panel" role="dialog" aria-modal="true" :aria-label="$t(title)" :style="panelStyle" @tap.stop>
      <view class="select-head">
        <text class="select-title">{{ $t(title) }}</text>
        <button class="select-close" :aria-label="$t('关闭')" @tap.stop="requestClose"><text class="iconfont icon-close" aria-hidden="true"></text></button>
      </view>
      <scroll-view scroll-y class="select-options" :style="{height:Math.min(options.length*56,448)+'px'}">
        <button v-for="(option,index) in options" :key="index" class="select-option" :class="{selected:index===selectedIndex}" :aria-pressed="index===selectedIndex" @tap="choose(index)">
          <text>{{ $t(option) }}</text><text v-if="index===selectedIndex" aria-hidden="true" class="iconfont icon-check"></text>
        </button>
      </scroll-view>
    </view>
  </view>
</template>
<script>
export default {
  props: {title:{type:String,default:''},options:{type:Array,default:()=>[]},selectedIndex:{type:Number,default:-1},anchor:{type:Object,default:null}},
  emits:['change','close'],
  data(){return{origin:'50% 85%',opened:false,closing:false,openTimer:null,closeTimer:null}},
  computed:{
    panelStyle(){
      const shown=this.opened&&!this.closing
      return {
        transformOrigin:this.origin,
        transform:shown?'scale(1)':'scale(0.05)',
        opacity:shown?1:0,
        transition:this.closing?'transform 300ms cubic-bezier(.4,0,.75,.3), opacity 220ms ease':'transform 380ms cubic-bezier(.22,1.25,.36,1), opacity 220ms ease'
      }
    }
  },
  mounted(){
    this.$nextTick(()=>{
      this.measureOrigin()
      this.openTimer=setTimeout(()=>{this.opened=true},24)
    })
  },
  beforeUnmount(){clearTimeout(this.openTimer);clearTimeout(this.closeTimer)},
  methods:{
    measureOrigin(){
      if(!this.anchor)return
      const self=this
      uni.createSelectorQuery().in(this).select('.select-panel').boundingClientRect(function(r){
        if(!r)return
        const ox=Math.round(self.anchor.x-r.left)
        const oy=Math.round(self.anchor.y-r.top)
        self.origin=ox+'px '+oy+'px'
      }).exec()
    },
    choose(index){this.$emit('change',{detail:{value:index}})},
    requestClose(){
      if(this.closing)return
      this.closing=true
      this.closeTimer=setTimeout(()=>{this.$emit('close')},300)
    }
  },
}
</script>
<style scoped>
.select-overlay{position:fixed;inset:0;z-index:3200;display:flex;align-items:center;justify-content:center;background:rgba(30,41,59,.28);padding:40rpx;box-sizing:border-box;overflow:hidden}
.select-panel{width:100%;max-width:620px;max-height:62vh;display:flex;flex-direction:column;background:var(--ng-surface,#fff);border-radius:32rpx;padding:26rpx 22rpx 20rpx;box-sizing:border-box;color:var(--ng-text,#1f2937);box-shadow:0 24px 60px rgba(20,15,50,.22);overflow:hidden}
.select-head{display:flex;align-items:center;justify-content:space-between;gap:12rpx;flex-shrink:0;padding:2rpx 2rpx 16rpx 28rpx}
.select-title{display:block;flex:1;min-width:0;font-size:32rpx;font-weight:700;line-height:1.5;padding:0}
.select-close{flex:0 0 auto;width:60rpx;height:60rpx;min-height:0;margin:0;padding:0;display:flex;align-items:center;justify-content:center;font-size:34rpx;line-height:1;color:var(--ng-secondary);background:rgba(99,102,241,0.08);border-radius:16rpx}
.select-close::after{border:0}
.select-options{width:100%;flex:1 1 auto;min-height:0;box-sizing:border-box;overflow:hidden}.select-option{display:flex;align-items:center;justify-content:space-between;gap:16rpx;min-height:56px;padding:12px 14px;margin:0;width:100%;box-sizing:border-box;text-align:left;font-size:16px;line-height:1.5;background:transparent;color:inherit;border-radius:16rpx}.select-option::after,.select-cancel::after{border:0}
.select-option.selected{background:var(--ng-raised,#eef2ff);color:var(--ng-accent-text,#4338ca);font-weight:600}.select-option:active{background:var(--ng-raised,#eef2ff)}

</style>
