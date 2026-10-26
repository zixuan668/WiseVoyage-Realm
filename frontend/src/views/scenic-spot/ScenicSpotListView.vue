<script setup lang="ts">import { t, formatTableCell } from '@/i18n'

import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Delete, Edit, Search } from '@/icons'
import { ElMessage, ElMessageBox } from 'element-plus'

import ScenicInstructionDialog from '@/components/ScenicInstructionDialog.vue'

import {
  getSpotList,
  deleteSpot,
  type ScenicSpotListData,
} from '@/api/scenicSpot'
import { AxiosError } from 'axios'
import { adminAssetUrl } from '@/utils/adminAssetUrl'

const router = useRouter()

// 信息弹窗显示标识
const ShowItemInfo = ref()

// 加载框
const tableLoading = ref(true)

// 查询 - 条件
const queryCondition = ref({
  currentPage: 1,
  pageSize: 10,
  spotName: '',
  category: '',
})

// 查询 - 结果
const queriedResult = ref<ScenicSpotListData>({} as ScenicSpotListData)

// 分类选项
const categoryOptions = [
  { label: '全部', value: '' },
  { label: '自然景观', value: 'natural' },
  { label: '历史古迹', value: 'historical' },
  { label: '文化体验', value: 'cultural' },
  { label: '现代建筑', value: 'modern' },
  { label: '综合景区', value: 'comprehensive' },
]

const categoryLabelMap: Record<string, string> = {
  'natural': '自然景观',
  'historical': '历史古迹',
  'cultural': '文化体验',
  'modern': '现代建筑',
  'comprehensive': '综合景区',
}

const categoryTagTypeMap: Record<string, string> = {
  'natural': 'success',
  'historical': 'warning',
  'cultural': 'info',
  'modern': '',
  'comprehensive': 'danger',
}

// 查询 - 方法
const fetchSpotList = async () => {
  tableLoading.value = true

  try {
    const { data } = await getSpotList(
      queryCondition.value.currentPage,
      queryCondition.value.pageSize,
      queryCondition.value.spotName || undefined,
      queryCondition.value.category || undefined,
    )
    tableLoading.value = false

    if (data.code === 0) {
      queriedResult.value = data.data
    } else {
      ElMessage.error(t("景点接口错误"))
      throw new Error(t("景点接口错误"))
    }
  } catch (error: unknown) {
    tableLoading.value = false
    if (error instanceof AxiosError) {
      ElMessage.error(t("景点接口失败: ") + error.message)
    } else {
      ElMessage.error(t("未知错误：") + error)
    }
  }
}

onMounted(() => {
  fetchSpotList()
})

const handleSearch = () => {
  queryCondition.value.currentPage = 1
  fetchSpotList()
}

const getCategoryLabel = (category: string) => {
  return categoryLabelMap[category] || category
}

const getCategoryTagType = (category: string): '' | 'success' | 'warning' | 'info' | 'danger' => {
  return (categoryTagTypeMap[category] as '' | 'success' | 'warning' | 'info' | 'danger') || ''
}

const isDeleting = ref(false)
const handleDelete = async (id: number, spotName: string) => {
  ElMessageBox.confirm(t("确定要删除景点 \"") + spotName + t("\" 吗？"), t("警告"), {
    confirmButtonText: t("确定"),
    cancelButtonText: t("取消"),
    type: 'warning',
    showClose: false,
  })
    .then(async () => {
      ElMessage.success(t("正在删除 ") + spotName + t("，请稍候"))
      isDeleting.value = true
      const { data } = await deleteSpot(id)
      if (data.code === 0) {
        ElMessage.success(t("删除成功"))
        fetchSpotList()
      } else {
        ElMessage.error(t("删除失败"))
      }
      isDeleting.value = false
    })
    .catch(() => {
      // 取消操作
    })
}
</script>

