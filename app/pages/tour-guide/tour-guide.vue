<template>
  <view class="page aurora-page">
    <!-- #ifdef APP-PLUS -->
    <view class="app-status-bar-shield" aria-hidden="true"></view>
    <!-- #endif -->
    <view class="aurora-background" aria-hidden="true"><view class="aurora-wave aurora-wave-one"></view><view class="aurora-wave aurora-wave-two"></view><view class="aurora-shine"></view></view>

    <view class="ink-bg"><view class="ink-mountain ink-mt-1"></view><view class="ink-mountain ink-mt-2"></view></view>

    <!-- 毛体标题 -->
    <scroll-view scroll-y class="page-scroll" :scroll-top="planningScrollTop" @scroll="onPlanningScroll" :style="viewportH?{height:viewportH+'px'}:null" :show-scrollbar="false">
    <view class="nav header-spacer" aria-hidden="true" :style="{height:statusH+'px'}"></view>
    <view class="planning-header">
      <button v-if="tab==='personal'" class="planning-back" :disabled="starting||recommending" :aria-label="t('返回选路线')" @tap="switchPlanningTab('route')"><text class="iconfont icon-zuoyoujiantou"></text></button>
      <text class="planning-title">{{ t(tab==='route' ? '游览路线' : '个性化行程') }}</text>
      <text class="planning-subtitle">{{ t(tab==='route' ? '选择想去的景点，查看行程后选择数字人' : '确认行程，选择数字人后开始导览') }}</text>
    </view>

    <view class="main" :class="{'itinerary-active':showItinerary}">
      <view v-if="loading" class="sk-wrap">
        <view class="sk-block" v-for="n in 3" :key="n">
          <view class="sk-line sk-w40"></view>
          <view class="sk-line sk-w100"></view>
          <view class="sk-line sk-w70"></view>
        </view>
      </view>
      <view v-if="error" class="err"><text>{{ t(error) }}</text><view class="retry" @tap="loadData">{{ t("重试") }}</view></view>

      <!-- ===== 游览路线 ===== -->
      <view v-if="tab==='route'">
        <view class="block" v-if="pageReady && routes.length">
          <view class="bl-hd"><view class="bl-dot"></view><text>{{ t("推荐路线") }}</text></view>
          <view class="route-carousel-wrap">
            <swiper @touchstart.stop="" @touchmove.stop="" @touchend.stop="" @touchcancel.stop="" class="route-carousel" :current="routeIndex" @change="routeIndex=$event.detail.current" :autoplay="pageVisible && routes.length > 1 && !routeDetail && !showMapPreview && !showItinerary && !detailSpot && !guidePicker && !previewingGuide" :interval="4500" :indicator-dots="routes.length > 1" :circular="routes.length > 1" indicator-color="#64748b" indicator-active-color="#ffffff" :duration="350">
              <swiper-item v-for="r in routes" :key="r.route_id" class="route-slide">
                <view class="route-card" :class="{on:pickedRouteId===r.route_id}" @tap="openRoute(r)">
                  <image v-if="r.cover_image&&!failedImages[r.cover_image]" @error="failedImages[r.cover_image]=true" :src="fixImg(r.cover_image)" class="route-cover-photo" mode="aspectFill" />
                  <view v-else class="route-cover-empty">{{ t("暂无路线图片") }}</view>
                  <view class="rc-top"><text class="rc-time">{{ r.estimated_time_minutes ? r.estimated_time_minutes+t('分钟') : t('时长待配置') }}</text></view>
                  <view class="rc-bottom">
                    <text class="rc-name">{{ t(r.name) }}</text>
                    <text class="rc-meta">{{ (r.spot_ids||[]).length }}{{ t("个景点") }}</text>
                  </view>
                </view>
              </swiper-item>
            </swiper>
            <view v-if="routes.length > 1" class="route-arrow route-arrow-left" @tap.stop="switchRoute(-1)"><text class="iconfont icon-zuoyoujiantou"></text></view>
            <view v-if="routes.length > 1" class="route-arrow route-arrow-right" @tap.stop="switchRoute(1)"><text class="iconfont icon-left"></text></view>
          </view>
        </view>

        <view class="block">
          <view class="bl-hd"><view class="bl-dot"></view><text>{{ t("景点选择") }}</text><text class="sub">{{ pickedCount }}/{{ spots.length }}</text></view>
          <view class="search-row"><input class="search-input" v-model="keyword" :placeholder="t('搜索景点')"/></view>
          <view class="spot-category-filters" role="group" :aria-label="t('景点分类')">
            <button v-for="cat in spotCats" :key="cat.value" class="spot-category-filter" :class="{active:spotCat===cat.value}" :aria-pressed="spotCat===cat.value" @tap="spotCat=cat.value"><text>{{ cat.value==='all'?t('全部'):catLabel(cat.value) }}</text><text class="category-count">{{ cat.count }}</text></button>
          </view>
          <view class="spot-list" v-if="filteredSpots.length">
            <view v-for="s in filteredSpots" :key="s.spot_id" class="spot-card" :class="{on:isPicked(s.spot_id)}">
              <image v-if="s.image_path&&!failedImages[s.image_path]" @error="failedImages[s.image_path]=true" :src="fixImg(s.image_path)" class="sc-img" mode="aspectFill"></image>
              <view v-else class="sc-img-df"><text class="photo-unavailable">{{ t("暂无图片") }}</text></view>
              <view class="sc-body" role="button" :aria-pressed="isPicked(s.spot_id)" :aria-label="t(s.spot_name)" @tap="toggleSpot(s.spot_id)">
                <view class="sc-info"><text class="sc-name">{{ t(s.spot_name) }}</text><text class="sc-cat">{{ catLabel(s.category) }}</text></view>
              </view>
              <view class="sc-btn" role="button" :aria-label="t('查看{place}详情',{place:t(s.spot_name)})" @tap="openDetail(s)">{{ t("详情") }}</view>
            </view>
          </view>
          <view class="empty" v-else-if="!loading"><image class="empty-art" src="/static/empty-state.png" mode="widthFix"></image><text class="empty-title">{{ t(spots.length?'未找到相关景点':'暂无景点') }}</text><text class="empty-hint">{{ t('试试其他分类或关键词') }}</text></view>
        </view>
      </view>

      <!-- ===== 个性化 ===== -->
      <view v-show="tab==='personal'">
        <view class="block">
          <view id="itinerary-planning" class="bl-hd"><view class="bl-dot"></view><text>{{ t('行程规划') }}</text></view>
          <RouteTiming ref="itinerary" v-if="pageReady&&pickedCount" :ids="selectedIds" :spots="spots" :plan="personalPlan" :pace="personalPlan?.pace||'standard'" :details="showItinerary" :disabled="recommending||starting" @open="showItinerary=true" @close="showItinerary=false" @dragging="itineraryDragging=$event" @reorder="reorderSelectedSpots" @remove="toggleSpot" @state="itineraryState=$event" />
          <text v-if="!pickedCount" class="planner-note planner-footnote">{{ t('先在游览路线中选择景点，再到这里拖动排序。') }}</text>
        </view>

        <view class="block">
          <view id="guide-selection" class="bl-hd"><view class="bl-dot"></view><text>{{ t("数字人形象") }}</text></view>
          <view class="guide-grid" v-if="guides.length">
            <view v-for="g in guides" :key="g.guide_id" class="guide-card" :class="{on:pickedGuide&&pickedGuide.guide_id===g.guide_id}" @tap="pickedGuide=g">
              <image v-if="guideImage(g)" :src="guideImage(g)" class="gc-image" mode="aspectFit" @error="imageFailed(g)" />
              <view v-else class="gc-empty">{{ g.previewLoading ? t('正在加载形象…') : t('形象未配置') }}</view>
              <view v-if="guideImage(g)||g.base_mp4_path" class="gc-preview" @tap.stop="previewGuide(g)">{{ t("预览") }}</view>
              <view class="gc-name">{{ guideName(g) }}{{ pickedGuide&&pickedGuide.guide_id===g.guide_id ? t(' · 已选择') : '' }}</view>
            </view>
          </view>
          <view class="empty" v-else-if="!loading"><image class="empty-art" src="/static/empty-state.png" mode="widthFix"></image><text class="empty-title">{{ t("暂无导游") }}</text><text class="empty-hint">{{ t("管理员上架数字导游后会显示在这里") }}</text></view>

        </view>
      </view>


      <view style="height:120rpx"></view>
    </view>
    <view class="page-bottom-space"></view>
    </scroll-view>

    <view v-if="previewingGuide" class="drawer-overlay" @tap="previewingGuide=null">
      <view class="drawer-mask"></view>
      <view class="drawer-panel guide-preview-panel" @tap.stop="">
        <view class="dp-hd"><text class="dp-title">{{ guideName(previewingGuide) }}</text></view>
        <view v-if="previewPhoto(previewingGuide)" class="guide-preview-half"><image :key="previewingGuide.guide_id" :src="previewPhoto(previewingGuide)" class="guide-preview-photo" mode="widthFix" @load="previewModelReady" @error="previewImageError" /></view>
        <text v-if="previewModelStatus" class="guide-description">{{ t(previewModelStatus) }}</text>
        <text class="guide-description">{{ guideCharacter(previewingGuide) || t('暂无角色介绍') }}</text>
        <text class="guide-description">{{ previewingGuide.previewMessage }}</text>
      </view>
    </view>
    <view v-if="guidePicker" class="drawer-overlay" @tap="guidePicker=false"><view class="drawer-mask"></view><view class="drawer-panel" @tap.stop=""><view class="dp-hd"><text class="dp-title">{{ t("选择数字人") }}</text><text @tap="guidePicker=false">{{ t("关闭") }}</text></view><view class="guide-grid"><view v-for="g in guides" :key="g.guide_id" class="guide-card" @tap="pickedGuide=g;guidePicker=false"><image v-if="guideImage(g)" :src="guideImage(g)" class="gc-image" mode="aspectFit" /><view class="gc-name">{{ t(g.name) }}</view></view></view></view></view>
    <!-- 主操作：先查看行程，再开始导览。 -->
    <FloatingTourButton v-if="!showItinerary && ((tab==='route'&&pickedCount>0) || (tab==='personal'&&canStart))" :variant="tab==='route'?'primary':'light'" :label="t(tab==='route'?'查看行程':'开始导览')" :icon="tab==='route'?'→':'▶'" @activate="tab==='route'?goSelectGuide():startTour()" @dragging="tourButtonDragging=$event" />

    <!-- 景点详情 -->
    <ScenicSheet v-if="detailSpot" ref="spotSheet" @closed="detailSpot=null">
      <view class="sheet-content spot-detail-panel" :class="{'has-photo': !!detailSpot.image_path&&!failedImages[detailSpot.image_path], scrolled: detailScrolled}" @tap.stop="">
        <view class="dp-hd"><text class="dp-title">{{ t("景点详情") }}</text></view>
        <scroll-view scroll-y :bounces="false" :show-scrollbar="false" class="dp-body" @scroll="onSpotScroll($event)">
          <view v-if="detailSpot.image_path&&!failedImages[detailSpot.image_path]" class="spot-hero"><image :src="fixImg(detailSpot.image_path)" mode="aspectFill" @error="failedImages[detailSpot.image_path]=true" /><view class="spot-hero-wash"></view></view>
          <view v-else class="spot-hero-empty"></view>
          <view class="dp-content">
          <text class="dp-name">{{ t(detailSpot.spot_name) }}</text>
          <text class="dp-desc">{{ t(detailSpot.description)||t('暂无简介') }}</text>
          <view class="dp-stats">
            <view class="dp-stat"><text class="dp-stat-label">{{ t('建议游览') }}</text><text class="dp-stat-value">{{ detailSpot.visit_duration||10 }}{{ t('分钟') }}</text></view>
            <view class="dp-stat"><text class="dp-stat-label">{{ t('自动播报') }}</text><text class="dp-stat-value">{{ Math.round(detailSpot.trigger_radius||50) }}{{ t('米内') }}</text></view>
          </view>
          <view class="dp-row"><text>{{ t("景点位置") }}</text><text>{{ t(detailSpot.city) ? t(detailSpot.city)+' · ' : '' }}{{ t(detailSpot.location)||t('暂无') }}</text></view>
          <view v-if="detailSpot.history_detail" class="dp-section"><text class="dp-sec-title">{{ t('历史与文化') }}</text><text class="dp-sec-text">{{ t(detailSpot.history_detail) }}</text></view>
          <view v-if="detailSpot.best_season" class="dp-section"><text class="dp-sec-title">{{ t('最佳季节') }}</text><text class="dp-sec-text">{{ t(detailSpot.best_season) }}</text></view>
          <view v-if="detailSpot.photo_tips" class="dp-section"><text class="dp-sec-title">{{ t('推荐取景') }}</text><text class="dp-sec-text">{{ t(detailSpot.photo_tips) }}</text></view>
          <view v-if="detailSpot.tour_tips" class="dp-section"><text class="dp-sec-title">{{ t('游览提示') }}</text><text class="dp-sec-text">{{ t(detailSpot.tour_tips) }}</text></view>
          <view v-if="detailSpot.service_facilities" class="dp-section"><text class="dp-sec-title">{{ t('周边服务') }}</text><text class="dp-sec-text">{{ t(detailSpot.service_facilities) }}</text></view>
        </view>
        <view class="dp-btn" :class="{added:isPicked(detailSpot.spot_id)}" @tap="toggleSpot(detailSpot.spot_id);closeSpotSheet()">
          <text>{{ isPicked(detailSpot.spot_id)?t('✓ 取消选择'):t('加入选择') }}</text>
        </view>
        </scroll-view>
      </view>
    </ScenicSheet>

    <!-- 路线时间轴抽屉 -->
    <ScenicSheet v-if="routeDetail" ref="routeSheet" @closed="routeDetail=null">
      <view class="sheet-content route-detail-panel" @tap.stop="">
        <view v-if="routeDetail.cover_image" class="route-detail-background"><image :src="fixImg(routeDetail.cover_image)" class="route-detail-photo" mode="aspectFill" /><view class="route-detail-wash"></view></view>
        
        <view class="dp-hd"><text class="dp-title">{{ t(routeDetail.name) }}</text></view>
        <scroll-view scroll-y :bounces="false" :show-scrollbar="false" class="dp-body" @scroll="$refs.routeSheet.setScroll($event)"><view class="dp-content">
          <view class="rd-tag">{{ (routeDetail.spot_ids||[]).length }}{{ t('个景点 ·') }} {{ routeTotalTime ? routeTotalTime+t('分钟') : t('时长待配置') }}</view>
          <text class="rd-desc">{{ t(routeDetail.description)||'' }}</text>
          <!-- 竖点时间轴 -->
          <view class="timeline">
            <view v-for="(s,i) in routeSpots" :key="s.spot_id" class="tl-item">
              <view class="tl-left">
                <view class="tl-dot" :class="{start:i===0,end:i===routeSpots.length-1}">{{ i+1 }}</view>
                <view class="tl-line" v-if="i<routeSpots.length-1">
                  <view class="tl-pulse"></view>
                  <view class="tl-pulse" style="animation-delay:.75s"></view>
                </view>
              </view>
              <view class="tl-card">
                <image v-if="s.image_path&&!failedImages[s.image_path]" @error="failedImages[s.image_path]=true" :src="fixImg(s.image_path)" class="tlc-img" mode="aspectFill"></image>
                <view v-else class="tlc-img-df"><text class="photo-unavailable">{{ t("暂无图片") }}</text></view>
                <view class="tlc-info">
                  <text class="tlc-name">{{ t(s.spot_name) }}</text>
                  <text class="tlc-cat">{{ t(s.city) ? t(s.city)+' · ' : '' }}{{ s.visit_duration ? t('预计')+s.visit_duration+t('分钟') : t('时长待配置') }}</text>
                </view>
              </view>
            </view>
          </view>
        </view></scroll-view>
        <view class="dp-actions">
          <view class="dpa-btn pick" :class="{on:pickedRouteId===routeDetail.route_id}" @tap="pickRoute(routeDetail)">
            <text>{{ pickedRouteId===routeDetail.route_id ? t('✓ 已选此路线') : t('选择此路线') }}</text>
          </view>
          <view class="dpa-btn start" @tap="goSelectGuide" v-if="pickedRouteId===routeDetail.route_id"><text>{{ t("查看行程") }}</text></view>
        </view>
      </view>
    </ScenicSheet>

    <!-- TabBar -->
  </view>
