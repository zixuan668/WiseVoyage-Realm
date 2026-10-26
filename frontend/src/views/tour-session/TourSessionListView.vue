<script setup lang="ts">import { t } from '@/i18n'

import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es'
import { VideoPlay, Plus, Check } from '@/icons'

import { getSessionList, createSession, startSession, endSession, analyzeSession, deleteSession, type TourSessionItem } from '@/api/tourSession'
import { getRouteList, type TourRouteItem } from '@/api/tourRoute'
import { getGuideList, type DigitalGuide } from '@/api/digitalHuman'
import { AxiosError } from 'axios'

// ======================== 列表数据 ========================

const sessionList = ref<TourSessionItem[]>([])
const loading = ref(false)

const fetchSessions = async () => {
  loading.value = true
  try {
    const { data } = await getSessionList(1, 100)
    if (data.code === 0) {
      sessionList.value = data.data.session_list
    } else {
      ElMessage.error(t("获取导览会话列表失败：") + data.message)
    }
  } catch (error: unknown) {
    if (error instanceof AxiosError) {
      ElMessage.error(t("获取导览会话列表失败：") + error.message)
    } else {
      ElMessage.error(t("未知错误"))
    }
  } finally {
    loading.value = false
  }
}

// ======================== 新建会话对话框 ========================

const dialogVisible = ref(false)
const creating = ref(false)
const routeList = ref<TourRouteItem[]>([])
const guideList = ref<DigitalGuide[]>([])
const form = ref({
  name: '',
  route_id: 0,
  guide_id: 0,
  preferences: '',
})

const openCreateDialog = async () => {
  form.value = { name: '', route_id: 0, guide_id: 0, preferences: '' }
  // 加载路线和导游列表
  try {
    const [routeRes, guideRes] = await Promise.all([
      getRouteList(1, 100),
      getGuideList(1, 100),
    ])
    if (routeRes.data.code === 0) routeList.value = routeRes.data.data.route_list
    if (guideRes.data.code === 0) guideList.value = guideRes.data.data.guide_list
    if (guideList.value.length === 0) {
      ElMessage.warning(t("请先在\"数字导游\"页面创建至少一个导游，再创建导览会话"))
    }
    if (routeList.value.length === 0) {
      ElMessage.warning(t("请先在\"游览路线\"页面创建至少一条路线，再创建导览会话"))
    }
  } catch (e) {
    console.error(e)
  }
  dialogVisible.value = true
}

const handleCreate = async () => {
  if (!form.value.name.trim()) {
    ElMessage.warning(t("请输入会话名称"))
    return
  }
  creating.value = true
  try {
    const { data } = await createSession(
      form.value.name,
      form.value.route_id,
      form.value.guide_id,
      form.value.preferences,
    )
    if (data.code === 0) {
      ElMessage.success(t("导览会话创建成功！"))
      dialogVisible.value = false
      await fetchSessions()
    } else {
      ElMessage.error(t("创建失败：") + data.message)
    }
  } catch (e: unknown) {
    if (e instanceof AxiosError) {
      ElMessage.error(t("创建失败：") + e.message)
    } else {
      ElMessage.error(t("未知错误"))
    }
  } finally {
    creating.value = false
  }
}

// ======================== 状态映射 ========================

interface StatusInfo {
  label: string
  tagType: 'info' | 'success' | 'warning' | 'danger' | ''
}

const getStatusInfo = (session: TourSessionItem): StatusInfo => {
  const raw = session.live_status
  switch (raw) {
    case 0: return { label: t("未开始"), tagType: 'info' }
    case 1: return { label: t("进行中"), tagType: 'success' }
    case 2: return { label: t("已结束"), tagType: 'warning' }
    default: return { label: t("未知"), tagType: '' }
  }
}

const isLive = (session: TourSessionItem): boolean => session.live_status === 1
const isPending = (session: TourSessionItem): boolean => session.live_status === 0

