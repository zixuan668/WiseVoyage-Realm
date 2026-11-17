<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import catalog from '../../../data/tour_visual_catalog.json'
import enhancedCovers from '@/data/scenicCoverImages.json'
import { backendAssetUrl } from '@/utils/backendAssetUrl'
type CoverPhoto = { url: string; position?: string }
type EnhancedCover = CoverPhoto & { original_url?: string; source: string }
const props=defineProps<{spot:{spot_name:string;image_path?:string;city?:string};framing?:'cover'|'natural';position?:string}>()
const failed=ref(0),ready=ref(false)
const candidates=computed(()=>{
 const isSummerPalace=!props.spot.city||['北京','北京市','Beijing'].includes(props.spot.city)
 const official: CoverPhoto[]=isSummerPalace
   ? ((catalog as Record<string,{images:Array<{url:string}>}>)[props.spot.spot_name]?.images||[]).map(p=>({url:backendAssetUrl(p.url)})) : []
 // The first bridge photograph is a lion detail; use the bridge panorama as its cover.
 if(props.spot.spot_name==='十七孔桥'&&official.length>1) official.unshift(...official.splice(1,1))
 // Enhanced covers are display assets; factual citations keep the original sources.
 const enhanced=isSummerPalace?(enhancedCovers as Record<string,EnhancedCover>)[props.spot.spot_name]:undefined
 // Stored absolute file URLs may point at a stale LAN host; render them through the page origin.
 const spotPhoto=backendAssetUrl(props.spot.image_path)
 const original=enhanced?.original_url?[{url:backendAssetUrl(enhanced.original_url),position:enhanced.position}]:[]
 const photos: CoverPhoto[]=[...(spotPhoto?[{url:spotPhoto}]:[]),...(enhanced?[{url:enhanced.url,position:enhanced.position}]:[]),...original,...official]
 return photos.filter((p,index)=>photos.findIndex(other=>other.url===p.url)===index)
})
const photo=computed(()=>candidates.value[failed.value])
watch(()=>candidates.value.map(p=>p.url).join('|'),()=>{failed.value=0;ready.value=false})
function tryNext(){ready.value=false;failed.value++}
</script>
<template>
 <span class="scenic-cover" :class="{ready,'scenic-cover--natural':framing==='natural'}">
  <img v-if="photo" :key="photo.url" :src="photo.url" :style="{objectPosition:position||photo.position||'center'}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" @load="ready=true" @error="tryNext" />
 </span>
</template>
<style scoped>
.scenic-cover{position:relative;display:block;width:100%;aspect-ratio:16/10;overflow:hidden;background:#edf1f5}
.scenic-cover img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .35s,transform .65s cubic-bezier(.2,.65,.3,1)}
.scenic-cover.ready img{opacity:1}.scenic-cover.ready:hover img{transform:scale(1.015)}
.scenic-cover--natural.ready{aspect-ratio:auto;background:#fff}
.scenic-cover--natural img{position:relative;display:block;height:auto;object-fit:contain}
.scenic-cover--natural.ready:hover img{transform:none}
@media(prefers-reduced-motion:reduce){.scenic-cover img{transition:none}.scenic-cover.ready:hover img{transform:none}}
</style>
