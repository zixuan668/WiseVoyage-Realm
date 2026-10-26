<template>
  <view v-if="displayed" class="route-overview">
    <view v-if="compare" class="route-comparison"><button :class="{on:!original}" @tap="original=false">{{ t('调整后') }}</button><button :class="{on:original}" @tap="original=true">{{ t('调整前') }}</button></view>
    <view class="route-metrics"><view><text class="metric-value">{{ (displayed.stops||[]).length }}{{ t('站') }}</text></view><view><text>{{ t('预计步行') }}</text><text class="metric-value">{{ distance(displayed.walking_meters) }}</text></view><view><text>{{ t('预计用时') }}</text><text class="metric-value">{{ displayed.total_minutes ?? '—' }}{{ t('分钟') }}</text></view></view>
    <RouteRoadMap v-if="showMap&&mapData.points.length" :data="mapData" :original="original" :active-leg="activeLeg" :current-marker="currentMarker" :marker-labels="markerLabels" @interacting="$emit('map-interacting',$event)" @leg="activeLeg=$event" />
    <scroll-view v-if="showMap&&legs.length>1" scroll-x class="route-leg-picker"><button v-for="(leg,index) in legs" :key="index" :class="{on:activeLeg===index}" @tap="activeLeg=index">{{ t(leg.from_name) }} → {{ t(leg.to_name) }}</button></scroll-view>
    <text v-if="!displayed.complete" class="route-warning">{{ t('部分路段无法确认可步行路径，请调整景点或通行条件。') }}</text>
    <view class="route-stops"><view v-for="(stop,index) in displayed.stops" :key="stop.spot_id" class="route-step" :class="{current:stop.spot_id===currentId}"><view class="route-stop-line"><text class="route-number">{{ stop.order||index+1 }}</text><text>{{ t(stop.spot_name) }}</text><text class="route-stay">{{ stop.visit_minutes ? t('停留')+' '+stop.visit_minutes+' '+t('分钟') : t('当前站，离开后计时') }}</text></view><text v-if="displayed.legs?.[index]" class="route-leg">{{ distance(displayed.legs[index].meters) }} · {{ t('步行') }} {{ displayed.legs[index].minutes??'—' }} {{ t('分钟') }}</text></view></view>
    <view v-if="displayed.exit_leg" class="route-leg">{{ t(displayed.exit_leg.to_name) }} · {{ distance(displayed.exit_leg.meters) }} · {{ displayed.exit_leg.minutes??'—' }} {{ t('分钟') }}</view>
    <text class="route-basis">{{ t('停留') }} {{ displayed.visit_minutes }} + {{ t('步行') }} {{ displayed.walking_minutes??'—' }} + {{ t('休息') }} {{ displayed.rest_minutes }}<template v-if="displayed.exit_leg"> + {{ t('离园') }} {{ displayed.exit_minutes??'—' }}</template><template v-if="displayed.reserve_minutes"> + {{ t('预留') }} {{ displayed.reserve_minutes }}</template> {{ t('分钟') }}</text>

  </view>
