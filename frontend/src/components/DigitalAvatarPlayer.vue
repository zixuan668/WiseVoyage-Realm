<script setup lang="ts">import { t } from '@/i18n'

import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { request_handler } from '@/api/base'
import XingyunGuide from './XingyunGuide.vue'
const xingyunRef = ref<InstanceType<typeof XingyunGuide> | null>(null)
const xingyunConnected = ref(false)
const props = withDefaults(defineProps<{ guideId?: number; tourId?: number; stationMode?:boolean; stationVisit?:{visit_id:string;access_token:string}; framing?: 'full' | 'half'; posterImage?: string; sourceVideo?: string; width?: number; height?: number; audioElement?: HTMLAudioElement | null; speaking?: boolean; busy?: boolean; volume?: number }>(), { volume: 1 })
const emit = defineEmits<{ playing: [value: boolean]; connected: [value: boolean] }>()
const posterUrl = computed(() => (props.posterImage || '').replace(/\\/g, '/').replace(/^https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?(?=\/api\/v1\/files)/, ''))
type AvatarJob = { job_id?: string; access_token?: string; status?: string; message?: string }
type Capability = { preferredMode?: string; realistic: { ready: boolean; message: string } }
const mode = ref('audio')
const state = ref<Capability | null>(null)
const capabilityLoading = ref(true)
const capabilityRevision=ref(0)
const message = ref('语音导览 · 提问后播放本轮讲解')
const videoUrl = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
let version = 0
let capabilityReady: Promise<void> = Promise.resolve()
let capabilityVersion=0
function stop() { xingyunRef.value?.stop(); version++; if(timer)clearTimeout(timer);timer=undefined;videoUrl.value=''; props.audioElement?.pause();emit('playing',false) }
function updateMessage() { message.value = mode.value === 'audio' ? t("语音导览 · 提问后播放本轮讲解") : state.value?.realistic?.message || t("正在查询数字人状态") }
async function poll(job: AvatarJob, current: number) {
  if(current!==version)return
  try {
    const response=await request_handler.get('/avatar/jobs/'+job.job_id,{params:{token:job.access_token}})
    if(current!==version)return
    const data=response.data.data
    if(data.status==='completed'){videoUrl.value=data.video_url;message.value='视频已生成';return}
    if(data.status==='failed'){message.value=data.message||t("视频生成失败");return}
    message.value=data.status==='processing'?t("正在生成口型视频…"):t("视频生成排队中")
    timer=setTimeout(()=>poll(job,current),1500)
  }catch{if(current===version)message.value='获取视频状态失败，请重新提问'}
}
function acceptJob(job?: AvatarJob | null) { if(job?.job_id){poll(job,version);return true} if(job?.message)message.value=job.message;return false }
watch(()=>[props.guideId,capabilityRevision.value],([id])=>{
  const own=++capabilityVersion
  stop();state.value=null;capabilityLoading.value=true
  capabilityReady=(async()=>{if(!id){capabilityLoading.value=false;return}try{const response=await request_handler.get('/avatar/capabilities/'+id,{timeout:12000});if(own===capabilityVersion){state.value=response.data.data;mode.value=state.value?.preferredMode==='xingyun'?'audio':state.value?.realistic.ready?'realistic':'audio';updateMessage()}}catch{if(own===capabilityVersion)message.value='数字人状态查询失败，请刷新重试'}finally{if(own===capabilityVersion)capabilityLoading.value=false}})()
},{immediate:true})
onBeforeUnmount(()=>{capabilityVersion++;stop()})
defineExpose({getMode:async()=>{await capabilityReady;return xingyunRef.value?.isReady() ? 'xingyun' : mode.value},speak:(text?:string)=>xingyunRef.value?.speak(text)||false,acceptJob,stop})
</script>
<template>
  <div class="digital-avatar" :class="{'station-avatar':stationMode}" :style="{maxWidth:stationMode?'none':(width||360)+'px'}">
    <div class="viewport" :style="{minHeight:0+'px'}">
      <div v-if="!state" class="avatar-loading" role="status">{{ $t(capabilityLoading ? '数字人正在加载中' : message) }}<button v-if="!capabilityLoading" type="button" @click="capabilityRevision++">{{ $t('重试') }}</button></div>
      <div v-if="stationMode && state?.preferredMode === 'xingyun' && !stationVisit" class="avatar-loading" role="status">{{ $t('数字人正在加载中') }}</div>
      <XingyunGuide v-if="!stationMode || !!stationVisit" v-show="state?.preferredMode === 'xingyun' && (!!tourId || !!stationVisit)" ref="xingyunRef" :guide-id="guideId" :tour-id="tourId" :station-visit="stationVisit" :station-mode="stationMode" :volume="volume" :framing="framing || 'full'" @playing="emit('playing', $event)" @connected="xingyunConnected=$event; emit('connected', $event)" />
      <video v-show="!xingyunConnected" v-if="videoUrl" :key="'speech-'+videoUrl" :volume="volume" :muted="false" :loop="false" playsinline :src="videoUrl" controls autoplay @play="emit('playing',true)" @pause="emit('playing',false)" @ended="emit('playing',false)" @error="message='视频播放失败，请检查网络';emit('playing',false)" />
      <img v-show="!xingyunConnected" v-else-if="!stationMode && posterUrl && state && state.preferredMode !== 'xingyun'" :src="posterUrl" :alt='$t("所选数字人全身形象")' style="width:100%;height:100%;min-height:0;object-fit:contain" />
      <div v-show="!xingyunConnected" v-else-if="state && state.preferredMode !== 'xingyun'" class="placeholder"><strong>{{ $t("待开发：请上传数字人形象素材") }}</strong></div>
    </div>
    <p v-if="state && !xingyunConnected && state.preferredMode !== 'xingyun'" class="playback-message" role="status">{{ $t(message) }}</p>
  </div>
</template>
<style scoped>
.avatar-loading{display:flex;align-items:center;justify-content:center;flex:1;padding:24px;font-size:18px;line-height:1.6;color:var(--text-secondary)}
.digital-avatar{height:100%;max-height:100%;display:flex;flex-direction:column;width:100%;margin:auto;padding:14px;box-sizing:border-box}.viewport{flex:1;min-height:0;display:flex;flex-direction:column;align-items:center;justify-content:center;border: 1px solid var(--glass-line);background: var(--glass);border-radius:16px;overflow:hidden}.viewport video{width:100%;max-height:440px;object-fit:contain}.playback-message{font-size:18px;color: var(--text-secondary);line-height:1.6}.placeholder{padding:28px;text-align:center;display:flex;flex-direction:column;gap:18px;align-items:center}.placeholder span{width:74px;height:74px;border-radius:22px;line-height:74px;background: var(--glass);color: var(--champagne-text);font-size:30px}.placeholder strong{font-size:18px;line-height:1.8;color: var(--text-secondary)}.placeholder small{font-size:18px;line-height:1.7;color:var(--text-muted)}
</style>
