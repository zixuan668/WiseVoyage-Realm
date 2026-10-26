<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import catalog from '../../../data/tour_visual_catalog.json'
import enhancedCovers from '@/data/scenicCoverImages.json'
type CoverPhoto = { url: string; position?: string }
type EnhancedCover = CoverPhoto & { original_url: string; source: string }
const props=defineProps<{spot:{spot_name:string;image_path?:string;city?:string};framing?:'cover'|'natural';position?:string}>()
const failed=ref(0),ready=ref(false)
const candidates=computed(()=>{
 const isSummerPalace=!props.spot.city||['北京','北京市','Beijing'].includes(props.spot.city)
 const official: CoverPhoto[]=isSummerPalace
   ? ((catalog as Record<string,{images:Array<{url:string}>}>)[props.spot.spot_name]?.images||[]).map(p=>({url:p.url})) : []
 // The first bridge photograph is a lion detail; use the bridge panorama as its cover.
 if(props.spot.spot_name==='十七孔桥'&&official.length>1) official.unshift(...official.splice(1,1))
 // Enhanced covers are display assets; factual citations keep the original sources.
 const enhanced=isSummerPalace?(enhancedCovers as Record<string,EnhancedCover>)[props.spot.spot_name]:undefined
 const photos: CoverPhoto[]=[...(props.spot.image_path?[{url:props.spot.image_path}]:[]),...(enhanced?[enhanced,{url:enhanced.original_url,position:enhanced.position}]:[]),...official]
 return photos.filter((p,index)=>photos.findIndex(other=>other.url===p.url)===index)
})
const photo=computed(()=>candidates.value[failed.value])
const bridge=computed(()=>/桥/.test(props.spot.spot_name))
watch(()=>candidates.value.map(p=>p.url).join('|'),()=>{failed.value=0;ready.value=false})
function tryNext(){ready.value=false;failed.value++}
</script>
<template>
 <span class="scenic-cover" :class="{ready,'scenic-cover--natural':framing==='natural'}">
  <svg class="cover-illustration" viewBox="0 0 500 210" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
   <rect width="500" height="210" fill="#edf2f1"/><circle cx="385" cy="49" r="25" fill="#f9f6eb"/>
   <path d="M0 144L98 42 203 142 316 66 452 147 500 106V210H0Z" fill="#d6e1e0"/>
   <path d="M0 164Q131 126 274 160T500 150V210H0Z" fill="#bfced8"/>
   <path v-if="bridge" d="M105 157Q248 27 395 157M111 151V172M145 119V162M182 95V157M221 83V153M260 82V153M300 92V155M338 113V162M377 144V170M102 169Q248 43 398 169" fill="none" stroke="#fbfaf6" stroke-width="10" stroke-linecap="round"/>
   <g v-else fill="#f8f6ef" stroke="#a7b1c3" stroke-width="3"><path d="M180 160V89H320V160M168 94H332L300 70H200ZM203 70V44H298V70M190 48H311L284 26H217Z"/><path d="M231 160V112H270V160M160 166H340" fill="#d2d8df"/></g>
   <g fill="none" stroke="#f3f7f6" stroke-width="3" opacity=".8"><path d="M42 191H158M315 191H451M181 201H290"/></g>
  </svg>
  <img v-if="photo" :key="photo.url" :src="photo.url" :style="{objectPosition:position||photo.position||'center'}" alt="" loading="lazy" referrerpolicy="no-referrer" @load="ready=true" @error="tryNext" />
  <span v-if="!ready" class="cover-kind">{{ $t('景观示意') }}</span>
 </span>
</template>
<style scoped>
.scenic-cover{position:relative;display:block;width:100%;aspect-ratio:16/10;overflow:hidden;background:#edf1f5}
.cover-illustration,.scenic-cover img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.scenic-cover img{opacity:0;transition:opacity .35s,transform .65s cubic-bezier(.2,.65,.3,1)}
.scenic-cover.ready img{opacity:1}.scenic-cover.ready:hover img{transform:scale(1.015)}
.scenic-cover.ready .cover-illustration{visibility:hidden}
.scenic-cover--natural.ready{aspect-ratio:auto;background:#fff}
.scenic-cover--natural img{position:relative;display:block;height:auto;object-fit:contain}
.scenic-cover--natural.ready:hover img{transform:none}
.cover-kind{position:absolute;bottom:10px;left:12px;font-size:18px;color:#5d6d7b;background:#ffffffc9;padding:3px 8px;border-radius:7px}
@media(prefers-reduced-motion:reduce){.scenic-cover img{transition:none}.scenic-cover.ready:hover img{transform:none}}
</style>
