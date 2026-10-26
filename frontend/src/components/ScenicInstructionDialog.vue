<script setup lang="ts">
import { ref } from 'vue'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import { getSpotInstruction } from '@/api/scenicSpot'
import { t } from '@/i18n'

const visible = ref(false)
const loading = ref(false)
const title = ref('')
const content = ref('')
const error = ref('')
let generation = 0

async function open(spotId: number, name: string) {
  const own = ++generation
  title.value = name
  content.value = ''
  error.value = ''
  visible.value = true
  loading.value = true
  try {
    const { data } = await getSpotInstruction(spotId)
    if (own !== generation) return
    if (data.code !== 0) throw new Error(data.message)
    content.value = data.data
  } catch {
    if (own === generation) error.value = t('游览说明加载失败，请重试')
  } finally {
    if (own === generation) loading.value = false
  }
}

defineExpose({ open })
</script>

<template>
  <el-dialog v-model="visible" :title="title + ' · ' + $t('游览说明')" width="min(960px, 94vw)" append-to-body destroy-on-close>
    <div v-loading="loading" class="scenic-instruction">
      <el-alert v-if="error" :title="error" type="error" :closable="false" />
      <MdPreview v-else editor-id="scenic-instruction" :model-value="content" />
    </div>
    <template #footer><el-button @click="visible = false">{{ $t('关闭') }}</el-button></template>
  </el-dialog>
</template>

<style scoped>
.scenic-instruction { min-height: 100px; max-height: 65dvh; overflow: auto; font-size: 18px; line-height: 1.7; }
</style>
