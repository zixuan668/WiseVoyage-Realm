<template>
  <div class="detail-container">
    <!-- 顶部栏 -->
    <div class="detail-header">
      <el-button :icon="ArrowLeft" @click="$router.back()">{{ $t("返回") }}</el-button>
      <h3>{{ $t(detail?.session?.name || '会话详情') }}</h3>
      <el-tag :type="statusType">{{ $t(statusText) }}</el-tag>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card"><span class="stat-num">{{ $t(detail?.stats?.total_messages || 0) }}</span><span class="stat-label">{{ $t("总消息数") }}</span></div>
      <div class="stat-card"><span class="stat-num">{{ $t(detail?.stats?.user_questions || 0) }}</span><span class="stat-label">{{ $t("游客提问") }}</span></div>
      <div class="stat-card"><span class="stat-num">{{ $t(detail?.stats?.guide_responses || 0) }}</span><span class="stat-label">{{ $t("导游回复") }}</span></div>
      <div class="stat-card"><span class="stat-num">{{ $t(currentSpotIndex) }}</span><span class="stat-label">{{ $t("浏览景点数") }}</span></div>
    </div>

    <!-- Tab 内容区 -->
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab 1: 对话记录 -->
      <el-tab-pane :label='$t("对话记录")' name="chat">
        <div class="chat-log">
          <div v-for="(msg, i) in detail?.conversation" :key="i" class="chat-item" :class="msg.role === 'user' ? 'user' : 'guide'">
            <div class="chat-role">{{ $t(msg.role === 'user' ? ' 游客' : ' AI导游') }}</div>
            <div class="chat-bubble">{{ msg.message }}</div>
            <div class="chat-time">{{ $t(msg.send_time) }}</div>
          </div>
          <el-empty v-if="!detail?.conversation?.length" :description='$t("暂无对话记录")' />
        </div>
      </el-tab-pane>

      <!-- Tab 2: AI 分析报告（增强版） -->
      <el-tab-pane :label='$t("AI 分析报告")' name="analysis">
        <div class="analysis-panel">
          <!-- 分析操作按钮 -->
          <div class="analysis-actions">
            <el-button type="primary" :loading="analyzing" @click="runQuestionAnalysis">{{ $t("逐题深度分析") }}</el-button>
            <el-button type="success" :loading="reportGenerating" @click="runReportGeneration">{{ $t("生成综合报告") }}</el-button>
            <el-button v-if="questionAnalysis || sessionReport" size="small" @click="clearAnalysis">{{ $t("清空结果") }}</el-button>
          </div>

          <!-- 逐题分析结果 -->
          <div v-if="questionAnalysis" class="analysis-result">
            <!-- 汇总统计卡片 -->
            <div class="summary-stats-row" v-if="questionAnalysis.summary_stats">
              <div class="mini-stat">
                <span class="mini-num">{{ $t(questionAnalysis.total_questions) }}</span>
                <span class="mini-label">{{ $t("分析题目数") }}</span>
              </div>
              <div class="mini-stat">
                <span class="mini-num">{{ $t(questionAnalysis.summary_stats.avg_answer_score?.toFixed(1) || '-') }}</span>
                <span class="mini-label">{{ $t("平均回答评分") }}</span>
              </div>
              <div class="mini-stat">
                <span class="mini-num">{{ $t(questionAnalysis.summary_stats.knowledge_gaps?.length || 0) }}</span>
                <span class="mini-label">{{ $t("知识盲区数") }}</span>
              </div>
            </div>

            <!-- 问题类型分布饼图 -->
            <div class="chart-row" v-if="typeDistributionData.length">
              <div class="chart-half">
                <PieChartComponent
                  :title='$t("问题类型分布")'
                  :data="typeDistributionData"
                  :colors="pieColors"
                  height="300px"
                />
              </div>
              <div class="chart-half">
                <div class="overall-assessment" v-if="questionAnalysis.summary_stats?.overall_assessment">
                  <h4>{{ $t("总体评价") }}</h4>
                  <p>{{ $t(questionAnalysis.summary_stats.overall_assessment) }}</p>
                </div>
                <div class="knowledge-gaps-card" v-if="questionAnalysis.summary_stats?.knowledge_gaps?.length">
                  <h4>{{ $t("知识盲区") }}</h4>
                  <div class="gap-tags">
                    <el-tag v-for="(gap, i) in questionAnalysis.summary_stats.knowledge_gaps" :key="i" type="danger" effect="plain" size="small">{{ $t(gap) }}</el-tag>
                  </div>
                </div>
              </div>
            </div>

            <!-- 逐题分析表格 -->
            <div class="question-table-section" v-if="questionAnalysis.per_question?.length">
              <h4>{{ $t("逐题分析详情") }}</h4>
              <el-table :data="questionAnalysis.per_question" stripe border style="width: 100%" max-height="500" size="small">
                <el-table-column type="index" label="#" width="45" />
                <el-table-column :formatter="formatTableCell" prop="question" :label='$t("游客提问")' min-width="160" show-overflow-tooltip />
                <el-table-column prop="question_type" :label='$t("问题类型")' width="100">
                  <template #default="{ row }">
                    <el-tag size="small" effect="plain" :type="questionTypeTag(row.question_type)">{{ $t(row.question_type) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="question_quality" :label='$t("质量")' width="65">
                  <template #default="{ row }">
                    <span :style="{ color: qualityColor(row.question_quality), fontWeight: 600 }">{{ $t(row.question_quality) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="answer_quality_score" :label='$t("评分")' width="60" sortable>
                  <template #default="{ row }">
                    <el-rate :model-value="row.answer_quality_score" disabled show-score :max="5" size="small" />
                  </template>
                </el-table-column>
                <el-table-column prop="knowledge_covered" :label='$t("知识覆盖")' width="95">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.knowledge_covered === '充分覆盖' ? 'success' : row.knowledge_covered === '部分覆盖' ? 'warning' : 'danger'">
                      {{ $t(row.knowledge_covered) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column :formatter="formatTableCell" prop="improvement_note" :label='$t("改进建议")' min-width="160" show-overflow-tooltip />
              </el-table>
            </div>
          </div>

          <!-- 综合报告结果 -->
          <div v-if="sessionReport" class="report-result">
            <div class="report-header">
              <el-tag size="large" :type="reportScoreType">{{ $t(sessionReport.report?.quality_level || '未知') }}</el-tag>
              <span class="report-score">{{ $t("综合评分:") }} {{ $t(sessionReport.report?.session_quality_score ?? '-') }} / 100</span>
              <el-button size="small" type="primary" plain @click="copyReport">{{ $t("复制报告") }}</el-button>
            </div>

            <!-- 游客画像 -->
            <div class="report-section" v-if="sessionReport.report?.visitor_profile">
              <h4>{{ $t("游客画像") }}</h4>
              <div class="visitor-profile-cards">
                <div class="profile-card">
                  <span class="profile-label">{{ $t("兴趣标签") }}</span>
                  <div class="tag-group">
                    <el-tag v-for="tag in (sessionReport.report.visitor_profile?.interests || [])" :key="tag" type="success" effect="plain" size="small">{{ $t(tag) }}</el-tag>
                  </div>
                </div>
                <div class="profile-card">
                  <span class="profile-label">{{ $t("参与度") }}</span>
                  <el-tag :type="engagementType(sessionReport.report.visitor_profile.engagement_level)" size="small">
                    {{ $t(sessionReport.report.visitor_profile.engagement_level) }}
                  </el-tag>
                </div>
                <div class="profile-card">
                  <span class="profile-label">{{ $t("满意度趋势") }}</span>
                  <el-tag :type="trendType(sessionReport.report.visitor_profile.satisfaction_trend)" size="small">
                    {{ $t(sessionReport.report.visitor_profile.satisfaction_trend) }}
                  </el-tag>
                </div>
              </div>
            </div>

            <!-- 服务亮点与知识盲区 -->
            <el-row :gutter="16" v-if="sessionReport.report">
              <el-col :span="12">
                <div class="report-section">
                  <h4>{{ $t("服务亮点") }}</h4>
                  <ul><li v-for="(h, i) in (sessionReport.report.service_highlights || [])" :key="i">{{ $t(h) }}</li></ul>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="report-section">
                  <h4>{{ $t("知识盲区") }}</h4>
                  <ul><li v-for="(g, i) in (sessionReport.report.knowledge_gaps || [])" :key="i">{{ $t(g) }}</li></ul>
                </div>
              </el-col>
            </el-row>

            <!-- 改进建议 -->
            <div class="report-section" v-if="sessionReport.report.improvement_suggestions?.length">
              <h4>{{ $t("改进建议") }}</h4>
              <div v-for="(sug, i) in sessionReport.report.improvement_suggestions" :key="i" class="suggestion-item">
                <el-tag :type="sug.priority === '高' ? 'danger' : sug.priority === '中' ? 'warning' : 'info'" size="small" effect="dark">
                  {{ $t(sug.priority) }} {{ $t("优先级") }}</el-tag>
                <span class="sug-area">【{{ $t(sug.area) }}】</span>
                <span class="sug-text">{{ $t(sug.suggestion) }}</span>
              </div>
            </div>

            <!-- 总结 -->
            <div class="report-section summary-box" v-if="sessionReport.report?.executive_summary">
              <h4>{{ $t("总结") }}</h4>
              <p>{{ $t(sessionReport.report.executive_summary) }}</p>
            </div>
          </div>

          <el-empty v-if="!questionAnalysis && !sessionReport" :description='$t("点击上方按钮进行AI分析")' />
        </div>
      </el-tab-pane>

      <!-- Tab 3: 问题挖掘 -->
      <el-tab-pane :label='$t("问题挖掘")' name="issues">
        <div class="analysis-panel">
          <el-button type="warning" :loading="analyzingIssues" @click="runIssueAnalysis" style="margin-bottom:16px">
            {{ $t(issueResult ? '重新分析' : 'AI问题挖掘') }}
          </el-button>
          <div v-if="issueResult" class="analysis-result">
            <div class="issue-analysis-meta">
              <span class="analysis-source"><i></i>{{ $t(issueResult.analysis_source || 'AI语义分析') }}</span>
              <span>{{ $t("已分析") }} {{ $t(issueResult.analyzed_question_count ?? detail?.stats.user_questions ?? 0) }} {{ $t("条游客提问") }}</span>
            </div>
            <!-- 满意度 -->
            <div class="analysis-section" v-if="issueResult.satisfaction">
              <h4>{{ $t("游客满意度") }}</h4>
              <p><el-tag :type="issueResult.satisfaction === '高' ? 'success' : issueResult.satisfaction === '低' ? 'danger' : 'warning'" size="large">{{ $t(issueResult.satisfaction) }}</el-tag> — {{ $t(issueResult.satisfaction_reason) }}</p>
            </div>
            <!-- 知识库盲区 -->
            <div class="analysis-section" v-if="issueResult.knowledge_gaps?.length">
              <h4>{{ $t("知识库盲区") }}</h4>
              <ul><li v-for="(g,i) in issueResult.knowledge_gaps" :key="i">{{ $t(g) }}</li></ul>
            </div>
            <!-- 游客常见困惑 -->
            <div class="analysis-section" v-if="issueResult.common_confusions?.length">
              <h4>{{ $t("游客常见困惑") }}</h4>
              <ul><li v-for="(c,i) in issueResult.common_confusions" :key="i">{{ $t(c) }}</li></ul>
            </div>
            <!-- 服务缺口 -->
            <div class="analysis-section" v-if="issueResult.service_gaps?.length">
              <h4>{{ $t("服务缺口") }}</h4>
              <ul><li v-for="(g,i) in issueResult.service_gaps" :key="i">{{ $t(g) }}</li></ul>
            </div>
            <!-- 改进措施 -->
            <div class="analysis-section" v-if="issueResult.improvement_actions?.length">
              <h4>{{ $t("改进措施") }}</h4>
              <ol><li v-for="(a,i) in issueResult.improvement_actions" :key="i">{{ $t(a) }}</li></ol>
            </div>
            <!-- 热门话题 -->
            <div class="analysis-section" v-if="issueResult.hot_topics?.length">
              <h4>{{ $t("热门话题") }}</h4>
              <div class="gap-tags"><el-tag v-for="(t,i) in issueResult.hot_topics" :key="i" type="success" effect="plain" size="small">{{ $t(t) }}</el-tag></div>
            </div>
            <!-- 总结 -->
            <div class="analysis-section summary-box" v-if="issueResult.summary">
              <h4>{{ $t("总结") }}</h4>
              <p>{{ $t(issueResult.summary) }}</p>
            </div>
          </div>
          <el-empty v-else :description='$t("点击按钮让AI挖掘潜在问题")' />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">import { t, formatTableCell } from '@/i18n'

import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@/icons'
import { getSessionDetail, analyzeSession, analyzeQuestions, generateSessionReport, type SessionDetail, type QuestionAnalysisResult, type SessionReportResult, type IssueAnalysisResult } from '@/api/tourSession'
import { AxiosError } from 'axios'
import PieChartComponent from '@/components/PieChartComponent.vue'

const route = useRoute()
const sessionId = Number(route.params.sessionId)
const activeTab = ref('chat')
const detail = ref<SessionDetail | null>(null)

// 分析状态
const analyzing = ref(false)
const analyzingIssues = ref(false)
const reportGenerating = ref(false)

const questionAnalysis = ref<QuestionAnalysisResult | null>(null)
const sessionReport = ref<SessionReportResult | null>(null)
const issueResult = ref<IssueAnalysisResult | null>(null)

const statusText = computed(() => {
  const s = detail.value?.session?.live_status
  return s === 1 ? t("进行中") : s === 2 ? t("已结束") : t("未开始")
})
const statusType = computed(() => {
  const s = detail.value?.session?.live_status
  return s === 1 ? 'success' : s === 2 ? 'warning' : 'info'
})
const currentSpotIndex = computed(() => (detail.value?.session?.current_spot_index || 0) + 1)

// 问题类型分布饼图数据
const typeDistributionData = computed(() => {
  const dist = questionAnalysis.value?.summary_stats?.question_type_distribution
  if (!dist) return []
  return Object.entries(dist).map(([name, value]) => ({ name, value: value as number }))
})

const pieColors = ['#4f46e5', '#818cf8', '#6366f1', '#10b981', '#ec4899', '#f59e0b', '#d15d1a', '#64748b']

// 报告评分类型
const reportScoreType = computed(() => {
  const level = sessionReport.value?.report?.quality_level
  if (level === '优秀' || level === '良好') return 'success'
  if (level === '一般') return 'warning'
  return 'danger'
})

// 辅助工具函数
function questionTypeTag(type: string): string {
  const map: Record<string, string> = { '历史文化': 'primary', '自然风景': 'success', '路线指引': 'warning', '门票价格': 'danger', '拍照打卡': 'info', '餐饮住宿': '', '其他': 'info' }
  return map[type] || ''
}

function qualityColor(q: string): string {
  if (q === '深度') return 'var(--success)'
  if (q === '中等') return 'var(--champagne-text)'
  return 'var(--text-muted)'
}

function engagementType(level: string): string {
  if (level === '高') return 'success'
  if (level === '中') return 'warning'
  return 'info'
}

function trendType(trend: string): string {
  if (trend === '上升') return 'success'
  if (trend === '平稳') return 'warning'
  return 'danger'
}

// 数据加载
onMounted(async () => {
  try {
    const { data } = await getSessionDetail(sessionId)
    if (data.code === 0) detail.value = data.data
  } catch (e: any) { ElMessage.error(t("加载失败")) }
})

// 逐题深度分析
async function runQuestionAnalysis() {
  analyzing.value = true
  try {
    const { data } = await analyzeQuestions(sessionId)
    if (data.code === 0) {
      questionAnalysis.value = data.data
      activeTab.value = 'analysis'
      ElMessage.success(t("逐题分析完成！"))
    } else {
      ElMessage.error(data.message || t("分析失败"))
    }
  } catch (e: any) {
    const message = e instanceof AxiosError
      ? (e.response?.data?.message || e.message)
      : t("未知错误")
    ElMessage.error(t("逐题分析失败：{p0}", {p0: message}))
  }
  finally { analyzing.value = false }
}

// 生成综合报告
async function runReportGeneration() {
  reportGenerating.value = true
  try {
    const { data } = await generateSessionReport(sessionId)
    if (data.code === 0) {
      sessionReport.value = data.data
      activeTab.value = 'analysis'
      ElMessage.success(t("报告生成完成！"))
    } else {
      ElMessage.error(data.message || t("报告生成失败"))
    }
  } catch (e: any) {
    const message = e instanceof AxiosError
      ? (e.response?.data?.message || e.message)
      : t("未知错误")
    ElMessage.error(t("报告生成失败：{p0}", {p0: message}))
  }
  finally { reportGenerating.value = false }
}

// 清空分析结果
function clearAnalysis() {
  questionAnalysis.value = null
  sessionReport.value = null
}

// 复制报告
function copyReport() {
  const report = sessionReport.value?.report
  if (!report) return
  const text = t("【{p0}】\n综合评分: {p1}/100 ({p2})\n\n 总结: {p3}\n\n 游客画像:\n- 兴趣: {p4}\n- 参与度: {p5}\n\n 服务亮点: {p6}\n\n 知识盲区: {p7}\n\n 改进建议: {p8}", {p0: report.title || '会话分析报告', p1: report.session_quality_score, p2: report.quality_level, p3: report.executive_summary, p4: report.visitor_profile?.interests?.join('、') || '-', p5: report.visitor_profile?.engagement_level || '-', p6: report.service_highlights?.join('；') || '-', p7: report.knowledge_gaps?.join('；') || '-', p8: report.improvement_suggestions?.map(s => `【${s.priority}】${s.area}: ${s.suggestion}`).join('\n') || '-'})
  navigator.clipboard.writeText(text).then(() => ElMessage.success(t("报告已复制")))
}

// 问题挖掘（使用原始分析接口兼容旧逻辑）
async function runIssueAnalysis() {
  analyzingIssues.value = true
  try {
    const { data } = await analyzeSession(sessionId)
    if (data.code === 0) {
      issueResult.value = data.data
      activeTab.value = 'issues'
      ElMessage.success(t("分析完成"))
    } else {
      ElMessage.error(data.message || t("分析失败"))
    }
  } catch (e: any) {
    const message = e instanceof AxiosError
      ? (e.response?.data?.message || e.message)
      : t("未知错误")
    ElMessage.error(t("问题挖掘失败：{p0}", {p0: message}))
  }
  finally { analyzingIssues.value = false }
}
</script>

<style scoped>
.detail-container { padding: 16px; max-width: 1400px; margin: 0 auto; }
.detail-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.detail-header h3 { margin: 0; font-size: 20px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.stat-card { padding: 16px; background: var(--glass); border-radius: 10px; border: 1px solid var(--glass-line); text-align: center; }
.stat-num { display: block; font-size: 28px; font-weight: 800; color: var(--champagne-text); }
.stat-label { font-size: 18px; color: var(--text-secondary); }

/* 对话记录 */
.chat-log { max-height: 60vh; overflow-y: auto; padding: 8px; }
.chat-item { margin-bottom: 16px; }
.chat-item.user .chat-bubble { background: var(--glass); border-color: var(--glass-line); }
.chat-item.guide .chat-bubble { background: var(--glass); border-color: var(--glass-line); }
.chat-role { font-size: 18px; color: var(--text-secondary); margin-bottom: 4px; }
.chat-bubble { padding: 10px 14px; border-radius: 10px; border: 1px solid; font-size: 18px; line-height: 1.6; }
.chat-time { font-size: 18px; color: var(--text-muted); text-align: right; margin-top: 2px; }

/* 分析面板 */
.analysis-panel { min-height: 300px; }
.analysis-actions { display: flex; gap: 12px; align-items: center; margin-bottom: 20px; flex-wrap: wrap; }
.analysis-result { display: flex; flex-direction: column; gap: 16px; }
.issue-analysis-meta { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 13px; border: 1px solid var(--glass-line); border-radius: 8px; background: var(--glass); color: var(--text-muted); font-size: 18px; }
.analysis-source { display: inline-flex; align-items: center; color: var(--champagne-text); font-weight: 650; }
.analysis-source i { width: 7px; height: 7px; margin-right: 7px; border-radius: 50%; background: var(--glass); box-shadow: var(--glass-shadow); }

/* 汇总统计 */
.summary-stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.mini-stat { padding: 14px; background: var(--glass); border-radius: 8px; border: 1px solid var(--glass-line); text-align: center; }
.mini-num { display: block; font-size: 24px; font-weight: 700; color: var(--champagne-text); }
.mini-label { font-size: 18px; color: var(--text-secondary); }

/* 图表行 */
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 8px 0; }
.chart-half { background: var(--glass); border-radius: 8px; border: 1px solid var(--glass-line); padding: 12px; }

.overall-assessment h4, .knowledge-gaps-card h4 { margin: 0 0 8px; font-size: 18px; color: var(--text); }
.overall-assessment p { font-size: 18px; color: var(--text-secondary); line-height: 1.6; }
.gap-tags { display: flex; flex-wrap: wrap; gap: 6px; }

.question-table-section { margin-top: 8px; }
.question-table-section h4 { margin: 0 0 8px; font-size: 18px; }

/* 报告结果 */
.report-result { display: flex; flex-direction: column; gap: 16px; }
.report-header { display: flex; align-items: center; gap: 16px; padding: 12px; background: var(--glass); border-radius: 8px; border: 1px solid var(--glass-line); }
.report-score { font-size: 18px; font-weight: 700; color: var(--champagne-text); }

.report-section { padding: 14px; background: var(--glass); border-radius: 8px; border: 1px solid var(--glass-line); }
.report-section h4 { margin: 0 0 8px; font-size: 18px; color: var(--text); }
.report-section p, .report-section li { font-size: 18px; color: var(--text-secondary); line-height: 1.7; margin: 2px 0; }
.report-section ul { padding-left: 18px; }

.visitor-profile-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.profile-card { padding: 10px; background: var(--glass); border-radius: 6px; border: 1px solid var(--glass-line); }
.profile-label { display: block; font-size: 18px; color: var(--text-muted); margin-bottom: 6px; }

.tag-group { display: flex; flex-wrap: wrap; gap: 4px; }

.suggestion-item { display: flex; align-items: center; gap: 8px; padding: 8px 0; }
.suggestion-item + .suggestion-item { border-top: 1px dashed var(--glass-line); }
.sug-area { font-size: 18px; color: var(--text-secondary); white-space: nowrap; }
.sug-text { font-size: 18px; color: var(--text); line-height: 1.5; }

.summary-box { background: var(--glass); border-color: var(--glass-line); }
.summary-box h4 { color: var(--champagne-text); }

/* 旧样式保持兼容 */
.analysis-section { padding: 12px; background: var(--glass); border-radius: 8px; border: 1px solid var(--glass-line); }
.analysis-section h4 { margin: 0 0 6px; font-size: 18px; color: var(--text); }
.analysis-section p, .analysis-section li { font-size: 18px; color: var(--text-secondary); line-height: 1.6; margin: 2px 0; }
.analysis-section ol, .analysis-section ul { padding-left: 20px; }
</style>