</template>

<script>
import RouteTiming from '../../components/RouteTiming.vue'
import FloatingTourButton from '../../components/FloatingTourButton.vue'
import ScenicSheet from '../../components/ScenicSheet.vue'
import { selectedOrder, moveStop, previewOptions, roadMap } from '../../common/route-planning.js'
import { prioritizeSummerPalace } from '../../common/scenic-order.js'
import { BASE_URL, assetUrl, isBeijingCity } from '../../common/config.js'
import { wgs84ToGcj02 } from '../../../shared/coordinates.js'

function req(o){
  return new Promise(function(resolve,reject){
    var url=o.url,token=uni.getStorageSync('token')||''
    if(url.indexOf('http')!==0)url=BASE_URL+url
    uni.request({
      url,method:o.method||'GET',data:o.data||{},
      header:Object.assign({'Content-Type':'application/json'},token?{Authorization:'Bearer '+token}:{},o.headers||{}),
      success:function(response){
        if(response.statusCode===200){resolve({data:response.data});return}
        var body=response.data||{},error=new Error(typeof body.detail==='string'?body.detail:body.message||'服务暂不可用，请稍后重试')
        error.statusCode=response.statusCode
        if(response.statusCode===401 && (uni.getStorageSync('token')||'')===token){
          uni.removeStorageSync('token')
          uni.removeStorageSync('login_provider')
          uni.reLaunch({url:'/pages/auth/auth?expired=1'})
        }
        reject(error)
      },
      fail:reject
    })
  })
}
var api={
  getSpots:function(){return req({url:'/tour-session/spots'})},
  getGuides:function(language){return req({url:'/tour-session/guides?language='+(language==='en'?'en':'zh')})},
  getRoutes:function(){return req({url:'/tour-session/routes'})},
  createSession:function(n,g,p,s,planning){return req({url:'/tour-session/visitor-create?name='+encodeURIComponent(n||'游客')+'&guide_id='+(g||1)+'&visitor_preferences='+encodeURIComponent(p||'')+'&spot_ids='+encodeURIComponent(JSON.stringify(s||[]))+(planning?'&planning='+encodeURIComponent(JSON.stringify(planning)):''),method:'POST'})},
}
export default {
  components:{FloatingTourButton,RouteTiming,ScenicSheet},
  watch:{
    dockHiddenByOverlay:function(v){ uni.$emit('dock:sync',{source:'tour',hide:!!v}) },
  },
  onReady:function(){
    this.pageReady=true
  },
  data:function(){return{failedImages:{},planningScrollTop:0,routeScrollTop:0,detailScrolled:false,statusH:20,viewportH:0,showMapPreview:false,pageReady:false,pageVisible:false,showItinerary:false,itineraryDragging:false,tourButtonDragging:false,orderedIds:[],starting:false,itineraryState:{key:"",busy:false,error:"",data:null},
    previewWidth:0,previewPixelRatio:1,previewModelStatus:'',previewingGuide:null,tab:'route',routeIndex:0,spots:[],routes:[],guides:[],pickedIds:{},pickedRouteId:null,pickedGuide:null,loading:true,error:'',detailSpot:null,keyword:'',routeDetail:null,themeMap:{comprehensive:'综合游览',history:'历史文化',nature:'自然风光',family:'亲子游览',photography:'摄影打卡'},
    previewWidth:0,previewPixelRatio:1,previewModelStatus:'',previewingGuide:null,tab:'route',routeIndex:0,spots:[],routes:[],guides:[],pickedIds:{},pickedRouteId:null,pickedGuide:null,loading:true,dataLoaded:false,error:'',detailSpot:null,keyword:'',routeDetail:null,themeMap:{comprehensive:'综合',history:'历史',nature:'自然',family:'亲子',photography:'摄影'},
    mapCenter:{latitude:0,longitude:0},spotCat:'all',guidePicker:false,planningDrafts:{route:null,personal:null},personalPlan:null,recommending:false,budgetIndex:2,budgetOptions:[60,90,120,180,240,360],paceIndex:0,
  }},
  computed:{
    dockHiddenByOverlay:function(){return !!(this.showItinerary||this.routeDetail||this.detailSpot||this.showMapPreview||this.guidePicker||this.previewingGuide)},
    canStart:function(){return this.pickedCount>0&&!!this.pickedGuide&&!this.recommending&&!this.starting&&this.itineraryState.key===this.itineraryKey&&!this.itineraryState.busy&&!this.itineraryState.error&&!!this.itineraryState.data?.complete},
    selectedIds:function(){return selectedOrder(this.orderedIds,this.pickedIds)},
    itineraryOptions:function(){return previewOptions(this.selectedIds,this.personalPlan,this.personalPlan?.pace||'standard')},
    itineraryKey:function(){return JSON.stringify(this.itineraryOptions)},
    itineraryMap:function(){return roadMap(this.itineraryState.key===this.itineraryKey?this.itineraryState.data:null)},
    pickedCount:function(){return Object.keys(this.pickedIds).length},
    spotCats:function(){const options=[{value:'all',count:this.spots.length}];this.spots.forEach(spot=>{const value=this.categoryKey(spot.category),option=options.find(item=>item.value===value);if(option)option.count++;else options.push({value,count:1})});return options},
    filteredSpots:function(){const kw=(this.keyword||'').trim().toLowerCase();return this.spots.filter(spot=>{if(this.spotCat!=='all'&&this.categoryKey(spot.category)!==this.spotCat)return false;if(!kw)return true;return [spot.spot_name,spot.description,spot.city,spot.location,spot.tags,this.catLabel(spot.category)].some(value=>{const text=String(value||'');return (text+' '+this.t(text)).toLowerCase().includes(kw)})})},
    mapMarkers:function(){var s=this;return s.spots.filter(function(x){return x.latitude&&x.longitude}).map(function(x,i){var picked=s.isPicked(x.spot_id);var point=wgs84ToGcj02(Number(x.latitude),Number(x.longitude));return{id:x.spot_id||i,latitude:point[0],longitude:point[1],width:28,height:28,iconPath:picked?'/static/pin-blue.png':'/static/pin-red.png',title:x.spot_name,callout:{content:x.spot_name,display:'BYCLICK',fontSize:11,borderRadius:5,padding:5}}})},
    routeSpots:function(){var s=this;if(!s.routeDetail)return[];var ids=s.routeDetail.spot_ids||[];return ids.map(function(id){return s.spots.find(function(x){return x.spot_id===id})}).filter(Boolean)},
    routeTotalTime:function(){return this.routeDetail&&this.routeDetail.estimated_time_minutes||null},

  },
  mounted:function(){var info=uni.getSystemInfoSync();this.statusH=info.statusBarHeight||20;this.viewportH=info.windowHeight||800},
  methods:{
    categoryKey:function(value){return String(value||'').trim()||'other'},
    catLabel:function(value){const key=this.categoryKey(value),labels={cultural:'文化古迹',historical:'历史遗迹',natural:'自然风光',modern:'现代景观',comprehensive:'综合景点',other:'其他'};return this.t(labels[key]||key)},
    guideName: function (g) { if (!g) return ""; return (this.tourLanguage === "en" && g.name_en) ? g.name_en : g.name },
    guideCharacter: function (g) { if (!g) return ""; return (this.tourLanguage === "en" && g.character_en) ? g.character_en : g.character },

    fixImg:function(u){if(!u)return'';return assetUrl(u)},
    guideImage:function(g){return this.fixImg(g.poster_image||g.avatar||g.previewUrl)},
    previewPhoto:function(g){return this.fixImg(g.avatar||g.poster_image||g.previewUrl)},
    imageFailed:function(g){if(g.poster_image){g.poster_image='';return}if(g.avatar){g.avatar='';return}g.previewUrl='';g.previewMessage='形象加载失败'},
    previewGuide:function(g){this.previewModelStatus=this.guideImage(g)?'正在加载形象图片':'暂无预览';this.previewingGuide=g},
    previewModelReady:function(){this.previewModelStatus=''},
    previewImageError:function(){this.previewModelStatus='形象图片加载失败，请关闭预览后重试'},
    previewVideoError:function(){uni.showToast({title:'形象视频播放失败，请检查素材',icon:'none'})},
    guideVoiceMessage:function(g){var label=g&&g.voice_label?String(g.voice_label).trim():'';if(!label)return this.tourLanguage==='en'?'Xingyun digital human':'星云数字人';return (this.tourLanguage==='en'?'Xingyun · ':'星云 · ')+label},
    loadGuidePreview:function(g){if(g.render_mode==='xingyun'){g.previewLoading=false;g.previewMessage=this.guideVoiceMessage(g);return}var s=this;req({url:'/avatar/capabilities/'+g.guide_id}).then(function(r){if(!r.data.success)throw new Error(r.data.message);var c=r.data.data;g.previewUrl='';g.previewMessage=c.realistic.message}).catch(function(){g.previewMessage='数字人状态查询失败，请重试'}).finally(function(){g.previewLoading=false})},
    goTab:function(p){uni.reLaunch({url:p})},
    isPicked:function(id){return!!this.pickedIds[id]},
    toggleSpot:function(id){if(this.starting||this.recommending)return;var order=this.selectedIds.slice();if(!this.pickedIds[id]&&order.length>=20){uni.showToast({title:this.t('路线最多支持20站，请先精简行程'),icon:'none'});return}var selected=this.spots.filter(x=>this.pickedIds[x.spot_id]);var next=this.spots.find(x=>x.spot_id===id);if(!this.pickedIds[id]){if(!next||!next.city){uni.showToast({title:'景点所属城市待配置',icon:'none'});return}if(selected.some(x=>x.city!==next.city)){uni.showToast({title:'一次导览只能选择同一城市',icon:'none'});return}}this.pickedRouteId=null;if(this.tab==='personal')this.personalPlan=null;var n={};Object.keys(this.pickedIds).forEach(function(k){n[k]=true});if(n[id])delete n[id];else n[id]=true;this.pickedIds=n;this.orderedIds=order.includes(id)?order.filter(x=>x!==id):order.concat(id);var s=this;var spot=s.spots.find(function(x){return x.spot_id===id});if(spot)s.saveHistory(spot)},
    pickRoute:function(r){
      if(this.starting||this.recommending)return
      this.personalPlan=null
      if(this.pickedRouteId===r.route_id){
        this.pickedRouteId=null
        this.pickedIds={}
        this.orderedIds=[]
        this.showItinerary=false
        return
      }
      this.pickedRouteId=r.route_id
      var ids={};(r.spot_ids||[]).forEach(function(id){ids[id]=true})
      this.pickedIds=ids
      this.orderedIds=(r.spot_ids||[]).slice()
    },
    reorderSelectedSpots:function(ids){
      if(this.starting||this.recommending)return
      const selected=this.selectedIds
      if(ids.length!==selected.length||new Set(ids).size!==selected.length||ids.some(id=>!selected.includes(id)))return
      this.orderedIds=ids.slice();this.pickedRouteId=null;this.personalPlan=null
    },
    moveSelectedSpot:function(id,direction){if(this.starting||this.recommending)return;this.orderedIds=moveStop(this.selectedIds,id,direction);this.pickedRouteId=null;this.personalPlan=null},
    onPlanningScroll:function(event){this._planningScrollTop=event.detail.scrollTop;if(this.tab==='route')this.routeScrollTop=event.detail.scrollTop},
    switchPlanningTab:function(next){
      if(this.starting||this.recommending||next===this.tab)return
      this.planningScrollTop=this._planningScrollTop||0
      this.tab=next;this.showItinerary=false
      this.$nextTick(()=>{this.planningScrollTop=next==='route'?this.routeScrollTop:0})
    },
    preferenceCount:function(v){return this.spots.filter(function(s){var p=s.preference_profile;return v==='comprehensive'||p&&p.affinities[v]>=3&&(v!=='family'||!p.stairs)}).length},
    changeBudget:function(e){if(this.recommending)return;this.budgetIndex=Number(e.detail.value)},
    changePace:function(e){if(this.recommending)return;this.paceIndex=Number(e.detail.value)},
    async generatePersonalPlan(){
      if(this.recommending||this.starting)return
      this.recommending=true
      try{
        const response=await req({url:'/tour-routes/recommend',method:'POST',data:{preferences:['comprehensive'],time_budget_minutes:this.budgetOptions[this.budgetIndex],pace:this.paceIndex?'relaxed':'standard',start_area:'auto'}})
        const result=response.data
        if(result.code!==0||!result.data?.spot_ids?.length){uni.showToast({title:result.message||this.t('暂无匹配路线'),icon:'none'});return}
        this.personalPlan=result.data
        const ids={};result.data.spot_ids.forEach(id=>{ids[id]=true})
        this.pickedIds=ids;this.orderedIds=result.data.spot_ids.slice();this.pickedRouteId=null
        this.recommending=false
        await this.$nextTick()
        uni.pageScrollTo({selector:'#itinerary-planning',duration:300})
      }catch(_){uni.showToast({title:this.t('规划失败，请检查服务'),icon:'none'})}
      finally{this.recommending=false}
    },
    openDetail:function(s){this.detailScrolled=false;this.detailSpot=s;this.saveHistory(s)},
    onSpotScroll:function(e){this.detailScrolled=(e.detail.scrollTop||0)>24;if(this.$refs.spotSheet)this.$refs.spotSheet.setScroll(e)},
    saveHistory:function(s){req({url:'/spot-favorites/history/'+s.spot_id,method:'PUT'}).then(function(r){if(!r.data.success)throw new Error('Save failed')}).catch(function(){uni.showToast({title:'浏览记录保存失败，请检查网络',icon:'none'})})},
    themeIcon:function(t){var m={comprehensive:'icon-youlan',history:'icon-lishiwenhua',nature:'icon-ziranfengguang',family:'icon-qinzi',photography:'icon-cam-3'};return m[t]||'icon-youlan'},
    switchRoute:function(direction){if(this.routes.length>1)this.routeIndex=(this.routeIndex+direction+this.routes.length)%this.routes.length},
    openRoute:function(r){this.routeDetail=r},
    goSelectGuide:function(){
      if(!this.pickedCount||this.starting||this.recommending)return
      this.routeDetail=null;this.switchPlanningTab('personal')
    },
    startTour:function(){var s=this;if(!s.pickedCount){uni.showToast({title:'请选择景点',icon:'none'});return}
      if(s.recommending||s.starting)return
      if(s.itineraryState.key!==s.itineraryKey||s.itineraryState.busy||s.itineraryState.error||!s.itineraryState.data?.complete){uni.showToast({title:s.t('请等待可用的路线与用时结果'),icon:'none'});return}
      var ids=s.selectedIds.slice(),gid=s.pickedGuide?s.pickedGuide.guide_id:0
      if(!gid){uni.showToast({title:'请选择数字人形象',icon:'none'});return}
      (s.starting=true,api.createSession('游客导览',gid,'',ids,s.personalPlan?{preferences:['comprehensive'],time_budget_minutes:s.budgetOptions[s.budgetIndex],pace:s.paceIndex?'relaxed':'standard',start_area:s.itineraryOptions.start_area,end_area:s.itineraryOptions.end_area,avoid_steps:s.itineraryOptions.avoid_steps}:null)).then(function(r){
        var sid=null;if(r&&r.data&&r.data.data&&r.data.data.session_id)sid=r.data.data.session_id;else if(r&&r.data&&r.data.session_id)sid=r.data.session_id
        if(sid&&r.data.data&&r.data.data.avatar_access_token)uni.setStorageSync('xingyun-tour-'+sid,r.data.data.avatar_access_token);if(sid)return req({url:'/tour-session/start/'+sid,method:'PUT',headers:{'X-Tour-Access':uni.getStorageSync('xingyun-tour-'+sid)}}).then(function(start){if(!start.data.success){uni.showToast({title:start.data.message||'开始导览失败',icon:'none'});return}uni.navigateTo({url:'/pages/tour/tour?sessionId='+sid})});else uni.showToast({title:r&&r.data&&r.data.message||'创建失败',icon:'none'})
      }).catch(function(error){if(error.statusCode!==401)uni.showToast({title:s.t(error.message||'网络连接失败，请稍后重试'),icon:'none'})}).finally(function(){s.starting=false})},
    restoreAISelection:function(){
      const rawIds=uni.getStorageSync('ai_spot_ids'),rawPlan=uni.getStorageSync('ai_route_plan'),owner=uni.getStorageSync('ai_route_owner')
      if(!rawIds&&!rawPlan)return
      uni.removeStorageSync('ai_spot_ids');uni.removeStorageSync('ai_route_plan');uni.removeStorageSync('ai_route_owner')
      const id=uni.getStorageSync('user_id'),current=id?'id:'+id:uni.getStorageSync('username')?'name:'+uni.getStorageSync('username'):'guest'
      if(owner!==current)return
      try{
        const plan=rawPlan?(typeof rawPlan==='string'?JSON.parse(rawPlan):rawPlan):null
        const ids=plan?.spot_ids||(typeof rawIds==='string'?JSON.parse(rawIds):rawIds)
        if(!Array.isArray(ids)||!ids.length||ids.length>20||ids.some(id=>!Number.isInteger(id)||id<=0)||new Set(ids).size!==ids.length)throw new Error()
        const selected=ids.map(id=>this.spots.find(spot=>spot.spot_id===id))
        if(selected.some(spot=>!spot?.city)||new Set(selected.map(spot=>spot.city)).size>1)throw new Error()
        if(plan){
          this.switchPlanningTab('personal');this.personalPlan=plan
          const budget=Number(plan.requested_time_minutes)
          if(Number.isInteger(budget)&&budget>=15&&budget<=480){if(!this.budgetOptions.includes(budget))this.budgetOptions=this.budgetOptions.concat(budget).sort((a,b)=>a-b);this.budgetIndex=this.budgetOptions.indexOf(budget)}
          this.paceIndex=plan.pace==='relaxed'?1:0
        }
        const picked={};ids.forEach(id=>{picked[id]=true});this.pickedIds=picked;this.orderedIds=ids.slice();this.pickedRouteId=null
      }catch(_){uni.showToast({title:this.t('部分推荐景点已不可用，请重新规划'),icon:'none'})}
    },
    loadData:function(){var s=this
      // 只有首次进入显示骨架屏；从 AI 页滑回来时静默刷新，避免整页闪一下骨架块。
      var first=!s.dataLoaded
      if(first)s.loading=true
      s.error=''
      Promise.all([api.getGuides(s.tourLanguage).catch(function(){return null}),api.getSpots().catch(function(){return null}),api.getRoutes().catch(function(){return null})]).then(function(r){
        var gr=r[0],sr=r[1],rr=r[2]
        if(gr&&gr.data){var g=gr.data
          var list=(g.data&&g.data.guide_list)?g.data.guide_list:(g.guide_list||[])
          var known={};s.guides.forEach(function(old){known[old.guide_id]=old})
          s.guides=list.map(function(item){var old=known[item.guide_id]
            return old?Object.assign({},item,{previewUrl:old.previewUrl,previewMessage:old.previewMessage,previewLoading:old.previewLoading}):Object.assign({},item,{previewUrl:'',previewMessage:'正在查询数字人服务状态',previewLoading:true})})
          var previous=s.pickedGuide&&s.pickedGuide.guide_id
          s.pickedGuide=s.guides.find(function(item){return item.guide_id===previous})||null
          // 星云数字人的声音标签随语言变化，每次加载都按当前语言重算；其他形象只为新增项拉取预览，避免图片闪烁。
          s.guides.forEach(function(item){
            if(item.render_mode==='xingyun'){item.previewLoading=false;item.previewMessage=s.guideVoiceMessage(item)}
            else if(!known[item.guide_id])s.loadGuidePreview(item)
          })
        }
        if(sr&&sr.data){var sd=sr.data;s.spots=(sd.data&&sd.data.spot_list)?sd.data.spot_list:(sd.spot_list||[])}
        if(rr&&rr.data){var rd=rr.data;s.routes=(rd.data&&rd.data.route_list)?rd.data.route_list:(rd.route_list||[])}
        s.spots=s.spots.filter(function(x){return isBeijingCity(x.city)})
        s.routes=s.routes.filter(function(x){return isBeijingCity(x.city)}).slice(0,3).map(r=>({...r,cover_image:({"皇家园林经典文化线": "/static/route-covers/royal-garden-culture.jpg", "昆明湖摄影漫游线": "/static/route-covers/kunming-lake-photography.jpg", "亲子湖山体验线": "/static/route-covers/family-lakeside.jpg"})[r.name]||r.cover_image}))
        s.routeIndex=Math.min(s.routeIndex,Math.max(0,s.routes.length-1))
        var ordered=prioritizeSummerPalace(s.spots,s.routes);s.spots=ordered.spots;s.routes=ordered.routes
        var located=s.spots.find(function(x){return x.latitude&&x.longitude});if(located){var point=wgs84ToGcj02(Number(located.latitude),Number(located.longitude));s.mapCenter={latitude:point[0],longitude:point[1]}}
        if(gr&&sr&&rr)s.dataLoaded=true
        if(!gr||!sr||!rr){if(first)s.error='部分数据加载失败，请重试'}
        // 进入导览页不自动选景点：上一次 AI 推荐留下的暂存直接丢弃。
        s.restoreAISelection()
        s.loading=false
      }).catch(function(){if(first)s.error='网络连接失败';s.loading=false})},
    onMarkerTap:function(e){var id=e.detail&&e.detail.markerId;if(id){this.toggleSpot(id);this.$forceUpdate()}},
    checkAuth:function(){var t=uni.getStorageSync('token');if(!t){uni.reLaunch({url:'/pages/auth/auth'});return false}return true},
  },
  onBackPress:function(){if(this.showItinerary){this.showItinerary=false;return true}if(this.showMapPreview){this.showMapPreview=false;return true}if(this.tab==='personal'){this.switchPlanningTab('route');return true}},
  onHide:function(){this.tourButtonDragging=false;this.itineraryDragging=false;this.showItinerary=false;this.pageVisible=false;this.showMapPreview=false},
  onUnload:function(){this.itineraryDragging=false;this.pageVisible=false;this.pageReady=false},
  onShow:function(){this.pageVisible=true;this.showMapPreview=false;if(this.checkAuth())this.loadData()},
}
</script>

