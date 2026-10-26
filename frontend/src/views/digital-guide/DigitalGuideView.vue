<script setup lang="ts">import { t } from '@/i18n'

import { onMounted, ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus/es'
import { Delete, Edit } from '@/icons'
import AvatarConfiguration from '@/components/AvatarConfiguration.vue'
import XingyunConfiguration from '@/components/XingyunConfiguration.vue'
import XingyunCreate from '@/components/XingyunCreate.vue'
import { header_authorization } from '@/api/user'
import { request_handler } from '@/api/base'

import {
  getGuideList,
  getGuideDetail,
  createGuide,
  editGuide,
  deleteGuide,
  type DigitalGuide,
} from '@/api/digitalHuman'
import FileUpload from '@/components/FileUpload.vue'
import { adminAssetUrl } from '@/utils/adminAssetUrl'
import { AxiosError } from 'axios'

// ======================== 列表数据 ========================

const guideList = ref<DigitalGuide[]>([])
const loading = ref(false)

const fetchGuides = async () => {
  loading.value = true
  try {
    const { data } = await getGuideList(1, 100)
    if (data.code === 0) {
      guideList.value = data.data.guide_list
    } else {
      ElMessage.error(t("获取数字导游列表失败：") + data.message)
    }
  } catch (error: unknown) {
    if (error instanceof AxiosError) {
      ElMessage.error(t("获取数字导游列表失败：") + error.message)
    } else {
      ElMessage.error(t("未知错误"))
    }
  } finally {
    loading.value = false
  }
}

// ======================== 卡片展示 ========================

// ======================== 对话框控制 ========================

const dialogVisible = ref(false)
const dialogTitle = ref('新增数字导游')
const isEditMode = ref(false)
const saving = ref(false)

const form = reactive({
  is_enabled: false,
  guide_id: 0,
  name: '',
  avatar: '',
  poster_image: '',
  character: '',
  voice_style: 'female_wenrou',
  voice_speed: 1.0,
  outfit_images: [] as string[],
  base_mp4_path: '',
  tts_reference_audio: '',
  tts_reference_sentence: '',
})

// ======================== 打开对话框 ========================

const openEditDialog = async (guideId: number) => {
  dialogTitle.value = '编辑数字导游'
  isEditMode.value = true
  try {
    const { data } = await getGuideDetail(guideId)
    if (data.code === 0) {
      const item = data.data
      form.guide_id = item.guide_id
      form.is_enabled = item.is_enabled
      form.name = item.name
      form.avatar = item.avatar
      form.poster_image = item.poster_image
      form.character = item.character
      form.voice_style = item.voice_style
      form.voice_speed = item.voice_speed
      try { form.outfit_images = JSON.parse(item.outfit_images || '[]') } catch { form.outfit_images = [] }
      form.base_mp4_path = item.base_mp4_path
      form.tts_reference_audio = item.tts_reference_audio
      form.tts_reference_sentence = item.tts_reference_sentence
      dialogVisible.value = true
    } else {
      ElMessage.error(t("获取导游详情失败：") + data.message)
    }
  } catch (error: unknown) {
    if (error instanceof AxiosError) {
      ElMessage.error(t("获取导游详情失败：") + error.message)
    } else {
      ElMessage.error(t("未知错误"))
    }
  }
}

// ======================== 保存 ========================

const handleSave = async () => {
  if (!form.name.trim()) {
    ElMessage.warning(t("请输入导游名称"))
    return
  }
  if (!form.poster_image || !form.avatar) { ElMessage.warning(t("请上传全身形象和头像")); return }
  saving.value = true
  try {
    const payload: Partial<DigitalGuide> = {
      is_enabled: form.is_enabled,
      name: form.name,
      character: form.character,
      avatar: form.avatar,
      voice_style: form.voice_style,
      voice_speed: form.voice_speed,
      outfit_images: JSON.stringify(form.outfit_images),
      poster_image: form.poster_image,
      base_mp4_path: form.base_mp4_path,
      tts_reference_audio: form.tts_reference_audio,
      tts_reference_sentence: form.tts_reference_sentence,
    }

    const res = isEditMode.value && form.guide_id > 0
      ? await editGuide(form.guide_id, payload)
      : await createGuide(payload)
    if (res.data.code === 0) {
      ElMessage.success(isEditMode.value ? t("编辑成功") : t("新增成功"))
      dialogVisible.value = false
      await fetchGuides()
    } else {
      ElMessage.error(t("保存失败：") + res.data.message)
    }
  } catch (error: unknown) {
    if (error instanceof AxiosError) {
      ElMessage.error(t("保存失败：") + error.message)
    } else {
      ElMessage.error(t("未知错误"))
    }
  } finally {
    saving.value = false
  }
}

const handleDelete = (guideId: number, name: string) => {
  ElMessageBox.confirm(t("确定删除数字导游“{p0}”吗？", {p0: name}), t("删除确认"), {
    confirmButtonText: t("删除"),
    cancelButtonText: t("取消"),
    type: 'warning',
  }).then(async () => {
    try {
      const { data } = await deleteGuide(guideId)
      if (data.code === 0) {
        ElMessage.success(t("删除成功"))
        await fetchGuides()
      } else {
        ElMessage.error(t("删除失败：") + data.message)
      }
    } catch (error: unknown) {
      ElMessage.error(error instanceof AxiosError ? t("删除失败：{p0}", {p0: error.message}) : t("删除失败"))
    }
  }).catch(() => undefined)
}

async function togglePublication(item: DigitalGuide) {
  try {
    const { data } = await request_handler.put('/digital-guide/publication/' + item.guide_id, { is_enabled: !item.is_enabled }, { headers: { Authorization: header_authorization.value } })
    if (!data.success) throw new Error(data.message)
    ElMessage.success(data.message); await fetchGuides()
  } catch(e: any) { ElMessage.error(e.response?.data?.detail || e.message || t("上下架失败")) }
}

// ======================== 生命周期 ========================

onMounted(() => {
  fetchGuides()

})
</script>

<template>
  <div class="digital-guide-container">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <div class="page-intro">
        <h2>{{ $t("数字导游管理") }}</h2>
      </div>
      <XingyunCreate @saved="fetchGuides" />
    </div>

    <!-- 导游卡片网格 -->
    <div v-loading="loading" class="card-grid">
      <el-empty v-if="!loading && guideList.length === 0" :description='$t("暂无数字导游")' />
      <el-card v-for="item in guideList" :key="item.guide_id" class="guide-card" shadow="never">
        <div class="card-content">
          <el-image v-if="item.poster_image" class="guide-portrait" :src="adminAssetUrl(item.poster_image)" fit="cover" :alt="item.name" :preview-src-list="[adminAssetUrl(item.poster_image)]" preview-teleported />
          <div v-else class="guide-portrait portrait-empty">{{ $t('待上传形象') }}</div>
          <div class="guide-summary">
            <div class="identity-row">
              <h3>{{ $t(item.name) }}</h3>
              <span class="publication-status" :class="{ published: item.is_enabled }">{{ $t(item.is_enabled ? '已上架' : '已下架') }}</span>
            </div>
            <div class="card-actions">
              <XingyunConfiguration :guide-id="item.guide_id" compact @saved="fetchGuides" />
              <el-button :type="item.is_enabled ? 'warning' : 'success'" plain @click="togglePublication(item)">{{ $t(item.is_enabled ? '下架' : '上架') }}</el-button>
              <el-button type="primary" plain @click="openEditDialog(item.guide_id)"><el-icon><Edit /></el-icon>{{ $t('编辑') }}</el-button>
              <el-button v-if="item.name !== '小颐'" type="danger" text @click="handleDelete(item.guide_id, item.name)"><el-icon><Delete /></el-icon>{{ $t('删除') }}</el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="$t(dialogTitle)" width="min(720px, 94vw)" append-to-body destroy-on-close>
      <el-form :model="form" label-width="130px" label-position="right">
        <el-form-item :label='$t("导游名称")' required>
          <el-input v-model="form.name" :placeholder='$t("请输入导游名称")' maxlength="30" show-word-limit />
        </el-form-item>
        <el-form-item :label='$t("游客可选择")'><el-switch v-model="form.is_enabled" /><span class="form-hint">{{ $t("新增人物可先保持下架，绑定应用后再上架。") }}</span></el-form-item>

        <el-form-item :label='$t("全身数字人形象")' required><FileUpload v-model="form.poster_image" file-type="image" /></el-form-item>
        <el-form-item :label='$t("头像")' required><FileUpload v-model="form.avatar" file-type="image" /></el-form-item>
        <AvatarConfiguration v-if="isEditMode && guideList.find(item => item.guide_id === form.guide_id)?.render_mode !== 'xingyun'" :guide-id="form.guide_id" />
        <el-form-item :label='$t("数字人基础视频")'>
          <FileUpload v-model="form.base_mp4_path" file-type="video" />
          <span class="form-hint">{{ $t("上传正面人物 MP4 视频，供真人口型推理使用。") }}</span>
        </el-form-item>

      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="handleSave" :loading="saving">{{ $t("保存") }}</el-button>
          <el-button @click="dialogVisible = false" :disabled="saving">{{ $t("取消") }}</el-button>
        </div>
      </template>
    </el-dialog>


  </div>
</template>

<style lang="scss" scoped>
.digital-guide-container {
  min-height: calc(100vh - 86px);
  padding: 24px 28px 32px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.page-intro h2 { margin: 0; font-size: 24px; font-weight: 700; }
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 440px), 1fr));
  align-items: start;
  gap: 16px;
}
.guide-card {
  container-type: inline-size;
  overflow: hidden;
  border: 1px solid var(--glass-line);
  border-radius: 18px;
  :deep(.el-card__body) { padding: 0; }
}
.card-content {
  display: grid;
  grid-template-columns: 176px minmax(0, 1fr);
  align-items: stretch;
  min-height: 240px;
}
.guide-portrait {
  width: 100%;
  height: 100%;
  min-height: 240px;
  overflow: hidden;
  background: transparent;
  :deep(.el-image__inner) { display: block; object-position: center top; }
}
.portrait-empty { display: grid; place-items: center; color: var(--text-muted); font-size: 18px; }
.guide-summary { display: flex; min-width: 0; flex-direction: column; justify-content: space-between; gap: 24px; padding: 22px; }
.identity-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  h3 { margin: 0; color: var(--text); font-size: 24px; line-height: 1.5; }
}
.publication-status { flex-shrink: 0; padding: 3px 10px; border-radius: 7px; background: #f1f5f9; color: var(--text-muted); font-size: 18px; line-height: 1.6; }
.publication-status.published { background: #ecfdf5; color: #047857; }
.card-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  align-items: start;
  .el-button { width: 100%; min-height: 42px; height: auto; margin: 0; padding: 9px 10px; border-radius: 10px; font-size: 18px; white-space: normal; }
}
@media (max-width: 600px) {
  .digital-guide-container { padding: 18px 14px; }
  .card-content { grid-template-columns: 132px minmax(0, 1fr); }
  .guide-summary { padding: 16px; gap: 18px; }
}
@container (max-width: 500px) {
  .card-content { grid-template-columns: 140px minmax(0, 1fr); }
  .guide-summary { padding: 16px; }
  .card-actions { grid-template-columns: 1fr; }
}
@container (max-width: 300px) {
  .card-content { grid-template-columns: 1fr; }
  .guide-portrait { height: 260px; }
}

// ---- 表单提示 ----

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 18px;
  color: var(--text-muted);
  line-height: 1.6;
}

// ---- 对话框 ----

::v-deep(.el-dialog) {
  border-radius: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
