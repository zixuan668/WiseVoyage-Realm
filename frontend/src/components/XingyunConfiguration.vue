<script setup lang="ts">import { t } from '@/i18n'

import { onMounted, ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { request_handler } from '@/api/base'
import { header_authorization } from '@/api/user'
const props = defineProps<{ guideId: number; compact?: boolean }>()
const emit = defineEmits<{ saved: [] }>()
const visible = ref(false)
const busy = ref(false)
const loaded = ref(false)
const error = ref('')
const form = reactive({ app_id: '', app_secret: '', voice_label: '', use_xingyun: true, secret_configured: false,
  app_id_en: '', app_secret_en: '', voice_label_en: '', secret_configured_en: false })
const headers = () => ({ Authorization: header_authorization.value })
function errorText(e: any) { return e.response?.data?.detail || e.message || t("操作失败") }
async function refresh() {
  try {
    const { data } = await request_handler.get('/xingyun/admin/' + props.guideId, { headers: headers() })
    Object.assign(form, data, { app_secret: '' })
    loaded.value = true; error.value = ''
  } catch(e) { error.value = errorText(e) }
}
async function open() { await refresh(); if (!error.value) visible.value = true }
async function save() {
  if (!form.app_id.trim() || (!form.secret_configured && !form.app_secret.trim())) { ElMessage.warning(t("请填写这个人物对应的 App ID 和 App Secret")); return }
  busy.value = true
  try {
    await request_handler.put('/xingyun/admin/' + props.guideId, {
      app_id: form.app_id.trim(), app_secret: form.app_secret.trim(), voice_label: form.voice_label.trim(), use_xingyun: form.use_xingyun,
      app_id_en: form.app_id_en.trim(), app_secret_en: form.app_secret_en.trim(), voice_label_en: form.voice_label_en.trim(),
    }, { headers: headers() })
    form.app_secret = ''; form.app_secret_en = ''; visible.value = false
    ElMessage.success(t("应用绑定已保存")); emit('saved'); await refresh()
  } catch(e) { ElMessage.error(errorText(e)) }
  finally { busy.value = false }
}
async function remove() {
  try { await ElMessageBox.confirm(t("移除绑定会清除本项目保存的应用凭据，并下架该导游。是否继续？"), t("移除应用绑定")) }
  catch { return }
  busy.value = true
  try { await request_handler.delete('/xingyun/admin/' + props.guideId, { headers: headers() }); ElMessage.success(t("已移除绑定并下架")); visible.value = false; emit('saved'); await refresh() }
  catch(e) { ElMessage.error(errorText(e)) }
  finally { busy.value = false }
}
onMounted(refresh)
</script>
<template>
  <section class="xingyun-config" :class="{ compact }">
    <strong v-if="!compact">{{ $t("数字人应用配置") }}</strong>
    <p v-if="error" role="alert">{{ $t(error) }}</p>
    <p v-else-if="loaded && !compact">{{ $t(form.use_xingyun && form.secret_configured ? '已绑定应用 · 云端连接待验证' : form.secret_configured ? '已保存数字人应用 · 当前使用本地数字人' : '尚未绑定应用') }}</p>
    <p v-else-if="!loaded && !compact">{{ $t("正在读取应用绑定…") }}</p>
    <el-button plain @click="open">{{ $t(form.secret_configured ? '管理应用' : '绑定应用') }}</el-button>
    <el-dialog v-model="visible" :title='$t("绑定该导游的数字人应用")' width="min(580px, 94vw)" class="xingyun-binding-dialog" append-to-body align-center destroy-on-close @closed="form.app_secret=''; form.app_secret_en=''">
      <p>{{ $t("在数字人平台选好人物、背景和音色，保存后点击「接入SDK」，将对应应用凭据填在这里。") }}</p>
      <el-form label-width="130px">
        <el-divider content-position="left">{{ $t("中文应用") }}</el-divider>
        <el-form-item label="中文 App ID" required><el-input v-model="form.app_id" autocomplete="off" maxlength="200" /></el-form-item>
        <el-form-item label="中文 App Secret" :required="!form.secret_configured"><el-input v-model="form.app_secret" type="password" show-password autocomplete="new-password" maxlength="500" :placeholder="$t(form.secret_configured ? '已保存，留空沿用；修改 App ID 时需重新填写' : '输入该应用的密钥')" /></el-form-item>
        <el-form-item :label='$t("中文音色名称")'><el-input v-model="form.voice_label" maxlength="80" :placeholder='$t("填写应用中选定的音色名称，供游客识别")' /></el-form-item>
        <el-form-item :label='$t("启用实时数字人")'><el-switch v-model="form.use_xingyun" /></el-form-item>
        <el-divider content-position="left">{{ $t("英文应用（可选）") }}</el-divider>
        <p>{{ $t("同一个角色在星云里再建一个英文音色应用：界面切英文时用这套凭据，中文模式仍用上面的应用。预览和展示仍只有一个人物。") }}</p>
        <el-form-item label="English App ID"><el-input v-model="form.app_id_en" autocomplete="off" maxlength="200" :placeholder="$t('留空表示英文模式也使用上面的应用')" /></el-form-item>
        <el-form-item label="English Secret" :required="!!form.app_id_en && !form.secret_configured_en"><el-input v-model="form.app_secret_en" type="password" show-password autocomplete="new-password" maxlength="500" :placeholder="$t(form.secret_configured_en ? '已保存，留空沿用' : '英文应用的密钥')" /></el-form-item>
        <el-form-item :label='$t("英文音色名称")'><el-input v-model="form.voice_label_en" maxlength="80" :placeholder="$t('例如 English female')" /></el-form-item>
      </el-form>
      <p>{{ $t("人物、背景、音色在数字人平台配置；此处只绑定应用。密钥由后端加密保存，不回显。") }}</p>
      <template #footer>
        <el-button v-if="form.secret_configured" type="danger" plain :disabled="busy" @click="remove">{{ $t("移除绑定") }}</el-button>
        <el-button @click="visible=false" :disabled="busy">{{ $t("取消") }}</el-button>
        <el-button type="primary" :loading="busy" @click="save">{{ $t("保存绑定") }}</el-button>
      </template>
    </el-dialog>
  </section>
</template>
<style scoped>
.xingyun-config{padding:16px;margin:18px 0;background: var(--glass);border: 1px solid var(--glass-line);border-radius:12px}.xingyun-config strong{font-size:18px}.xingyun-config p{font-size:18px;line-height:1.8;color: var(--text-secondary)}
.xingyun-config.compact{display:flex;align-items:center;flex-wrap:wrap;min-width:0;gap:10px;padding:0;margin:0;border:0;border-radius:0;background:transparent}
.xingyun-config.compact p{min-width:0;margin:0;font-size:18px;line-height:1.5}
.xingyun-config.compact :deep(.el-button){width:100%;min-height:42px;height:auto;margin:0;padding:9px 10px;font-size:18px;border-radius:10px;white-space:normal}
/* The dialog is teleported out of the animated, clipped guide card. */
:global(.xingyun-binding-dialog.el-dialog){display:flex;flex-direction:column;max-height:calc(100dvh - 32px);overflow:hidden}
:global(.xingyun-binding-dialog .el-dialog__header),:global(.xingyun-binding-dialog .el-dialog__footer){flex-shrink:0}
:global(.xingyun-binding-dialog .el-dialog__body){min-height:0;overflow-y:auto;overscroll-behavior:contain}
:global(.xingyun-binding-dialog p){font-size:18px;line-height:1.8;color:var(--text-secondary);overflow-wrap:anywhere}
</style>