<style scoped>
.planning-header{position:relative;z-index:1;padding:16rpx 120rpx 28rpx;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:12rpx}
.planning-title{text-align:center;font-size:40rpx;font-weight:700;color:var(--ng-text)}
.planning-subtitle{text-align:center;font-size:25rpx;line-height:1.5;color:var(--ng-secondary)}
.planning-back{position:absolute;left:16rpx;top:4rpx;margin:0;padding:6rpx 0;font-size:24rpx;line-height:1.8;color:var(--ng-accent-text,#5141ad);background:transparent;border:0;border-radius:0;box-shadow:none}.planning-back[disabled]{background:transparent;opacity:.5}.planning-back::after,.selection-next::after{border:0}
.main.itinerary-active{z-index:2200}
.header-spacer{padding:0!important;border-bottom:0!important;pointer-events:none}
.map-preview{margin:0 0 0 auto;padding:8rpx 24rpx;line-height:1.6;min-height:0;font-size:25rpx;color:#6840c2;background:#f1eaff;border-radius:14rpx}
.map-preview::after{border:0}.map-preview[disabled]{color:#938aa5;background:#f4f0f8}
.map-preview-overlay{display:flex;align-items:center;justify-content:center;padding:0 24rpx;box-sizing:border-box}
.map-preview-dialog{position:relative;width:100%;background:#fff;border-radius:24rpx;overflow:hidden}
.map-preview-heading{height:100rpx;display:flex;align-items:center;justify-content:space-between;padding:0 24rpx;font-size:32rpx;font-weight:600;box-sizing:border-box}
.map-preview-close{margin:0;padding:8rpx 20rpx;line-height:1.6;font-size:26rpx;color:#6840c2;background:#f1eaff;border-radius:12rpx}
.map-preview-close::after{border:0}
.large-scenic-map{display:block;width:100%;height:60vh}
.guide-preview-half{height:600rpx;margin:0 24rpx;overflow:hidden;background:var(--ng-surface)}.guide-preview-photo{display:block;width:100%}
.guide-preview-panel{overflow-y:auto}.guide-preview-panel .dp-hd{position:relative;justify-content:center;padding:20rpx 80rpx}.guide-preview-panel .dp-title{font-size:46rpx;font-weight:700;line-height:1.4;text-align:center}.guide-preview-panel .guide-description{font-size:34.5rpx;line-height:1.65;padding:16rpx 24rpx;color:var(--ng-secondary)}
.gc-image{position:absolute;width:100%;height:100%;left:0;top:0}.gc-empty{padding:70rpx 16rpx;text-align:center;font-size:27.6rpx;color:var(--ng-secondary)}.guide-description{display:block;padding:18rpx;color:var(--ng-secondary);font-size:27.6rpx;line-height:1.7}.guide-description text{display:block}.guide-preview-video{width:100%;height:600rpx}
.gc-preview{position:absolute;right:10rpx;top:10rpx;z-index:3;padding:8rpx 16rpx;border-radius:12rpx;background:rgba(30,41,59,0.28);color:var(--ng-text);font-size:25.3rpx}
.page{min-height:100vh;box-sizing:border-box;background-color:var(--ng-surface);position:relative}
.ink-bg{position:absolute;inset:0;pointer-events:none;z-index:0}.ink-mountain{position:absolute;left:0;right:0;background:var(--ng-night);border-radius:50% 70% 0 0}.ink-mt-1{bottom:20%;height:200rpx;opacity:.03;transform:scaleX(1.4)}.ink-mt-2{bottom:25%;height:150rpx;opacity:.02;transform:scaleX(1.2) translateX(10%)}
.page-bg{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0}

.nav{position:relative;z-index:1;display:flex;align-items:center;justify-content:center;padding:16rpx 24rpx;background:var(--ng-surface)}.nav-title{font-size:39.1rpx;font-weight:600;color:var(--ng-text);letter-spacing:0;font-family:var(--app-font-family);text-align:center}

.main{position:relative;z-index:1;padding:0 20rpx;min-height:0;box-sizing:border-box;width:100%}.load{text-align:center;padding:80rpx;color:var(--ng-secondary)}.err{text-align:center;padding:32rpx;background:var(--ng-surface);border-radius:14rpx;border:1rpx solid rgba(99,102,241,0.25)}.err text{display:block;color:var(--ng-secondary);font-size:27.6rpx;margin-bottom:12rpx}.retry{display:inline-block;padding:10rpx 28rpx;background:rgba(99,102,241,0.18);color:var(--ng-text);border-radius:10rpx;font-size:27.6rpx}

/* ═══════ 输入栏：弹性定位紧贴tab上沿 ═══════ */




.block{margin:14rpx 0;background:var(--ng-surface);border-radius:16rpx;padding:18rpx;border:1rpx solid var(--ng-border)}
.bl-hd{display:flex;align-items:center;gap:8rpx;margin-bottom:14rpx}.bl-dot{width:7rpx;height:20rpx;border-radius:3rpx;background:rgba(99,102,241,0.18)}.bl-hd text{font-size:32.2rpx;font-weight:600;color:var(--ng-text)}.sub{font-weight:400;color:var(--ng-secondary);font-size:25.3rpx;margin-left:8rpx}
.map-wrap{position:relative;width:100%;height:180rpx;border-radius:14rpx;overflow:hidden}.mini-map{display:block;position:relative;width:100%;height:180rpx}.map-empty{height:180rpx;display:flex;align-items:center;justify-content:center;background:var(--ng-surface);color:var(--ng-secondary)}
.route-carousel-wrap{position:relative;border-radius:20rpx;overflow:hidden}.route-carousel{height:440rpx;width:100%}.route-slide{height:100%}.route-card{position:relative;width:100%;height:100%;overflow:hidden;background:var(--ng-night);box-sizing:border-box}.route-card.on{box-shadow:inset 0 0 0 4rpx rgba(99,102,241,0.15)}.route-carousel .route-cover-photo{position:absolute;inset:0;width:100%;height:100%;border-radius:0;margin:0}.route-cover-empty{height:100%;display:flex;align-items:center;justify-content:center;color:var(--ng-text)}.rc-top{position:absolute;top:22rpx;left:24rpx;right:24rpx;display:flex;justify-content:space-between;align-items:center}.rc-tag{font-size:25.3rpx;color:var(--ng-text);background:rgba(0,0,0,.3);padding:6rpx 14rpx;border-radius:24rpx}.rc-time{font-size:25.3rpx;color:var(--ng-text);text-shadow:0 2rpx 6rpx rgba(0,0,0,.9),0 0 3rpx rgba(0,0,0,.85)}.rc-bottom{position:absolute;left:26rpx;right:26rpx;bottom:48rpx}.route-carousel .route-cover-note{display:block;font-size:20.7rpx;color:var(--ng-text);margin-bottom:6rpx}.rc-name{font-size:34.5rpx;line-height:1.4;font-weight:600;color:var(--ng-text);display:block;text-shadow:0 2rpx 10rpx rgba(0,0,0,.92),0 0 4rpx rgba(0,0,0,.9)}.rc-meta{display:block;font-size:25.3rpx;color:var(--ng-text);margin-top:8rpx;text-shadow:0 2rpx 8rpx rgba(0,0,0,.9),0 0 3rpx rgba(0,0,0,.85)}.route-arrow{position:absolute;top:50%;transform:translateY(-50%);width:64rpx;height:84rpx;display:flex;align-items:center;justify-content:center;font-size:42rpx;color:var(--ng-text);background:rgba(0,0,0,.32);border-radius:12rpx;z-index:2}.route-arrow .iconfont{font-size:36rpx;color:var(--ng-text)}.route-arrow-left{left:12rpx}.route-arrow-right{right:12rpx}
.search-row{margin-bottom:14rpx;width:100%;box-sizing:border-box}.search-input{width:100%;height:68rpx;padding:0 20rpx;border:1rpx solid var(--ng-border);border-radius:34rpx;background:var(--ng-surface);font-size:27.6rpx;color:var(--ng-text);box-sizing:border-box}
.cat-tabs{white-space:nowrap;margin-bottom:14rpx}.cat-tab{display:inline-block;font-size:25.3rpx;color:var(--ng-secondary);padding:8rpx 20rpx;margin-right:10rpx;border-radius:20rpx;background:rgba(99,102,241,0.08)}.cat-tab.on{background:rgba(99,102,241,0.18);color:var(--ng-text);font-weight:700}
.spot-category-filters{display:flex;flex-wrap:wrap;gap:10rpx;padding:0 0 18rpx;margin-bottom:16rpx;border-bottom:1rpx solid var(--ng-border)}
.spot-category-filter{display:flex;align-items:center;justify-content:center;gap:12rpx;min-height:64rpx;margin:0;padding:10rpx 18rpx;line-height:1.4;font-size:25rpx;font-weight:400;color:var(--ng-secondary);background:transparent;border-radius:14rpx;box-sizing:border-box;transition:background-color .24s ease,color .24s ease;will-change:transform}
.spot-category-filter::after{border:0}.spot-category-filter.active{color:var(--ng-soft-blue-text);background:var(--ng-glass-blue-bg);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.92);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);animation:categoryPop .42s cubic-bezier(.34,1.56,.64,1) both}.category-count{font-size:22rpx;opacity:.8}@keyframes categoryPop{0%{transform:scale(.9)}55%{transform:scale(1.07)}100%{transform:scale(1.04)}}@media (prefers-reduced-motion:reduce){.spot-category-filter.active{animation:none}}
.spot-list{display:flex;flex-direction:column;gap:10rpx}.spot-card{display:flex;align-items:center;gap:12rpx;padding:14rpx;border:1rpx solid var(--ng-border);border-radius:14rpx;background:var(--ng-surface)}.spot-card.on{border-color:rgba(99,102,241,0.25);background:rgba(99,102,241,0.06)}.sc-img{width:64rpx;height:64rpx;border-radius:12rpx;flex-shrink:0}.sc-img-df{width:64rpx;height:64rpx;border-radius:12rpx;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.1);font-size:32.2rpx;flex-shrink:0}.sc-body{display:flex;align-items:center;flex:1;min-width:0}.sc-info{flex:1;min-width:0}.sc-name{font-size:29.9rpx;font-weight:700;color:var(--ng-text);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sc-cat{display:inline-flex;font-size:21rpx;line-height:1.5;color:var(--ng-soft-blue-text);margin-top:6rpx;padding:1rpx 10rpx;border-radius:8rpx;background:var(--ng-glass-blue-bg);box-shadow:0 1rpx 2rpx rgba(70,105,170,.06),0 4rpx 8rpx -4rpx rgba(70,105,170,.12),inset 0 1rpx 0 rgba(255,255,255,.9)}.sc-btn{font-size:23rpx;color:var(--ng-secondary);padding:6rpx 12rpx;border:1rpx solid rgba(99,102,241,0.25);border-radius:8rpx;flex-shrink:0}
.guide-grid{display:flex;flex-wrap:wrap;gap:12rpx}.guide-card{width:calc(50% - 6rpx);min-height:200rpx;display:flex;align-items:flex-end;justify-content:flex-end;padding:10rpx;border:2rpx solid var(--ng-border);border-radius:16rpx;background-color:var(--ng-surface);background-size:contain;background-repeat:no-repeat;background-position:center;box-sizing:border-box;position:relative;overflow:hidden}.guide-card.on{border-color:rgba(99,102,241,0.25);box-shadow:0 0 0 3rpx rgba(99,102,241,0.15)}.gc-name{position:relative;z-index:2;padding:6rpx 14rpx;border-radius:8rpx;background:transparent;backdrop-filter:none;color:#000;font-size:27.6rpx;font-weight:700}
.fab-btn{position:fixed;left:24rpx;bottom:200rpx;width:100rpx;height:100rpx;border-radius:50%;background:linear-gradient(135deg,rgba(99,102,241,0.18),rgba(99,102,241,0.18));box-shadow:0 8rpx 24rpx rgba(99,102,241,0.15);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:100;opacity:0;transform:scale(.5);transition:transform .3s,opacity .3s}.fab-btn.show{opacity:1;transform:scale(1)}.fab-icon{font-size:28rpx;color:var(--ng-text)}.fab-text{font-size:23rpx;color:var(--ng-text);font-weight:600;margin-top:2rpx}
.empty{color:var(--ng-secondary);font-size:27.6rpx;text-align:center;padding:40rpx}

/* 详情抽屉 — 优化版 */
.drawer-overlay{position:fixed;inset:0;z-index:1000}.drawer-mask{position:absolute;inset:0;background:rgba(30,41,59,0.28)}.drawer-panel{position:absolute;bottom:0;left:16rpx;right:16rpx;max-height:75vh;background:var(--ng-surface);border-radius:32rpx 32rpx 0 0;overflow:hidden;box-shadow:0 -8rpx 40rpx rgba(0,0,0,.12)}.dp-handle{width:48rpx;height:5rpx;border-radius:3rpx;background:rgba(99,102,241,0.12);margin:16rpx auto 10rpx}.dp-hd{display:flex;justify-content:space-between;align-items:center;padding:6rpx 28rpx 16rpx}.dp-title{font-size:36.8rpx;font-weight:600;color:var(--ng-text)}.dp-close{width:48rpx;height:48rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.08);font-size:32.2rpx;color:var(--ng-secondary)}
.dp-body{width:100%;padding:0;max-height:50vh;box-sizing:border-box}.dp-content{padding:0 32rpx 16rpx;box-sizing:border-box;min-width:0}.dp-desc{overflow-wrap:anywhere}.dp-row text:last-child{min-width:0;overflow-wrap:anywhere}
.dp-hero{width:100%;height:220rpx;border-radius:18rpx;margin-bottom:20rpx;box-shadow:0 4rpx 16rpx rgba(0,0,0,.06)}
.dp-name{font-size:41.4rpx;font-weight:600;color:var(--ng-text);display:block;margin-bottom:12rpx}
.dp-desc{font-size:27.6rpx;color:var(--ng-text);line-height:1.8;display:block;margin-bottom:20rpx}
.dp-row{display:flex;align-items:flex-start;gap:20rpx;padding:12rpx 0;border-top:1rpx solid var(--ng-border)}.dp-row text:first-child{font-size:27.6rpx;color:var(--ng-secondary);flex:0 0 auto;min-width:150rpx;white-space:nowrap}.dp-row text:last-child{font-size:27.6rpx;color:var(--ng-text);flex:1;min-width:0;line-height:1.6;text-align:left;overflow-wrap:anywhere}
.dp-btn{padding:12rpx 28rpx 28rpx;padding-bottom:calc(28rpx + env(safe-area-inset-bottom))}.dp-btn text{display:block;padding:24rpx;text-align:center;border-radius:18rpx;background:linear-gradient(135deg,rgba(99,102,241,0.18),rgba(99,102,241,0.18));color:var(--ng-text);font-size:34.5rpx;font-weight:600;box-shadow:0 6rpx 20rpx rgba(99,102,241,0.15)}.dp-btn.added text{background:rgba(99,102,241,0.08);color:var(--ng-secondary);box-shadow:none}
.rd-tag{display:inline-block;font-size:25.3rpx;color:var(--ng-secondary);background:rgba(99,102,241,0.06);padding:8rpx 18rpx;border-radius:22rpx;margin-bottom:16rpx}
.rd-desc{font-size:29.9rpx;color:var(--ng-text);line-height:1.8;display:block;margin-bottom:24rpx}
.dp-actions{display:flex;gap:14rpx;padding:12rpx 28rpx 28rpx;padding-bottom:calc(28rpx + env(safe-area-inset-bottom))}
.dpa-btn{flex:1;padding:24rpx;text-align:center;border-radius:18rpx;font-size:32.2rpx;font-weight:600;transition:background-color .2s,border-color .2s,box-shadow .2s}
.dpa-btn.pick{background:var(--ng-glass-blue-bg);color:var(--ng-soft-blue-text);border:0;box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9)}.dpa-btn.pick.on{background:var(--ng-glass-blue-bg);color:var(--ng-soft-blue-text);border-color:transparent;box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9)}
.dpa-btn.start{background:linear-gradient(135deg,rgba(99,102,241,0.18),rgba(99,102,241,0.18));color:var(--ng-text);box-shadow:0 6rpx 20rpx rgba(99,102,241,0.15)}

/* 路线时间轴 */
.timeline{display:flex;flex-direction:column;padding:8rpx 0}
.tl-item{display:flex;gap:16rpx}
.tl-left{display:flex;flex-direction:column;align-items:center;width:56rpx;flex-shrink:0}
.tl-dot{width:56rpx;height:56rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:27.6rpx;font-weight:600;color:var(--ng-soft-blue-text);background:var(--ng-glass-blue-bg);border:0;z-index:1;flex-shrink:0;box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9)}
.tl-dot.start{background:var(--ng-glass-blue-bg);border-color:transparent;color:var(--ng-soft-blue-text);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9)}
.tl-dot.end{background:var(--ng-glass-blue-bg);border-color:transparent;color:var(--ng-soft-blue-text);box-shadow:var(--ng-glass-shadow),inset 0 1rpx 0 rgba(255,255,255,.9)}
.tl-line{width:3rpx;flex:1;min-height:60rpx;background:rgba(99,102,241,0.12);position:relative;overflow:hidden}
.tl-card{flex:1;display:flex;gap:16rpx;padding:16rpx 18rpx;margin-bottom:12rpx;background:var(--ng-surface);border:1rpx solid var(--ng-border);border-radius:16rpx;box-shadow:0 2rpx 10rpx rgba(0,0,0,.03);transition:background-color .2s,border-color .2s,box-shadow .2s}
.tl-card:active{transform:scale(.98)}
.tlc-img{width:88rpx;height:88rpx;border-radius:14rpx;flex-shrink:0;box-shadow:0 2rpx 8rpx rgba(0,0,0,.06)}
.tlc-img-df{width:88rpx;height:88rpx;border-radius:14rpx;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.1);font-size:41.4rpx;flex-shrink:0}
.tlc-info{flex:1;display:flex;flex-direction:column;justify-content:center;gap:6rpx}.tlc-name{font-size:32.2rpx;font-weight:600;color:var(--ng-text)}.tlc-cat{font-size:25.3rpx;color:var(--ng-secondary)}

