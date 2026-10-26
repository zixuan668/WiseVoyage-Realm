<script setup lang="ts">import { t } from '@/i18n'

import { onMounted, ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus/es'
import { Plus, Delete, Edit, Top, Bottom } from '@/icons'

import {
  getRouteList,
  getRouteDetail,
  createRoute,
  editRoute,
  deleteRoute,
  type TourRouteItem,
  type RouteCreateData,
} from '@/api/tourRoute'
import { getSpotList, type ScenicSpotItem } from '@/api/scenicSpot'
import { AxiosError } from 'axios'

// ======================== 列表数据 ========================

const routeList = ref<TourRouteItem[]>([])
const loading = ref(false)

const fetchRoutes = async () => {
  loading.value = true
  try {
    const { data } = await getRouteList(1, 100)
    if (data.code === 0) {
      routeList.value = data.data.route_list
    } else {
      ElMessage.error(t("获取路线列表失败：") + data.message)
    }
  } catch (error: unknown) {
    if (error instanceof AxiosError) {
      ElMessage.error(t("获取路线列表失败：") + error.message)
    } else {
      ElMessage.error(t("未知错误"))
    }
  } finally {
    loading.value = false
  }
}

// ======================== 主题映射 ========================

const themeMap: Record<string, string> = {
  history: '历史',
  nature: '自然',
  comprehensive: '综合',
  photography: '摄影',
  family: '亲子',
}

const themeTagType: Record<string, string> = {
  history: '',
  nature: 'success',
  comprehensive: '',
  photography: 'warning',
  family: 'danger',
}

// ======================== 对话框控制 ========================

const dialogVisible = ref(false)
const dialogTitle = ref('新建路线')
const isEditMode = ref(false)
const saving = ref(false)

const form = reactive<RouteCreateData & { route_id?: number }>({
  name: '',
  theme: 'comprehensive',
  estimated_time_minutes: 60,
  description: '',
  spot_ids: [],
})

// ======================== 景点多选 ========================

const spotOptions = ref<ScenicSpotItem[]>([])
const selectedSpots = ref<ScenicSpotItem[]>([])

const fetchSpotOptions = async () => {
  try {
    const { data } = await getSpotList(1, 500)
    if (data.code === 0) {
      spotOptions.value = data.data.spot_list
    }
  } catch (error: unknown) {
    console.error('获取景点列表失败', error)
  }
}

// 拖拽排序
const moveSpotUp = (index: number) => {
  if (index <= 0) return
  const arr = [...selectedSpots.value]
  ;[arr[index - 1], arr[index]] = [arr[index], arr[index - 1]]
  selectedSpots.value = arr
  syncSpotIds()
}

const moveSpotDown = (index: number) => {
  if (index >= selectedSpots.value.length - 1) return
  const arr = [...selectedSpots.value]
  ;[arr[index], arr[index + 1]] = [arr[index + 1], arr[index]]
  selectedSpots.value = arr
  syncSpotIds()
}

const syncSpotIds = () => {
  form.spot_ids = selectedSpots.value.map((s) => s.spot_id)
}

const onSpotSelectChange = (spotIds: number[]) => {
  selectedSpots.value = spotIds
    .map((id) => spotOptions.value.find((s) => s.spot_id === id))
    .filter((s): s is ScenicSpotItem => s !== undefined)
  syncSpotIds()
}

// ======================== 打开对话框 ========================

const openCreateDialog = () => {
  dialogTitle.value = '新建路线'
  isEditMode.value = false
  form.route_id = undefined
  form.name = ''
  form.theme = 'comprehensive'
  form.estimated_time_minutes = 60
  form.description = ''
  form.spot_ids = []
  selectedSpots.value = []
  dialogVisible.value = true
}

const openEditDialog = async (routeId: number) => {
  dialogTitle.value = '编辑路线'
  isEditMode.value = true
  try {
    const { data } = await getRouteDetail(routeId)
    if (data.code === 0) {
      const item = data.data
      form.route_id = item.route_id
      form.name = item.name
      form.theme = item.theme
      form.estimated_time_minutes = item.estimated_time_minutes
      form.description = item.description
      form.spot_ids = [...(item.spot_ids ?? [])]
      selectedSpots.value = (item.spot_ids ?? [])
        .map((id) => spotOptions.value.find((s) => s.spot_id === id))
        .filter((s): s is ScenicSpotItem => s !== undefined)
      dialogVisible.value = true
    } else {
      ElMessage.error(t("获取路线详情失败：") + data.message)
    }
  } catch (error: unknown) {
    if (error instanceof AxiosError) {
      ElMessage.error(t("获取路线详情失败：") + error.message)
    } else {
      ElMessage.error(t("未知错误"))
    }
  }
}

// ======================== 保存 ========================

const handleSave = async () => {
  if (!form.name.trim()) {
    ElMessage.warning(t("请输入路线名称"))
    return
  }
  if (form.spot_ids.length === 0) {
    ElMessage.warning(t("请至少选择一个景点"))
    return
  }
  syncSpotIds()
  saving.value = true
  try {
    let res
    if (isEditMode.value && form.route_id) {
      res = await editRoute(form.route_id, {
        name: form.name,
        theme: form.theme,
        estimated_time_minutes: form.estimated_time_minutes,
        description: form.description,
        spot_ids: form.spot_ids,
      })
    } else {
      res = await createRoute({
        name: form.name,
        theme: form.theme,
        estimated_time_minutes: form.estimated_time_minutes,
        description: form.description,
        spot_ids: form.spot_ids,
      })
    }
    if (res.data.code === 0) {
      ElMessage.success(isEditMode.value ? t("编辑成功") : t("创建成功"))
      dialogVisible.value = false
      await fetchRoutes()
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

// ======================== 删除 ========================

const handleDelete = (routeId: number, name: string) => {
  ElMessageBox.confirm(t("确定要删除路线\"{p0}\"吗？删除后不可恢复。", {p0: name}), t("警告"), {
    confirmButtonText: t("确定"),
    cancelButtonText: t("取消"),
    type: 'warning',
  })
    .then(async () => {
      try {
        const { data } = await deleteRoute(routeId)
        if (data.code === 0) {
          ElMessage.success(t("删除成功"))
          await fetchRoutes()
        } else {
          ElMessage.error(t("删除失败：") + data.message)
        }
      } catch (error: unknown) {
        if (error instanceof AxiosError) {
          ElMessage.error(t("删除失败：") + error.message)
        } else {
          ElMessage.error(t("未知错误"))
        }
      }
    })
    .catch(() => {
      // 用户取消
    })
}

// ======================== 生命周期 ========================

onMounted(async () => {
  await fetchSpotOptions()
  await fetchRoutes()
})
</script>

<template>
  <div class="tour-route-container">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <el-button type="primary" size="large" @click="openCreateDialog">
        <el-icon style="margin-right: 5px"><Plus /></el-icon>{{ $t("新建路线") }}</el-button>
    </div>

    <!-- 路线卡片网格 -->
    <div v-loading="loading" class="card-grid">
      <el-empty v-if="!loading && routeList.length === 0" :description='$t("暂无游览路线")' />

      <div v-for="item in routeList" :key="item.route_id" class="card-row">
            <el-card class="route-card" shadow="hover">
              <!-- 路线名称 -->
              <div class="card-header">
                <span class="route-name">{{ $t(item.name) }}</span>
                <el-tag :type="themeTagType[item.theme] as any" size="small">
                  {{ $t(themeMap[item.theme] || item.theme) }}
                </el-tag>
              </div>

              <!-- 信息条 -->
              <div class="card-meta">
                <span class="meta-item">
                  <strong>{{ $t(item.spot_count ?? item.spot_ids?.length ?? 0) }}</strong>{{ $t("个景点") }}</span>
                <span class="meta-divider">|</span>
                <span class="meta-item">{{ $t("预计") }}<strong>{{ $t(item.estimated_time_minutes) }}</strong>{{ $t("分钟") }}</span>
              </div>

              <!-- 描述预览 -->
              <p class="card-desc">{{ $t(item.description || '暂无描述') }}</p>

              <!-- 底部操作 -->
              <div class="card-actions">
                <el-button type="primary" size="small" @click="openEditDialog(item.route_id)">
                  <el-icon><Edit /></el-icon>{{ $t("编辑") }}</el-button>
                <el-button type="danger" size="small" @click="handleDelete(item.route_id, item.name)">
                  <el-icon><Delete /></el-icon>{{ $t("删除") }}</el-button>
              </div>
            </el-card>
      </div>
    </div>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="$t(dialogTitle)" width="700px" destroy-on-close>
      <el-form :model="form" label-width="110px" label-position="right">
        <el-form-item :label='$t("路线名称")' required>
          <el-input v-model="form.name" :placeholder='$t("请输入路线名称")' maxlength="50" show-word-limit />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label='$t("路线主题")' required>
              <el-select v-model="form.theme" :placeholder='$t("请选择主题")' style="width: 100%">
                <el-option :label='$t("历史文化")' value="history" />
                <el-option :label='$t("自然风光")' value="nature" />
                <el-option :label='$t("综合游览")' value="comprehensive" />
                <el-option :label='$t("摄影打卡")' value="photography" />
                <el-option :label='$t("亲子休闲")' value="family" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label='$t("预计时长")' required>
              <el-input-number
                v-model="form.estimated_time_minutes"
                :min="10"
                :max="480"
                :step="10"
                style="width: 100%"
              />
              <span style="margin-left: 8px; color: var(--text-muted)">{{ $t("分钟") }}</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label='$t("路线描述")'>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            :placeholder='$t("请输入路线描述")'
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item :label='$t("包含景点")' required>
          <el-select
            v-model="form.spot_ids"
            multiple
            filterable
            :placeholder='$t("请选择景点（可多选）")'
            style="width: 100%"
            @change="onSpotSelectChange"
          >
            <el-option
              v-for="spot in spotOptions"
              :key="spot.spot_id"
              :label="$t(spot.spot_name)"
              :value="spot.spot_id"
            >
              <span>{{ $t(spot.spot_name) }}</span>
              <el-tag size="small" style="margin-left: 8px">{{ $t(spot.category) }}</el-tag>
            </el-option>
          </el-select>
        </el-form-item>

        <!-- 已选景点拖拽排序 -->
        <el-form-item v-if="selectedSpots.length > 0" :label='$t("游览顺序")'>
          <div class="spot-sort-list">
            <div v-for="(spot, idx) in selectedSpots" :key="spot.spot_id" class="spot-sort-item">
              <span class="spot-index">{{ $t(idx + 1) }}</span>
              <span class="spot-name">{{ $t(spot.spot_name) }}</span>
              <span class="spot-category">{{ $t(spot.category) }}</span>
              <div class="spot-actions">
                <el-button
                  :disabled="idx === 0"
                  :icon="Top"
                  size="small"
                  circle
                  @click="moveSpotUp(idx)"
                />
                <el-button
                  :disabled="idx === selectedSpots.length - 1"
                  :icon="Bottom"
                  size="small"
                  circle
                  @click="moveSpotDown(idx)"
                />
              </div>
            </div>
          </div>
          <span class="sort-hint">{{ $t("点击上下箭头调整景点的游览顺序") }}</span>
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
.tour-route-container {
  padding: 16px;
}

.toolbar {
  margin-bottom: 20px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
  gap: 20px;
  align-items: start;
}
.card-row { min-width: 0; }

.route-card {
  border-radius: 12px;
  transition: transform 0.2s;

  &:hover {
    transform: translateY(-2px);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.route-name {
  font-size: 18px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
}

.card-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 18px;
  color: var(--text-secondary);
}

.meta-divider {
  color: var(--text-muted);
}

.card-desc {
  font-size: 18px;
  color: var(--text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 40px;
  margin-bottom: 14px;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  :deep(.el-button) { margin: 0; }
}

// 对话框样式
.spot-sort-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.spot-sort-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--glass-line);
  border-radius: 8px;
  background: var(--glass);
  transition: background 0.2s;

  &:hover {
    background: var(--glass);
  }
}

.spot-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: var(--text);
  font-size: 18px;
  font-weight: 600;
  flex-shrink: 0;
}

.spot-name {
  flex: 1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spot-category {
  flex-shrink: 0;
  font-size: 18px;
  color: var(--text-muted);
}

.spot-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.sort-hint {
  display: block;
  margin-top: 6px;
  font-size: 18px;
  color: var(--text-muted);
}

// 覆盖 el-dialog 样式
::v-deep(.el-dialog) {
  border-radius: 12px;
}
</style>
