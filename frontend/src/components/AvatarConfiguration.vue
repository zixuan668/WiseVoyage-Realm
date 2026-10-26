<script setup lang="ts">import { t } from '@/i18n'

import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { request_handler } from '@/api/base'
import { header_authorization } from '@/api/user'
const props = defineProps<{ guideId: number }>()
type Capability = { realistic: { ready: boolean; message: string; sourceConfigured: boolean } }
const state = ref<Capability | null>(null)
const error = ref('')
const uploading = ref(false)
const motionConfig = ref<{configured:boolean;message:string;default_prompt:string} | null>(null)
type MotionJob = {job_id:string;status:string;message:string;video_url:string}
const motion = ref<MotionJob | null>(null)
const prompt = ref('')
const recoveryTaskId = ref('')
const motionBusy = ref(false)
const motionError = ref('')
let disposed = false
let pollTimer: ReturnType<typeof setTimeout> | undefined
const auth = () => ({Authorization:header_authorization.value})
function errorMessage(e: unknown) {
  const value=e as {response?:{data?:{detail?:string}}}
  return value.response?.data?.detail || t("请求失败，请检查服务连接")
}
function schedulePoll() {
  if(disposed)return
  if(pollTimer)clearTimeout(pollTimer)
  if(motion.value && ['pending','running'].includes(motion.value.status))pollTimer=setTimeout(refreshMotion,15000)
}
async function loadMotion() {
  try {
    const [config,job]=await Promise.all([request_handler.get('/avatar/motion-config',{headers:auth()}),request_handler.get('/avatar/motion/'+props.guideId,{headers:auth()})])
    motionConfig.value=config.data.data;motion.value=job.data.data
    if(!prompt.value)prompt.value=motionConfig.value?.default_prompt||''
    schedulePoll()
  } catch(e) {motionError.value=errorMessage(e)}
}
async function generateMotion() {
  if(motionBusy.value)return
  motionBusy.value=true;motionError.value=''
  try {
    const response=await request_handler.post('/avatar/motion/'+props.guideId,{prompt:prompt.value},{headers:auth(),timeout:90000})
    motion.value=response.data.data;schedulePoll()
  } catch(e) {motionError.value=errorMessage(e);await loadMotion()}
  finally {motionBusy.value=false}
}
async function refreshMotion() {
  if(!motion.value)return
  motionBusy.value=true
  try {const r=await request_handler.post('/avatar/motion-jobs/'+motion.value.job_id+'/refresh',null,{headers:auth(),timeout:180000});motion.value=r.data.data;motionError.value=''}
  catch(e) {motionError.value=errorMessage(e)}
  finally {motionBusy.value=false;schedulePoll()}
}
async function recoverMotion() {
  if(!motion.value||!recoveryTaskId.value.trim())return
  motionBusy.value=true
  try {const r=await request_handler.post('/avatar/motion-jobs/'+motion.value.job_id+'/recover',{task_id:recoveryTaskId.value.trim()},{headers:auth(),timeout:180000});motion.value=r.data.data;motionError.value='';schedulePoll()}
  catch(e) {motionError.value=errorMessage(e)}
  finally {motionBusy.value=false}
}
async function applyMotion() {
  if(!motion.value)return
  motionBusy.value=true
  try {const r=await request_handler.post('/avatar/motion-jobs/'+motion.value.job_id+'/apply',null,{headers:auth()});motion.value=r.data.data;ElMessage.success(t("动作视频已应用"));await refresh()}
  catch(e) {motionError.value=errorMessage(e)}
  finally {motionBusy.value=false}
}
const statusText:Record<string,string>={submitting:'正在提交',pending:'服务排队中',running:'正在生成',completed:'已生成，待预览应用',applied:'已应用',failed:'生成失败',unknown:'提交结果不确定，请核对百炼控制台'}
async function refresh() {
  error.value = ''
  try { const response = await request_handler.get('/avatar/capabilities/' + props.guideId); state.value = response.data.data }
  catch { error.value = '数字人服务状态获取失败' }
}
async function upload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.mp4') || file.size > 200 * 1024 * 1024) { ElMessage.error(t("请选择 200MB 以内的 MP4 视频")); input.value = ''; return }
  uploading.value = true
  try { const form = new FormData(); form.append('file', file); await request_handler.post('/avatar/source/' + props.guideId, form, { headers: { Authorization: header_authorization.value } }); ElMessage.success(t("真人素材已保存")); await refresh() }
  catch(e) { ElMessage.error(errorMessage(e)) }
  finally { uploading.value = false; input.value = '' }
}
onMounted(()=>{refresh();loadMotion()})
onBeforeUnmount(()=>{disposed=true;if(pollTimer)clearTimeout(pollTimer)})
watch(()=>props.guideId,()=>{motion.value=null;prompt.value='';if(pollTimer)clearTimeout(pollTimer);refresh();loadMotion()})
</script>
<template>
  <div class="avatar-config">
    <strong>{{ $t("数字人接入状态") }}</strong>
    <p v-if="error" class="error">{{ $t(error) }}</p>
    <template v-else-if="state">
      <p><span :class="{ready:state.realistic.ready}">{{ $t("真人") }}</span>{{ state.realistic.message }}</p>
    </template>
    <p v-else>{{ $t("正在查询后端状态…") }}</p>
    <div class="actions"><label class="upload"><input type="file" accept="video/mp4,.mp4" :disabled="uploading" @change="upload" />{{ $t(uploading ? '正在上传…' : '上传动作视频') }}</label><el-button text @click="refresh">{{ $t("刷新状态") }}</el-button></div>
    <small>{{ $t("上传3至30秒的MP4：全身完整入镜、头部朝前、动作小幅自然、固定镜头。系统会检查视频解码和画面变化，动作质量需预览确认。") }}</small>
    <div class="motion-panel">
      <strong>{{ $t("海报生成全身动作") }}</strong>
      <p>{{ motionConfig?.message || '正在查询动作生成配置…' }}</p>
      <el-input v-model="prompt" type="textarea" :rows="4" maxlength="800" :placeholder='$t("描述欢迎、点头、讲解手势等动作")' />
      <small>{{ $t("会将该角色海报提交到阿里云百炼，调用会产生费用。生成效果需确认人物、服装与动作一致。") }}</small>
      <div class="actions">
        <el-button :disabled="!motionConfig?.configured || motionBusy || !prompt.trim() || !!(motion && ['submitting','pending','running','unknown'].includes(motion.status))" @click="generateMotion">{{ $t("生成动作视频（收费）") }}</el-button>
        <el-button v-if="motion" :disabled="motionBusy" @click="refreshMotion">{{ $t("刷新任务") }}</el-button>
      </div>
      <p v-if="motion">{{ $t(statusText[motion.status] || motion.status) }} {{ motion.message ? '：'+motion.message : '' }}</p>
      <div v-if="motion?.status==='unknown'">
        <el-input v-model="recoveryTaskId" :placeholder='$t("在百炼控制台找到原任务，粘贴任务ID")' />
        <el-button :disabled="motionBusy || !recoveryTaskId.trim()" @click="recoverMotion">{{ $t("恢复原任务") }}</el-button>
      </div>
      <p v-if="motionError" class="error">{{ $t(motionError) }}</p>
      <video v-if="motion?.video_url" :src="motion.video_url" controls playsinline class="motion-preview" />
      <el-button v-if="motion?.status==='completed'" :disabled="motionBusy" @click="applyMotion">{{ $t("使用这段动作视频") }}</el-button>
    </div>
  </div>
</template>
<style scoped>
.avatar-config{padding:16px;margin:18px 0 4px;background: var(--glass);border: 1px solid var(--glass-line);border-radius:12px}.avatar-config strong{font-size:18px}.avatar-config p{font-size:18px;color: var(--text-secondary);line-height:1.7;margin:10px 0;display:flex;gap:10px}.avatar-config span{background: var(--glass);border-radius:5px;padding:0 6px;flex-shrink:0}.avatar-config span.ready{background: var(--glass);color: var(--champagne-text)}.actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px}.motion-panel{margin-top:18px;padding-top:16px;border-top: 1px solid var(--glass-line)}.motion-preview{display:block;width:100%;max-height:460px;object-fit:contain;margin:12px 0}.upload{position:relative;padding:7px 10px;background: var(--glass);color: var(--champagne-text);border-radius:7px;font-size:18px;cursor:pointer}.upload input{position:absolute;inset:0;width:100%;opacity:0;cursor:pointer}.avatar-config small{display:block;margin-top:10px;color: var(--text-muted);line-height:1.6}.avatar-config .error{color: var(--champagne-text)}
</style>