/* TabBar */
.tb-root{position:fixed;bottom:0;left:0;right:0;z-index:999;background:var(--ng-surface)}
.tb-ink-line{height:1rpx;background:linear-gradient(90deg,transparent,rgba(99,102,241,0.12),transparent);margin:0 32rpx}
.tb-inner{display:flex;align-items:center;justify-content:space-around;padding:4rpx 8rpx}
.tb-item{display:flex;flex-direction:column;align-items:center;gap:4rpx;padding:2rpx 10rpx;position:relative;flex:1}
.tb-icon{font-size:38rpx}.tb-label{font-size:23rpx;font-weight:600;color:var(--ng-secondary)}
.tb-dot{position:absolute;bottom:-4rpx;width:24rpx;height:4rpx;border-radius:2rpx;background:rgba(99,102,241,0.18);opacity:.6}
.tb-item.on .tb-label{color:var(--ng-secondary);font-weight:600}.tb-item.on .tb-icon{transform:scale(1.1)}
.tb-hl-ring{width:68rpx;height:68rpx;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(99,102,241,0.18);border:2rpx solid rgba(99,102,241,0.25);margin-bottom:-2rpx}
.tb-hl-ring.on{background:linear-gradient(135deg,rgba(99,102,241,0.18),rgba(99,102,241,0.18));border-color:transparent;box-shadow:0 6rpx 18rpx rgba(99,102,241,0.15);animation:tabBounce .4s ease-out}
.tb-hl-ring .tb-icon{font-size:34rpx}.tb-safe{height:env(safe-area-inset-bottom,10rpx);min-height:2rpx}
.tl-pulse{position:absolute;top:0;left:-5rpx;width:13rpx;height:24rpx;border-radius:7rpx;background:linear-gradient(180deg,transparent,rgba(99,102,241,0.18),var(--ng-surface),rgba(99,102,241,0.18),transparent);animation:pulseDown 1.5s ease-in-out infinite;box-shadow:0 0 12rpx rgba(99,102,241,0.15)}.tl-pulse:nth-child(2){animation-delay:.75s}
@keyframes pulseDown{0%{transform:translateY(-12rpx);opacity:0}15%{opacity:1}85%{opacity:1}100%{transform:translateY(65rpx);opacity:0}}
@keyframes tabBounce{0%{transform:scale(1)}30%{transform:scale(1.15)}60%{transform:scale(.95)}100%{transform:scale(1)}}

