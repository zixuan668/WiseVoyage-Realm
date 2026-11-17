<script setup lang="ts">
import { t } from '@/i18n'
import { ref, watch } from 'vue'
import { request_handler } from '@/api/base'
const props=withDefaults(defineProps<{
 spot:{description?:string;history_detail?:string;service_facilities?:string;tour_tips?:string;photo_tips?:string;best_season?:string}
 park?:string
}>(),{park:''})
type Services={source_url:string;checked_at:string;categories:Array<{id:string;label:string;scope:string}>}
const services=ref<Services|null>(null), failed=ref(false)
let version=0
async function load(){
 const own=++version
 services.value=null;failed.value=false
 if(!props.park)return
 try{
  const data=(await request_handler.get<Services>('/tour-experience/park-services/'+props.park)).data
  if(own===version)services.value=data
 }catch{if(own===version)failed.value=true}
}
watch(()=>props.park,load,{immediate:true})
const paragraphs=(text?:string)=>(text||'').split(/\n+/).map(p=>p.trim()).filter(Boolean)
</script>
<template>
 <div class="knowledge-sections">
  <section v-if="spot.description"><h2>{{t('景点介绍')}}</h2><p v-for="p in paragraphs(spot.description)" :key="p">{{t(p)}}</p></section>
  <section v-if="spot.history_detail"><h2>{{t('历史与文化')}}</h2><p v-for="p in paragraphs(spot.history_detail)" :key="p">{{t(p)}}</p></section>
  <section v-if="spot.tour_tips"><h2>{{t('值得留意')}}</h2><p v-for="p in paragraphs(spot.tour_tips)" :key="p">{{t(p)}}</p></section>
  <section v-if="spot.photo_tips"><h2>{{t('拍照建议')}}</h2><p v-for="p in paragraphs(spot.photo_tips)" :key="p">{{t(p)}}</p></section>
  <section v-if="spot.best_season"><h2>{{t('季节建议')}}</h2><p>{{spot.best_season}}</p></section>
 </div>
</template>
<style scoped>
.knowledge-sections{color:inherit;font-family:inherit}
section+section{margin-top:26px}
h2{margin:0 0 12px;font-size:19px;line-height:1.5;font-weight:600;color:inherit}
h3{font-size:15px;font-weight:500;margin:18px 0 10px;color:inherit}
p{margin:0 0 12px;font-size:16px;line-height:1.9;overflow-wrap:anywhere;color:inherit;opacity:1}
.facility-list{display:grid;grid-template-columns:1fr 1fr;gap:10px 16px;list-style:none;padding:0;margin:0 0 18px;font-size:14px;line-height:1.6}
.facility-list li::before{content:'·';margin-right:8px}
a{color:inherit;text-underline-offset:4px;font-size:14px}
button{min-height:44px;border:0;border-radius:10px;background:transparent;color:inherit;font:inherit;text-decoration:underline}
</style>