const handleStart = async (sessionId: number) => {
  try {
    const { data } = await startSession(sessionId)
    if (data.code === 0) {
      ElMessage.success(t("导览已开始"))
      fetchSessions()
    } else {
      ElMessage.error(t("开始失败：") + data.message)
    }
  } catch (e: unknown) {
    if (e instanceof AxiosError) ElMessage.error(t("开始失败：") + e.message)
  }
}

const handleEnd = async (sessionId: number) => {
  try {
    const { data } = await endSession(sessionId)
    if (data.code === 0) {
      ElMessage.success(t("导览已结束"))
      fetchSessions()
    } else {
      ElMessage.error(t("结束失败：") + data.message)
    }
  } catch (e: unknown) {
    if (e instanceof AxiosError) ElMessage.error(t("结束失败：") + e.message)
  }
}

// ======================== 格式化时间 ========================

const formatTime = (timeStr: string | undefined): string => {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ======================== 删除会话 ========================
const deleteMode = ref(false)
const selectedIds = ref<Set<number>>(new Set())
const deleting = ref(false)

const toggleDeleteMode = () => {
  deleteMode.value = !deleteMode.value
  selectedIds.value = new Set()
}

const toggleSelect = (sessionId: number) => {
  if (selectedIds.value.has(sessionId)) {
    selectedIds.value.delete(sessionId)
  } else {
    selectedIds.value.add(sessionId)
  }
  // 触发响应式更新
  selectedIds.value = new Set(selectedIds.value)
}

const confirmDelete = async () => {
  if (selectedIds.value.size === 0) {
    ElMessage.warning(t("请至少勾选一个会话"))
    return
  }
  deleting.value = true
  try {
    const ids = Array.from(selectedIds.value)
    const results = await Promise.allSettled(ids.map(id => deleteSession(id)))
    const successCount = results.filter(r => r.status === 'fulfilled' && (r.value.data as any)?.code === 0).length
    if (successCount > 0) {
      ElMessage.success(t("成功删除 {p0} 个会话", {p0: successCount}))
    }
    const failedCount = ids.length - successCount
    if (failedCount > 0) {
      ElMessage.warning(t("{p0} 个会话删除失败", {p0: failedCount}))
    }
    deleteMode.value = false
    selectedIds.value = new Set()
    await fetchSessions()
  } catch (e: unknown) {
    ElMessage.error(t("删除操作出错"))
  } finally {
    deleting.value = false
  }
}

// ======================== 进入导览 ========================

const enterTour = (sessionId: number) => {
  router.push(`/tour-session/${sessionId}/detail`)
}

// ═══════════ AI 分析 ═══════════
const router = useRouter()
const analyzingId = ref(0)
const analysisDialogVisible = ref(false)
const analysisResult = ref<any>(null)

const handleAnalyze = async (sessionId: number) => {
  analyzingId.value = sessionId
  try {
    const { data } = await analyzeSession(sessionId)
    if (data.code === 0) {
      analysisResult.value = data.data
      analysisDialogVisible.value = true
      ElMessage.success(t("AI分析完成"))
    } else {
      ElMessage.error(data.message || t("分析失败"))
    }
  } catch (e: unknown) {
    if (e instanceof AxiosError) ElMessage.error(t("分析失败：") + e.message)
    else ElMessage.error(t("未知错误"))
  } finally {
    analyzingId.value = 0
  }
}

// ======================== 生命周期 ========================

onMounted(() => {
  fetchSessions()
})
</script>

<template>
  <div class="tour-session-container">
    <div class="page-header">
      <h3 class="page-title">{{ $t("导览会话管理") }}</h3>
      <div class="header-actions">
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>{{ $t("新建会话") }}</el-button>
        <el-button :loading="loading" @click="fetchSessions">{{ $t("刷新列表") }}</el-button>
        <el-button v-if="!deleteMode" @click="toggleDeleteMode">{{ $t("删除会话") }}</el-button>
        <el-button v-else type="danger" :loading="deleting" @click="confirmDelete">{{ $t("确认删除") }}</el-button>
      </div>
    </div>

    <!-- 会话卡片网格 -->
    <div v-loading="loading" class="card-grid">
      <el-empty v-if="!loading && sessionList.length === 0" :description='$t("暂无导览会话，请先创建")' />

      <div v-for="item in sessionList" :key="item.session_id" class="card-row">
            <el-card
              class="session-card"
              :class="{ 'delete-card-mode': deleteMode, 'is-selected': selectedIds.has(item.session_id) }"
              shadow="hover"
              @click="deleteMode ? toggleSelect(item.session_id) : router.push(`/tour-session/${item.session_id}/detail`)"
            >
              <div v-if="deleteMode" class="delete-check-circle" @click.stop="toggleSelect(item.session_id)">
                <div v-if="selectedIds.has(item.session_id)" class="checked-circle">
                  <el-icon><Check /></el-icon>
                </div>
                <div v-else class="empty-circle" />
              </div>
              <div class="card-status">
                <el-tag :type="getStatusInfo(item).tagType" size="small" effect="dark">
                  {{ $t(getStatusInfo(item).label) }}
                </el-tag>
              </div>

              <p class="session-name">
                {{ $t(item.name || `会话 #${item.session_id}`) }}
              </p>

              <div class="session-info">
                <div class="info-row">
                  <span class="info-label">{{ $t("开始时间") }}</span>
                  <span class="info-value">{{ $t(formatTime(item.start_time)) }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">{{ $t("消息数") }}</span>
                  <span class="info-value">{{ (item as any).message_count || 0 }} {{ $t("条") }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">{{ $t("景点进度") }}</span>
                  <span class="info-value">{{ $t("第") }} {{ $t(((item as any).current_spot_index || 0) + 1) }} {{ $t("个") }}</span>
                </div>
              </div>

              <div class="card-actions">
                <template v-if="isPending(item)">
                  <el-button type="primary" size="default" @click="handleStart(item.session_id)">{{ $t("开始导览") }}</el-button>
                </template>
                <template v-else-if="isLive(item)">
                  <el-button type="success" size="default" :icon="VideoPlay" @click="enterTour(item.session_id)">{{ $t("进入导览") }}</el-button>
                  <el-button type="danger" size="default" @click="handleEnd(item.session_id)">{{ $t("结束") }}</el-button>
                </template>
                <template v-else>
                  <el-button type="warning" size="default" :loading="analyzingId === item.session_id" @click="handleAnalyze(item.session_id)">{{ $t("AI 分析") }}</el-button>
                </template>
              </div>
            </el-card>
      </div>
    </div>

    <!-- AI 分析结果弹窗 -->
    <el-dialog v-model="analysisDialogVisible" :title='$t("AI 导览分析报告")' width="650px" destroy-on-close>
      <div v-if="analysisResult" class="analysis-content">
        <div class="analysis-section">
          <h4>{{ $t("游客满意度") }}</h4>
          <el-tag :type="analysisResult.satisfaction === '高' ? 'success' : analysisResult.satisfaction === '中' ? 'warning' : 'danger'" size="large">
            {{ $t(analysisResult.satisfaction || '-') }}
          </el-tag>
          <p class="analysis-desc">{{ $t(analysisResult.satisfaction_reason || '-') }}</p>
        </div>
        <div class="analysis-section">
          <h4>{{ $t("游客情感趋势") }}</h4>
          <p>{{ $t(analysisResult.visitor_emotion_trend || '-') }}</p>
        </div>
        <div class="analysis-section">
          <h4>{{ $t("热门话题") }}</h4>
          <div class="tag-group">
            <el-tag v-for="(t, i) in (analysisResult.hot_topics || [])" :key="i" type="success" effect="plain">{{ $t(t) }}</el-tag>
            <span v-if="!analysisResult.hot_topics?.length">-</span>
          </div>
        </div>
        <div class="analysis-section">
          <h4>{{ $t("游客常见提问") }}</h4>
          <ul class="question-list">
            <li v-for="(q, i) in (analysisResult.frequent_questions || [])" :key="i">{{ $t(q) }}</li>
            <li v-if="!analysisResult.frequent_questions?.length">-</li>
          </ul>
        </div>
        <div class="analysis-section">
          <h4>{{ $t("改进建议") }}</h4>
          <p class="analysis-desc">{{ $t(analysisResult.service_suggestions || '-') }}</p>
        </div>
        <div class="analysis-section summary-box">
          <h4>{{ $t("总结") }}</h4>
          <p>{{ $t(analysisResult.summary || analysisResult.raw || '-') }}</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="analysisDialogVisible = false">{{ $t("关闭") }}</el-button>
      </template>
    </el-dialog>

    <!-- 新建会话对话框 -->
    <el-dialog v-model="dialogVisible" :title='$t("新建导览会话")' width="500px" destroy-on-close>
      <el-form :model="form" label-width="100px">
        <el-form-item :label='$t("会话名称")' required>
          <el-input v-model="form.name" :placeholder='$t("如：3月15日导览")' maxlength="50" />
        </el-form-item>
        <el-form-item :label='$t("游览路线")'>
          <el-select v-model="form.route_id" :placeholder='$t("选择路线")' style="width:100%">
            <el-option v-for="r in routeList" :key="r.route_id" :label="$t(r.name)" :value="r.route_id" />
          </el-select>
        </el-form-item>
        <el-form-item :label='$t("数字导游")'>
          <el-select v-model="form.guide_id" :placeholder='$t("选择导游")' style="width:100%">
            <el-option v-for="g in guideList" :key="g.guide_id" :label="$t(g.name)" :value="g.guide_id" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t("取消") }}</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">{{ $t("创建") }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.tour-session-container {
  padding: 16px;
}