<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <!-- 头部 -->
        <div class="card-header">
          <div>
            <el-form :inline="true">
              <el-form-item :label='$t("搜索")'>
                <el-input
                  style="width: 240px"
                  v-model="queryCondition.spotName"
                  :placeholder='$t("景点名称")'
                  clearable
                  @keyup.enter="handleSearch"
                />
              </el-form-item>
              <el-form-item :label='$t("分类")'>
                <el-select
                  v-model="queryCondition.category"
                  :placeholder='$t("景点分类")'
                  clearable
                  style="width: 160px"
                >
                  <el-option
                    v-for="item in categoryOptions"
                    :key="item.value"
                    :label="$t(item.label)"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleSearch">
                  <el-icon style="margin-right: 5px">
                    <Search />
                  </el-icon>{{ $t("查询") }}</el-button>
              </el-form-item>
            </el-form>
          </div>
          <div>
            <!-- 添加景点 -->
            <el-button type="primary" @click="router.push({ name: 'ScenicSpotCreate' })">
              <el-icon style="margin-right: 5px">
                <Plus />
              </el-icon>{{ $t("添加景点") }}</el-button>
          </div>
        </div>
      </template>

      <!-- 中部表格信息 -->
      <el-table :data="queriedResult.spot_list" max-height="1000" v-loading="tableLoading">
        <el-table-column prop="spot_number" :label='$t("景点编号")' align="center" width="110px">
          <template #default="{ row }">{{ row.spot_number ?? '—' }}</template>
        </el-table-column>

        <el-table-column prop="image_path" :label='$t("图片")' align="center" width="100px">
          <template #default="scope">
            <div style="display: flex; align-items: center; justify-content: center">
              <el-image
                v-if="scope.row.image_path"
                :src="adminAssetUrl(scope.row.image_path)"
                :preview-src-list="[adminAssetUrl(scope.row.image_path)]"
                style="width: 60px; height: 60px"
                fit="cover"
              />
              <span v-else class="spot-no-image">{{ $t("暂无图片") }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column :formatter="formatTableCell" prop="spot_name" :label='$t("景点名称")' align="center" min-width="190px" show-overflow-tooltip />

        <el-table-column prop="category" :label='$t("分类")' align="center" width="180px">
          <template #default="scope">
            <el-tag :type="getCategoryTagType(scope.row.category)" size="small">
              {{ $t(getCategoryLabel(scope.row.category)) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="tags" :label='$t("标签")' align="center" min-width="200px">
          <template #default="scope">
            <div style="display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; max-height: 96px; overflow: auto">
              <el-tag
                v-for="(tag, index) in (scope.row.tags ? scope.row.tags.split(';').filter(Boolean) : [])"
                :key="index"
                size="small"
                type="info"
                :title="$t(tag)"
                style="max-width: 100%; overflow: hidden; text-overflow: ellipsis"
              >
                {{ $t(tag) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column :formatter="formatTableCell" prop="location" :label='$t("所在位置")' align="center" min-width="180px" show-overflow-tooltip />
        <el-table-column :formatter="formatTableCell" prop="best_season" :label='$t("最佳季节")' align="center" width="160px" show-overflow-tooltip />
        <el-table-column :formatter="formatTableCell" prop="upload_date" :label='$t("上传时间")' align="center" width="180px" />

        <el-table-column :label='$t("操作")' v-slot="{ row }" align="center" width="310px">
          <div class="control-item">
            <el-button
              :type="row.instruction ? 'success' : 'warning'"
              :disabled="!row.instruction"
              size="small"
              @click="
                ShowItemInfo.open(row.spot_id, row.spot_name)
              "
            >{{ $t("游览说明") }}</el-button>

            <!-- 编辑按钮 -->
            <el-button
              type="primary"
              :icon="Edit"
              size="small"
              @click="router.push({ name: 'ScenicSpotEdit', params: { spotId: row.spot_id } })"
            />

            <!-- 删除按钮 -->
            <el-button
              type="danger"
              @click="handleDelete(row.spot_id, row.spot_name)"
              :icon="Delete"
              :disabled="isDeleting"
              size="small"
            />
          </div>
        </el-table-column>
      </el-table>

      <!-- 信息弹窗 -->
      <ScenicInstructionDialog ref="ShowItemInfo" />

      <!-- 分页栏 -->
      <template #footer>
        <el-pagination
          v-model:current-page="queryCondition.currentPage"
          v-model:page-size="queryCondition.pageSize"
          :page-sizes="[5, 10, 15, 20]"
          :background="true"
          layout="total, sizes, prev, pager, next, jumper"
          :total="queriedResult.totalSize || 0"
          @size-change="handleSearch"
          @current-change="fetchSpotList"
        />
      </template>
    </el-card>
  </div>
</template>

<style lang="scss" scoped>
.spot-no-image {
  display: inline-block;
  width: 60px;
  height: 60px;
  line-height: 60px;
  font-size: 18px;
  color: #9ca3af;
  background: #f3f4f6;
  border-radius: 6px;
}

.el-card {
  border-radius: 12px;
}

.box-card {
  width: auto;
}

// 查询栏
.card-header {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: space-between;
  align-items: center;

  .el-form-item {
    margin: 0;
  }
  > div { min-width: 0; max-width: 100%; }
  .el-form { display: flex; flex-wrap: wrap; gap: 16px; }
  :deep(.el-input), :deep(.el-select) { max-width: 100%; }
}

// 分页框
.el-pagination {
  margin-top: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
}

// 操作栏
.control-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

// 去掉表格下边框线
:deep(.el-table__inner-wrapper::before) {
  height: 0;
}
</style>