.nav{box-sizing:border-box;position:relative;display:flex;align-items:center;justify-content:center;padding-left:0;padding-right:0;padding-bottom:0;background:var(--ng-surface);border-bottom:1rpx solid var(--ng-border)}.nav .nav-title{font-size:18.4px;line-height:44px}.nav .nav-ai{position:absolute;left:16px;bottom:8px;width:28px;height:28px;border-radius:8px;font-size:13.8px;box-shadow:none}

.selection-next{padding:24rpx;margin:20rpx 0;border-radius:16rpx;background:rgba(99,102,241,0.18);color:var(--ng-text);text-align:center;font-weight:600}

.route-cover-photo{width:100%;height:220rpx;border-radius:14rpx;margin-bottom:14rpx}
.sk-wrap{padding:8rpx 0}
.sk-block{padding:26rpx 24rpx;margin-bottom:18rpx;border-radius:24rpx;background:var(--ng-surface);border:1rpx solid var(--ng-border)}
.sk-line{height:26rpx;border-radius:13rpx;background:linear-gradient(90deg,rgba(148,163,184,.18) 25%,rgba(148,163,184,.30) 37%,rgba(148,163,184,.18) 63%);background-size:400% 100%;animation:skShimmer 1.4s ease infinite;margin-bottom:16rpx}
.sk-line:last-child{margin-bottom:0}
.sk-w40{width:40%}.sk-w70{width:70%}.sk-w100{width:100%}
@keyframes skShimmer{0%{background-position:100% 50%}100%{background-position:0 50%}}
.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:48rpx 24rpx;text-align:center}
.empty-art{width:320rpx;margin-bottom:20rpx;opacity:.95}
.empty-title{font-size:28rpx;font-weight:600;color:var(--ng-text);margin-bottom:8rpx}
.empty-hint{font-size:24rpx;color:var(--ng-secondary);line-height:1.7}.route-cover-note{font-size:20.7rpx;color:var(--ng-secondary)}.scenic-fade{position:relative;height:360rpx;overflow:hidden}.scenic-clear,.scenic-blur{position:absolute;width:100%;height:100%;top:0;left:0}.scenic-blur{filter:blur(10px);mask-image:linear-gradient(to bottom,transparent 30%,black 70%,transparent 100%)}.scenic-veil{position:absolute;inset:0;background:linear-gradient(to bottom,transparent 35%,var(--ng-surface) 60%,var(--ng-surface) 100%)}