</template>
<script>
import { roadMap } from '../common/route-planning.js'
import RouteRoadMap from './RouteRoadMap.vue'
export default {
  components:{RouteRoadMap},props:{overview:Object,compare:Object,currentId:Number,showMap:{type:Boolean,default:true}},data(){return{original:false,activeLeg:0}},
  computed:{
    displayed(){return this.original&&this.compare?this.compare:this.overview},mapData(){return roadMap(this.displayed)},
    legs(){const o=this.displayed;return o?[o.entry_leg,...(o.legs||[]),o.exit_leg].filter(Boolean):[]},selectedLeg(){return this.legs[this.activeLeg]},
    currentMarker(){const index=this.displayed?.stops?.findIndex(s=>s.spot_id===this.currentId);return index>=0?index+1:0},
    markerLabels(){const labels={};(this.displayed?.stops||[]).forEach((s,i)=>{labels[i+1]=this.t(s.spot_name)+' · '+this.t('步行接入点')});if(this.displayed?.entry_anchor)labels[1001]=this.t(this.displayed.entry_anchor.label);if(this.displayed?.exit_anchor)labels[1002]=this.t(this.displayed.exit_anchor.label);return labels},
  },
  watch:{overview(){this.original=false;this.resetLeg()},displayed(){this.resetLeg()},currentId(){this.resetLeg()}},
  mounted(){this.resetLeg()},methods:{distance(n){return n==null?'—':n>=1000?(n/1000).toFixed(2)+'km':n+'m'},resetLeg(){const index=this.legs.findIndex(leg=>leg.from_id===this.currentId);this.activeLeg=index>=0?index:0}},
}
</script>
<style scoped>
.route-overview{color:var(--ng-text);font-size:28rpx;line-height:1.7;min-width:0}.route-metrics{display:flex;gap:16rpx;flex-wrap:wrap;background:#f3f5fa;border:1rpx solid var(--ng-border);padding:24rpx;border-radius:20rpx}.route-metrics>view{flex:1;min-width:140rpx}.route-metrics text,.route-metrics .metric-value{display:block}.route-metrics text{font-size:24rpx;color:var(--ng-secondary)}.route-metrics .metric-value{font-size:31rpx;font-weight:600}.route-road-map{width:100%;height:360rpx;margin-top:20rpx;border-radius:18rpx;overflow:hidden}.route-stops{margin-top:24rpx}.route-step{padding:12rpx 0;border-bottom:1rpx solid var(--ng-border)}.route-stop-line{display:flex;align-items:center;gap:14rpx;flex-wrap:wrap}.route-number{display:flex;justify-content:center;align-items:center;width:44rpx;height:44rpx;border-radius:50%;background:#e8f2ff;color:#36558f;flex-shrink:0}.current .route-number{background:#e0f1eb;color:#24755f}.route-stay{font-size:23rpx;color:var(--ng-secondary);margin-left:auto}.route-leg{display:block;margin:12rpx 0;color:var(--ng-secondary);font-size:25rpx}.route-basis,.route-source{display:block;margin-top:18rpx;font-size:24rpx;color:var(--ng-secondary);white-space:pre-line}.route-source{font-size:21rpx}.route-warning{display:block;margin:16rpx 0;color:#a43c50;background:#fff0f2;padding:18rpx;border-radius:14rpx}.route-comparison{display:flex;gap:12rpx;margin-bottom:18rpx}.route-comparison button{flex:1;font-size:26rpx;border:1rpx solid var(--ng-border);border-radius:14rpx;background:#f8f9fc;color:var(--ng-secondary)}.route-comparison .on{color:#36558f;background:#e8f2ff;border-color:#b9d4f2}
.selected-route-leg{display:grid;gap:6rpx;padding:18rpx 0;font-size:26rpx;color:var(--ng-text)}.selected-route-leg>text:last-child{font-size:24rpx;color:var(--ng-secondary)}.route-leg-picker{white-space:nowrap;margin-bottom:16rpx}.route-leg-picker button{display:inline-block;font-size:24rpx;line-height:2.2;padding:4rpx 16rpx;margin:0 10rpx 0 0;border-radius:12rpx;background:#eef5ff;color:#4f6f9e}.route-leg-picker .on{background:#d9ebff;color:#36558f}
.expand-map-button{margin:12px 0 0 auto;padding:3px 12px;width:max-content;font-size:13px;line-height:2;border-radius:12px;background:#e8f2ff;color:#36558f}
.route-metrics{flex-wrap:nowrap;align-items:center;justify-content:space-between;gap:10px;padding:16px 12px}.route-metrics>view{display:flex;align-items:center;justify-content:center;gap:4px;flex:0 1 auto;min-width:0;flex-wrap:wrap}.route-metrics text,.route-metrics .metric-value{display:inline;font-size:13px;line-height:1.6}.route-metrics .metric-value{font-size:14px;white-space:nowrap;color:var(--ng-text)}
.route-leg-picker{margin-top:16px}
</style>
