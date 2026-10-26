<script setup lang="ts">import { t } from '@/i18n'

import { onMounted, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es'
import type { InputInstance } from 'element-plus'
import { Plus } from '@/icons'

import FileUpload from '@/components/FileUpload.vue'

import {
  type ScenicSpotItem,
  getSpotDetail,
  createSpot,
  editSpot,
  aiGenerateSpotContent,
} from '@/api/scenicSpot'
import { AxiosError } from 'axios'

const router = useRouter()

// 定义 URL ID 传参
const props = defineProps({
  spotId: {
    type: String,
    default: '',
  },
})

// 步骤条ID
const currentStep = ref(0)

const saveLoading = ref(false)

// 景点信息
const spotInfo = ref({} as ScenicSpotItem)
spotInfo.value.spot_id = 0 // 初始化

// 标签操作
const tagList = ref([] as string[])
const inputTagValue = ref('')
const inputTagVisible = ref(false)
const InputTagRef = ref<InputInstance>()

const handleTagClose = (tag: string) => {
  tagList.value.splice(tagList.value.indexOf(tag), 1)
}

const showTagInput = () => {
  inputTagVisible.value = true
  nextTick(() => {
    InputTagRef.value!.input!.focus()
  })
}

const handleTagInputConfirm = () => {
  if (inputTagValue.value) {
    tagList.value.push(inputTagValue.value)
  }
  inputTagVisible.value = false
  inputTagValue.value = ''
}

// AI 生成
const aiGenerating = ref(false)

const handleAiGenerate = async () => {
  if (!spotInfo.value.spot_name?.trim()) {
    ElMessage.warning(t("请先输入景点名称"))
    return
  }
  aiGenerating.value = true
  try {
    const { data } = await aiGenerateSpotContent(spotInfo.value.spot_name.trim())
    if (data.code === 0) {
      spotInfo.value.description = data.data.description || ''
      spotInfo.value.history_detail = data.data.history_detail || ''
      ElMessage.success(t("AI 已根据游览说明文档自动生成景点描述和历史详情"))
    } else {
      ElMessage.error(t("AI生成失败：") + data.message)
    }
  } catch (e: any) {
    ElMessage.error(t("AI服务请求失败：") + (e?.message || t("未知错误")))
  } finally {
    aiGenerating.value = false
  }
}

// 表单提交
const onSubmit = async () => {
  const statusInfo = props.spotId ? t("编辑景点") : t("新建景点")

  try {
    saveLoading.value = true

    // 将标签数组变成 ; 分割的字符串
    spotInfo.value.tags = tagList.value.join(';')

    const spotIdNum = props.spotId ? Number(props.spotId) : 0
    let response

    if (spotIdNum === 0) {
      // 新增景点
      response = await createSpot(spotInfo.value)
    } else {
      // 编辑景点
      response = await editSpot(spotIdNum, spotInfo.value)
    }

    const { data } = response
    if (data.code === 0) {
      ElMessage.success(statusInfo + t("成功!"))
      saveLoading.value = false
      router.push({ name: 'ScenicSpotList' })
    } else {
      saveLoading.value = false
      ElMessage.error(statusInfo + t("失败, ") + data.message)
      throw new Error(statusInfo + t("失败, ") + data.message)
    }
  } catch (error: unknown) {
    saveLoading.value = false
    if (error instanceof AxiosError) {
      ElMessage.error(t("失败:") + error.message)
    } else {
      ElMessage.error(t("未知错误：") + error)
    }
  }
}

onMounted(async () => {
  // 获取景点信息
  if (props.spotId) {
    try {
      const { data } = await getSpotDetail(Number(props.spotId))
      if (data.code === 0) {
        spotInfo.value = data.data
        tagList.value = spotInfo.value.tags
          ? spotInfo.value.tags.split(';').filter(Boolean)
          : []
        ElMessage.success(t("获取景点信息成功"))
      } else {
        ElMessage.error(data.message)
      }
    } catch (error: unknown) {
      if (error instanceof AxiosError) {
        ElMessage.error(t("失败:") + error.message)
      } else {
        ElMessage.error(t("未知错误：") + error)
      }
    }
  }
})
</script>

<template>
  <div>
    <!-- 返回栏 -->
    <el-page-header @back="router.push({ name: 'ScenicSpotList' })" :title='$t("返回")'>
      <template #content>
        <div class="flex items-center">
          <span class="text-large font-600 mr-3">
            {{ $t(props.spotId ? '编辑' : '新建') }} {{ $t("景点") }}</span>
        </div>
      </template>
      <template #extra>
        <div class="flex items-center">
          <el-button type="primary" class="ml-2" @click="onSubmit" :loading="saveLoading"
            >{{ $t("保存") }}</el-button
          >
        </div>
      </template>
    </el-page-header>
    <el-card>
      <template #header>
        <!-- 步骤条 -->
        <el-steps :active="currentStep" finish-status="success" align-center>
          <el-step :title='$t("头图 & 游览说明")' @click="currentStep = 0" />
          <el-step :title='$t("景点信息")' @click="currentStep = 1" />
        </el-steps>
      </template>
      <!-- 表单 -->
      <el-form :model="spotInfo" label-width="120" size="large">
        <div v-show="currentStep === 0">
          <!-- 景点头图 & 游览说明 -->
          <el-form-item :label='$t("景点图片")'>
            <FileUpload v-model="spotInfo.image_path" file-type="image" />
          </el-form-item>

          <el-form-item :label='$t("游览说明")'>
            <FileUpload v-model="spotInfo.instruction" file-type="doc" />
          </el-form-item>
        </div>

        <div v-show="currentStep === 1">
          <!-- 景点信息 -->
          <el-form-item :label='$t("景点名称")'>
            <el-input v-model="spotInfo.spot_name" maxlength="50" show-word-limit />
          </el-form-item>

          <el-form-item :label='$t("景点分类")'>
            <el-select v-model="spotInfo.category" :placeholder='$t("请选择景点分类")'>
              <el-option :label='$t("自然景观")' value="natural" />
              <el-option :label='$t("历史古迹")' value="historical" />
              <el-option :label='$t("文化体验")' value="cultural" />
              <el-option :label='$t("现代建筑")' value="modern" />
              <el-option :label='$t("综合景区")' value="comprehensive" />
            </el-select>
          </el-form-item>

          <el-form-item :label='$t("景点标签")'>
            <el-tag
              v-for="(tag, index) in tagList"
              :key="index"
              :disable-transitions="false"
              closable
              @close="handleTagClose(tag)"
              round
              size="large"
              style="margin: 3px"
            >
              {{ $t(tag) }}
            </el-tag>

            <el-input
              v-if="inputTagVisible"
              ref="InputTagRef"
              v-model="inputTagValue"
              class="w-20"
              @keyup.enter="handleTagInputConfirm"
              @blur="handleTagInputConfirm"
              size="large"
            />
            <el-button
              v-else
              @click="showTagInput"
              circle
              :icon="Plus"
              type="primary"
              plain
              size="small"
              :disabled="tagList.length > 7"
            >
            </el-button>
          </el-form-item>

          <el-form-item :label='$t("所在位置")'>
            <el-input v-model="spotInfo.location" maxlength="200" show-word-limit />
          </el-form-item>

          <el-form-item :label='$t("最佳季节")'>
            <el-select v-model="spotInfo.best_season" :placeholder='$t("请选择最佳游览季节")'>
              <el-option :label='$t("春季")' value="Spring" />
              <el-option :label='$t("夏季")' value="Summer" />
              <el-option :label='$t("秋季")' value="Autumn" />
              <el-option :label='$t("冬季")' value="Winter" />
              <el-option :label='$t("全年")' value="AllYear" />
            </el-select>
          </el-form-item>

          <el-form-item :label='$t("景点描述")'>
            <el-input
              v-model="spotInfo.description"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 8 }"
              maxlength="2000"
              show-word-limit
            />
          </el-form-item>

          <el-form-item :label='$t("历史详情")'>
            <el-input
              v-model="spotInfo.history_detail"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 8 }"
              maxlength="5000"
              show-word-limit
            />
          </el-form-item>

          <el-form-item :label="$t('拍照建议')"><el-input v-model="spotInfo.photo_tips" type="textarea" :rows="3" maxlength="5000" /></el-form-item>
          <el-form-item :label="$t('游览提醒')"><el-input v-model="spotInfo.tour_tips" type="textarea" :rows="3" maxlength="5000" /></el-form-item>
          <el-form-item :label="$t('周边服务设施')"><el-input v-model="spotInfo.service_facilities" type="textarea" :rows="3" maxlength="5000" /></el-form-item>
          <el-form-item :label="$t('建议停留分钟')"><el-input-number v-model="spotInfo.visit_duration" :min="1" :max="480" /></el-form-item>
          <el-form-item :label="$t('所属城市')"><el-input v-model="spotInfo.city" maxlength="50" /></el-form-item>
          <el-form-item :label="$t('WGS84 纬度')"><el-input-number v-model="spotInfo.latitude" :min="-90" :max="90" :precision="7" /></el-form-item>
          <el-form-item :label="$t('WGS84 经度')"><el-input-number v-model="spotInfo.longitude" :min="-180" :max="180" :precision="7" /></el-form-item>
          <div class="bottom-gen-btn">
            <el-button type="success" :loading="aiGenerating" @click="handleAiGenerate">{{ $t("AI 生成") }}</el-button>
            <span class="gen-hint">{{ $t("根据\"游览说明\"文件夹中的 .md 文档自动填充景点描述和历史详情") }}</span>
          </div>
        </div>
      </el-form>

      <template #footer>
        <div class="form-bottom-btn">
          <el-button v-show="currentStep > 0" @click="currentStep--" :disabled="saveLoading"
            >{{ $t("上一步") }}</el-button
          >
          <el-button v-show="currentStep < 1" @click="currentStep++">{{ $t("下一步") }}</el-button>
          <el-button
            v-show="currentStep === 1"
            type="primary"
            @click="onSubmit"
            :loading="saveLoading"
            >{{ $t("保存") }}</el-button
          >
        </div>
      </template>
    </el-card>
  </div>
</template>

<style lang="scss" scoped>
.el-card {
  width: auto;
  margin-top: 20px;
}

// 步骤条
.el-step {
  cursor: pointer;
}

// 底部按钮
.form-bottom-btn {
  display: flex;
  justify-content: center;
  align-items: center;
}

// 中间表单控件
.el-form {
  padding: 0px 180px 0px 100px;
}

// 每个表单底部 AI 生成按钮
.bottom-gen-btn {
  margin-top: 15px;
  margin-left: 70px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 6px;

  .gen-hint {
    font-size: 18px;
    color: var(--text-muted);
  }
}
</style>