.route-detail-background{position:absolute;top:0;left:0;right:0;height:560rpx;max-height:60%;pointer-events:none;z-index:0;overflow:hidden}
.page.aurora-page{height:100vh;overflow:hidden;padding-bottom:0!important}
.page-scroll{display:block;height:100vh;box-sizing:border-box}
.page-bottom-space{height:calc(110px + env(safe-area-inset-bottom))}
.route-detail-photo{position:absolute;inset:0;width:100%;height:100%;opacity:1}
.route-detail-wash{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(255,255,255,.08) 0%,rgba(255,255,255,.24) 20%,rgba(255,255,255,.58) 45%,rgba(255,255,255,.86) 70%,#fff 100%)}
.route-detail-panel>.dp-handle,.route-detail-panel>.dp-hd,.route-detail-panel>.dp-body,.route-detail-panel>.dp-start,.route-detail-panel>.dp-actions{position:relative;z-index:1}
.route-detail-panel .dp-title{font-size:40.25rpx;line-height:1.4}
.route-detail-panel .dp-desc,.route-detail-panel .rd-desc{font-size:31.05rpx;color:var(--ng-secondary)}
.route-detail-panel .dp-tag,.route-detail-panel .rd-tag{font-size:27.6rpx}
.route-detail-panel .tlc-name{font-size:33.35rpx}
.route-detail-panel .tlc-cat,.route-detail-panel .tlc-trans text{font-size:26.45rpx}
/* Avoid filtered layers being clipped as cards enter Android's scroll viewport. */
.route-detail-panel .tl-card{background:#fff;-webkit-backdrop-filter:none;backdrop-filter:none;min-width:0}
.route-detail-panel .tlc-info{min-width:0}
.route-detail-panel .tlc-name{overflow-wrap:anywhere}
/* 顶部标签与底部导航共用放大后的响应式字号。 */
.page.aurora-page{--tab-label-size:16.1px}
@media(min-width:390px){.page.aurora-page{--tab-label-size:17.25px}}
@media(min-width:430px){.page.aurora-page{--tab-label-size:18.4px}}

.planner-note{display:block;font-size:26rpx;line-height:1.7;color:var(--ng-secondary);margin-top:14rpx}.planner-control{margin-top:18rpx;padding:20rpx;border-radius:16rpx;background:#f7f8fc;color:var(--ng-text);font-size:29rpx}.planner-generate{margin-top:22rpx;padding:22rpx;text-align:center;background:#5447db;border-radius:18rpx;color:#fff;font-size:30rpx}.planner-result{margin-top:28rpx;font-size:30rpx;color:var(--ng-text)}.planner-stop{padding:20rpx 0;border-bottom:1rpx solid var(--ng-border)}

.scenic-page-stage{height:100vh;box-sizing:border-box;padding-bottom:90px;overflow-y:auto;background:var(--ng-night);}
.sheet-content{border-radius:inherit;position:relative;width:100%;overflow:hidden;display:flex;flex-direction:column;height:100%;max-height:100%;min-height:0;background:#fff}
.sheet-content>.dp-body{height:0;max-height:none;flex:1;min-height:0;overscroll-behavior:contain;background:#fff}
.sheet-content>.dp-hd,.sheet-content>.dp-btn,.sheet-content>.dp-actions{flex-shrink:0}
.photo-unavailable{font-size:20rpx;color:var(--ng-muted)}

.spot-detail-panel>.dp-hd{position:absolute;top:24px;left:0;right:0;z-index:6;padding:8rpx 28rpx;pointer-events:none}
.spot-detail-panel.has-photo .dp-title{color:#fff;text-shadow:0 2rpx 12rpx rgba(0,0,0,.7)}
.spot-hero{position:relative;height:16vh;min-height:100px;width:100%;overflow:hidden}
.spot-hero image{display:block;width:100%;height:100%}
.spot-hero-wash{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(15,23,42,.25),transparent 65%,#fff)}
.spot-hero-empty{height:84px;background:#f1f2fa}
.spot-detail-panel .dp-content{padding:8rpx 28rpx 12rpx;background:#fff}
.spot-detail-panel .dp-name{font-size:36rpx;margin-bottom:8rpx}
.spot-detail-panel .dp-desc{margin-bottom:12rpx;line-height:1.7}
.spot-detail-panel .dp-btn{margin:0;padding:12rpx 24rpx calc(12rpx + env(safe-area-inset-bottom));background:#fff;border-top:1rpx solid var(--ng-border)}
.spot-detail-panel .dp-btn text{padding:18rpx;font-size:30rpx}
.spot-detail-panel{height:50vh;max-height:50vh}
.spot-detail-panel>.dp-body{height:0;max-height:none;flex:1;min-height:0}
.spot-detail-panel.scrolled>.dp-hd{opacity:0;transition:opacity .2s ease}
.dp-stats{display:flex;gap:16rpx;margin:10rpx 0 14rpx}
.dp-stat{flex:1;min-width:0;padding:16rpx 18rpx;border-radius:18rpx;background:rgba(99,102,241,.06);display:flex;flex-direction:column;gap:6rpx}
.dp-stat-label{font-size:22rpx;color:var(--ng-secondary)}
.dp-stat-value{font-size:30rpx;font-weight:600;color:var(--ng-text)}
.dp-section{margin-top:18rpx;padding-top:16rpx;border-top:1rpx solid var(--ng-border)}
.dp-sec-title{display:block;font-size:28rpx;font-weight:600;color:var(--ng-text);margin-bottom:8rpx}
.dp-sec-text{display:block;font-size:25rpx;line-height:1.75;color:var(--ng-text);white-space:pre-line;overflow-wrap:anywhere}
.route-detail-panel>.dp-hd{padding-top:28px;z-index:6;pointer-events:none}
.route-detail-panel .dp-actions{background:#fff;padding-bottom:calc(12rpx + env(safe-area-inset-bottom))}

.sheet-content.route-detail-panel>.dp-body{background:transparent}
.route-detail-panel .dp-title{text-shadow:0 1px 8px rgba(255,255,255,.85)}

.planner-control{display:flex;align-items:center;justify-content:space-between;gap:12px}.planner-footnote{font-size:12px;text-align:center}.is-generating{opacity:.65}
.bl-hd .planning-stop-count{margin-left:auto;font-size:25rpx;font-weight:400;color:var(--ng-secondary);text-align:right}
</style>

