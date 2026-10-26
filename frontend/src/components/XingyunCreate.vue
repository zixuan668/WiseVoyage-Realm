<script setup lang="ts">import { t } from '@/i18n'

import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { request_handler } from '@/api/base'
import { header_authorization } from '@/api/user'
import FileUpload from '@/components/FileUpload.vue'
const emit = defineEmits<{ saved: [] }>()
const visible = ref(false)
const busy = ref(false)
const form = reactive({ name: '', character: '', app_id: '', app_secret: '', voice_label: '', voice_style: 'male_wenhou', poster_image: '', avatar: '' })
function open() {
  Object.assign(form, { name: '', character: '', app_id: '', app_secret: '', voice_label: '', voice_style: 'male_wenhou', poster_image: '', avatar: '' })
  visible.value = true
}
async function save() {
  if (!form.name.trim() || !form.app_id.trim() || !form.app_secret.trim()) {
    ElMessage.warning(t("请填写导游名称、App ID 和 App Secret")); return
  }
  if (!form.poster_image || !form.avatar) { ElMessage.warning(t("请上传展示封面和头像")); return }
  busy.value = true
  try {
    await request_handler.post('/xingyun/guides', form, { headers: { Authorization: header_authorization.value } })
    form.app_secret = ''; visible.value = false
    ElMessage.success(t("已创建并绑定应用，请连接验证后上架"))
    emit('saved')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || t("创建失败，请检查后端连接"))
  } finally { busy.value = false }
}
</script>
<template>
  <el-button type="primary" @click="open">{{ $t("新增数字人") }}</el-button>
  <el-dialog v-model="visible" :title='$t("新增数字人")' width="min(600px, 94vw)" :close-on-click-modal="false" :before-close="(done: () => void) => { if (!busy) done() }" @closed="form.app_secret=''">
    <p>{{ $t("请上传星云的数字人。") }}</p>
    <p>{{ $t("在数字人平台保存人物、背景和音色，再点击「接入 SDK」复制应用凭据。每个人物分别添加一次。") }}</p>
    <el-form label-width="110px" :disabled="busy">
      <el-form-item :label='$t("导游名称")' required><el-input v-model="form.name" maxlength="30" /></el-form-item>
      <el-form-item label="App ID" required><el-input v-model="form.app_id" maxlength="200" autocomplete="off" /></el-form-item>
      <el-form-item label="App Secret" required><el-input v-model="form.app_secret" maxlength="500" type="password" show-password autocomplete="new-password" /></el-form-item>
      <el-form-item :label='$t("音色名称")'><el-input v-model="form.voice_label" maxlength="80" :placeholder='$t("应用中所选音色的名称，可留空")' /></el-form-item>
      <el-form-item :label='$t("展示封面")' required><FileUpload v-model="form.poster_image" file-type="image" /></el-form-item>
      <el-form-item :label='$t("头像")' required><FileUpload v-model="form.avatar" file-type="image" /></el-form-item>
    </el-form>
    <p>{{ $t("封面和头像用于网页、App的人物选择与预览展示，可使用对应人物截图。无需上传人物视频。实时导览的背景和音色使用数字人应用配置；网页和App导览页均完整显示全身。保存后默认下架，密钥由后端加密保存。") }}</p>
    <template #footer>
      <el-button :disabled="busy" @click="visible=false">{{ $t("取消") }}</el-button>
      <el-button type="primary" :loading="busy" @click="save">{{ $t("创建并绑定") }}</el-button>
    </template>
  </el-dialog>
</template>