.page-header {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--glass);
  padding: 10px 0;
  border-bottom: 1px solid var(--glass-line);
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  :deep(.el-button) { margin: 0; }
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
  gap: 20px;
  align-items: start;
}
.card-row { min-width: 0; }

.session-card {
  border-radius: 12px;
  transition: transform 0.2s;

  &:hover {
    transform: translateY(-2px);
  }
}

.card-status {
  margin-bottom: 10px;
}

.session-name {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 14px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--glass);
  border-radius: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
}

.info-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.info-value {
  color: var(--text);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-left: 12px;
  text-align: right;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  align-items: center;
  :deep(.el-button) { margin: 0; }
}

.not-live-hint {
  font-size: 18px;
  color: var(--text-muted);
}
.analysis-content { display: flex; flex-direction: column; gap: 16px; }
.analysis-section h4 { margin: 0 0 6px; font-size: 18px; color: var(--text); }
.analysis-desc { margin: 6px 0 0; font-size: 18px; color: var(--text-secondary); line-height: 1.6; }
.tag-group { display: flex; flex-wrap: wrap; gap: 6px; }
.question-list { margin: 4px 0 0; padding-left: 18px; font-size: 18px; color: var(--text-secondary); line-height: 1.8; }
.summary-box { padding: 12px; background: var(--glass); border-radius: 8px; border: 1px solid var(--glass-line); }
.summary-box h4 { color: var(--champagne-text); }

/* ======================== 删除模式 ======================== */

.delete-card-mode {
  cursor: pointer;
  position: relative;

  &.is-selected {
    border: 2px solid var(--glass-line);
    box-shadow: var(--glass-shadow);
  }
}

.delete-check-circle {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 5;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;

  .empty-circle {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: 2px solid var(--glass-line);
    background: var(--glass);
    transition: border-color 0.2s;

    &:hover {
      border-color: var(--glass-line);
    }
  }

  .checked-circle {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--glass);
    display: flex;
    align-items: center;
    justify-content: center;

    .el-icon {
      font-size: 18px;
      color: var(--text);
      font-weight: 700;
    }
  }
}
</style>
