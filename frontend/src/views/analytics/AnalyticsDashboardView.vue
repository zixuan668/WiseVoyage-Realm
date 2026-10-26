<template>
  <div class="dashboard-container" v-loading="loading">
    <!-- ========== 顶部统计卡片 ========== -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="4" v-for="card in statCards" :key="card.title">
        <div class="stat-card" :style="{ backgroundColor: card.bgColor }">
          <div class="stat-card-body">

            <div>
              <div class="stat-value" :style="{ color: card.color }">{{ $t(card.value) }}</div>
              <div class="stat-title">{{ $t(card.title) }}</div>
            </div>
          </div>

        </div>
      </el-col>
    </el-row>

    <!-- ========== 图表第一行: 服务趋势 + 热门景点 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="14">
        <el-card shadow="never" class="chart-card">
          <template #header><span class="card-title">{{ $t("近30天服务趋势") }}</span></template>
          <div ref="trendChartRef" class="dashboard-chart dashboard-trend-chart" />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" class="chart-card">
          <template #header><span class="card-title">{{ $t("热门景点TOP10") }}</span></template>
          <div ref="spotChartRef" class="dashboard-chart dashboard-ranking-chart" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ========== 图表第二行: 问题类型 + 活跃热力图 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="10">
        <el-card shadow="never" class="chart-card">
          <template #header><span class="card-title">{{ $t("问题类型分布") }}</span></template>
          <PieChartComponent
            v-if="questionTypeData.length"
            :data="questionTypeData"
            :colors="['#4f46e5','#818cf8','#6366f1','#10b981','#ec4899','#f59e0b','#d15d1a']"
            height="340px"
          />
          <el-empty v-else :description='$t("暂无数据")' :image-size="80" />
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="never" class="chart-card">
          <template #header><span class="card-title">{{ $t("游客活跃时段分布（近7天）") }}</span></template>
          <HeatmapComponent
            v-if="hourlyData.length"
            :data="hourlyData"
            height="340px"
          />
          <el-empty v-else :description='$t("暂无数据")' :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ========== 图表第三行: 知识盲区 + 情感分布 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="card-header-row">
              <span class="card-title">{{ $t("知识盲区分析") }}</span>
              <el-button size="small" type="primary" :loading="gapsLoading" @click="loadKnowledgeGaps">{{ $t("刷新") }}</el-button>
            </div>
          </template>
          <div v-if="knowledgeGaps">
            <div class="gap-summary">
              <span class="gap-count">{{ $t("发现") }} {{ $t(knowledgeGaps.uncertain_answers_count) }} {{ $t("个不确定回答") }}</span>
              <span class="gap-total">{{ $t("（共分析") }} {{ $t(knowledgeGaps.total_interactions_analyzed) }} {{ $t("条交互）") }}</span>
            </div>
            <div v-if="knowledgeGaps.uncertain_samples?.length" class="gap-samples">
              <div v-for="(sample, i) in knowledgeGaps.uncertain_samples.slice(0, 5)" :key="i" class="gap-sample-item">
                <el-tag size="small" type="warning" effect="dark">{{ $t(sample.keyword_matched) }}</el-tag>
                <span class="gap-text">{{ $t(sample.guide_response) }}</span>
              </div>
            </div>
            <div v-if="knowledgeGaps.top_entities?.length" class="gap-entities">
              <h4>{{ $t("高频实体词") }}</h4>
              <div class="entity-tags">
                <el-tag v-for="(e, i) in knowledgeGaps.top_entities.slice(0, 10)" :key="i" size="small" effect="plain" :type="i < 3 ? 'danger' : 'warning'">
                  {{ $t(e.entity) }} ({{ $t(e.count) }})
                </el-tag>
              </div>
            </div>
          </div>
          <el-empty v-else :description='$t("点击刷新加载数据")' :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header><span class="card-title">{{ $t("游客情感分布") }}</span></template>
          <div v-if="emotionStats" class="emotion-section">
            <div class="emotion-bars">
              <div class="emotion-bar-item">
                <span class="emotion-label">{{ $t("正面") }}</span>
                <div class="emotion-track"><div class="emotion-fill positive" :style="{ width: emotionStats.positive_rate + '%' }"></div></div><span class="emotion-rate">{{ $t(emotionStats.positive_rate) }}%</span>
                <span class="emotion-count">{{ $t(emotionStats.positive) }}</span>
              </div>
              <div class="emotion-bar-item">
                <span class="emotion-label">{{ $t("中性") }}</span>
                <div class="emotion-track"><div class="emotion-fill neutral" :style="{ width: (100 - emotionStats.positive_rate - emotionStats.negative_rate) + '%' }"></div></div><span class="emotion-rate">{{ $t((100 - emotionStats.positive_rate - emotionStats.negative_rate).toFixed(1)) }}%</span>
                <span class="emotion-count">{{ $t(emotionStats.neutral) }}</span>
              </div>
              <div class="emotion-bar-item">
                <span class="emotion-label">{{ $t("负面") }}</span>
                <div class="emotion-track"><div class="emotion-fill negative" :style="{ width: emotionStats.negative_rate + '%' }"></div></div><span class="emotion-rate">{{ $t(emotionStats.negative_rate) }}%</span>
                <span class="emotion-count">{{ $t(emotionStats.negative) }}</span>
              </div>
            </div>
            <div class="emotion-total">{{ $t("总交互数:") }} {{ $t(emotionStats.total) }}</div>
          </div>
          <el-empty v-else :description='$t("暂无数据")' :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ========== AI 报告生成区 ========== -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="24">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="card-header-row">
              <span class="card-title">{{ $t("AI 分析报告") }}</span>
              <div class="report-actions">
                <el-button size="small" type="primary" :loading="reportLoading === 'daily'" @click="generateReport('daily')">{{ $t("生成日报") }}</el-button>
                <el-button size="small" type="success" :loading="reportLoading === 'weekly'" @click="generateReport('weekly')">{{ $t("生成周报") }}</el-button>
              </div>
            </div>
          </template>
          <div v-if="currentReport" class="report-display">
            <div class="report-meta">
              <el-tag type="primary" size="large">{{ $t(currentReport.report?.title || currentReport.report_type) }}</el-tag>
              <span class="report-period">{{ $t(currentReport.report?.period || '') }}</span>
              <span class="report-time">{{ $t("生成时间:") }} {{ $t(currentReport.generated_at) }}</span>
            </div>
            <div class="report-body" v-if="currentReport.report">
              <div class="report-summary">{{ $t(currentReport.report.executive_summary) }}</div>
              <el-divider />
              <div class="key-metrics">
                <div v-for="(m, i) in currentReport.report.key_metrics" :key="i" class="metric-item">
                  <span class="metric-name">{{ $t(m.name) }}</span>
                  <span class="metric-value" :style="{ color: m.trend === 'up' ? '#059669' : m.trend === 'down' ? '#e11d48' : '#818cf8' }">
                    {{ $t(m.value) }} {{ $t(m.trend === 'up' ? '↑' : m.trend === 'down' ? '↓' : '→') }}
                  </span>
                  <span class="metric-comment">{{ $t(m.comment) }}</span>
                </div>
              </div>
              <el-divider />
              <div class="report-recommendations">
                <h4>{{ $t("改进建议") }}</h4>
                <div v-for="(rec, i) in currentReport.report.recommendations" :key="i" class="rec-item">
                  <el-tag :type="rec.priority === '高' ? 'danger' : rec.priority === '中' ? 'warning' : 'info'" size="small">
                    {{ $t(rec.priority) }}
                  </el-tag>
                  <span>{{ $t(rec.action) }}</span>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else :description='$t("点击上方按钮生成AI分析报告")' :image-size="80" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">import { t, locale } from '@/i18n'

import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { useResizeObserver } from '@vueuse/core'
import { serviceTrendOption, popularSpotsOption } from '@/utils/dashboardCharts'
import {
  getComprehensiveAnalytics, getKnowledgeGaps, generateAnalyticsReport,
  type ComprehensiveData, type KnowledgeGapData, type AnalyticsReport,
} from '@/api/analytics'
import PieChartComponent from '@/components/PieChartComponent.vue'
import HeatmapComponent from '@/components/HeatmapComponent.vue'

// ====== 加载状态 ======
const loading = ref(false)
const gapsLoading = ref(false)
const reportLoading = ref<string | null>(null)

// ====== 数据 ======
const comprehensive = ref<ComprehensiveData | null>(null)
const knowledgeGaps = ref<KnowledgeGapData | null>(null)
const currentReport = ref<AnalyticsReport | null>(null)

// 图表refs
const trendChartRef = ref<HTMLElement | null>(null)
const spotChartRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
let spotChart: echarts.ECharts | null = null

// ====== 统计卡片 ======
const statCards = computed(() => {
  const stats = comprehensive.value?.service_stats
  const emotion = comprehensive.value?.emotion_stats
  return [
    { title: t("总交互数"), value: emotion?.total || 0, color: '#818cf8', bgColor: 'rgba(99,102,241,0.08)', sub: t("全局交互次数") },
    { title: t("好评率"), value: (emotion?.positive_rate || 0) + '%', color: '#059669', bgColor: 'rgba(99,102,241,0.08)', sub: t("正面情绪占比") },
    { title: t("今日提问"), value: stats?.today_questions || 0, color: '#4f46e5', bgColor: 'rgba(99,102,241,0.08)', sub: t("今日游客提问") },
    { title: t("负面率"), value: (emotion?.negative_rate || 0) + '%', color: '#e11d48', bgColor: 'rgba(99,102,241,0.08)', sub: t("负面情绪占比") },
    { title: t("本周服务"), value: stats?.week_sessions || 0, color: '#6366f1', bgColor: 'rgba(99,102,241,0.08)', sub: t("本周会话数") },
    { title: t("知识覆盖"), value: knowledgeGaps.value ? Math.max(0, 100 - knowledgeGaps.value.uncertain_answers_count * 2) + '%' : 'N/A', color: '#818cf8', bgColor: 'rgba(99,102,241,0.08)', sub: t("知识响应率") },
  ]
})

// 问题类型分布（基于情感统计模拟）
const questionTypeData = computed(() => {
  const emotion = comprehensive.value?.emotion_stats
  if (!emotion) return []
  return [
    { name: t("满意度相关"), value: emotion.positive || 0 },
    { name: t("一般问题"), value: emotion.neutral || 0 },
    { name: t("投诉/不满"), value: emotion.negative || 0 },
  ]
})

const emotionStats = computed(() => comprehensive.value?.emotion_stats)
const hourlyData = computed(() => comprehensive.value?.hourly_distribution || [])

// ====== 初始化趋势图 ======
function initTrendChart() {
  if (!trendChartRef.value || !comprehensive.value?.daily_trend) return
  trendChart ??= echarts.init(trendChartRef.value, 'soft-ui')
  trendChart.resize()
  trendChart.setOption(serviceTrendOption(comprehensive.value.daily_trend, trendChartRef.value.clientWidth))
}
function initSpotChart() {
  if (!spotChartRef.value || !comprehensive.value?.spot_ranking) return
  spotChart ??= echarts.init(spotChartRef.value, 'soft-ui')
  spotChart.resize()
  spotChart.setOption(popularSpotsOption(comprehensive.value.spot_ranking, spotChartRef.value.clientWidth))
}
useResizeObserver(trendChartRef, initTrendChart)
useResizeObserver(spotChartRef, initSpotChart)
onBeforeUnmount(() => { trendChart?.dispose(); spotChart?.dispose() })

// ====== 数据加载 ======
async function loadComprehensive() {
  try {
    const { data } = await getComprehensiveAnalytics()
    if (data.code === 0) {
      comprehensive.value = data.data
      await nextTick()
      initTrendChart()
      initSpotChart()
    }
  } catch (e: any) { console.error('Failed to load comprehensive data', e) }
}

async function loadKnowledgeGaps() {
  gapsLoading.value = true
  try {
    const { data } = await getKnowledgeGaps()
    if (data.code === 0) knowledgeGaps.value = data.data
  } catch (e: any) { ElMessage.error(t("加载知识盲区失败")) }
  finally { gapsLoading.value = false }
}

async function generateReport(type: 'daily' | 'weekly') {
  reportLoading.value = type
  try {
    const { data } = await generateAnalyticsReport(type)
    if (data.code === 0) {
      currentReport.value = data.data
      ElMessage.success(t("{p0}生成成功！", {p0: type === 'daily' ? '日报' : '周报'}))
    } else {
      ElMessage.error(data.message || t("报告生成失败"))
    }
  } catch (e: any) { ElMessage.error(t("请求失败")) }
  finally { reportLoading.value = null }
}

onMounted(async () => {
  loading.value = true
  await Promise.all([loadComprehensive(), loadKnowledgeGaps()])
  loading.value = false
})
watch(locale, () => { initTrendChart(); initSpotChart() })
</script>

<style lang="scss" scoped>
.dashboard-container { padding: 16px; }

// 统计卡片
.stat-row { margin-bottom: 16px; }
.stat-card { border-radius: 12px; padding: 16px 20px; transition: transform .2s; cursor: default;
  &:hover { transform: translateY(-2px); }
}
.stat-card-body { display: flex; align-items: center; gap: 12px; }
.stat-icon { font-size: 28px; }
.stat-value { font-size: 24px; font-weight: 700; }
.stat-title { font-size: 18px; color: var(--text-muted); }
.stat-sub { margin-top: 4px; font-size: 18px; color: var(--text-muted); }

// 图表卡片
.chart-row { margin-bottom: 16px; }
.chart-card { border-radius: 12px; }
.card-title { font-size: 18px; font-weight: 600; }
.card-header-row { display: flex; justify-content: space-between; align-items: center; }

// 知识盲区
.gap-summary { margin-bottom: 12px; }
.gap-count { font-size: 18px; font-weight: 700; color: var(--danger); }
.gap-total { font-size: 18px; color: var(--text-muted); }
.gap-sample-item { display: flex; align-items: flex-start; gap: 8px; padding: 8px 0; border-bottom: 1px dashed var(--glass-line); }
.gap-text { font-size: 18px; color: var(--text-secondary); line-height: 1.5; }
.gap-entities { margin-top: 12px; }
.gap-entities h4 { font-size: 18px; margin: 0 0 6px; }
.entity-tags { display: flex; flex-wrap: wrap; gap: 6px; }

// 情感分布
.emotion-bars { display: flex; flex-direction: column; gap: 14px; }
.emotion-bar-item { display: flex; align-items: center; gap: 10px; }
.emotion-label { width: 40px; font-size: 18px; color: var(--text-secondary); }
.emotion-track { flex: 1; height: 24px; background: var(--glass); border-radius: 6px; overflow: hidden; }
.emotion-fill { height: 100%; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 600; color: var(--text); transition: width .6s ease; }
.emotion-fill.positive { background: var(--success); }
.emotion-fill.neutral { background: var(--champagne); }
.emotion-fill.negative { background: var(--danger); }
.emotion-count { width: 35px; font-size: 18px; color: var(--text-muted); text-align: right; }
.emotion-total { margin-top: 10px; font-size: 18px; color: var(--text-muted); text-align: center; }

// 报告区
.report-actions { display: flex; gap: 8px; }
.report-display { display: flex; flex-direction: column; gap: 12px; }
.report-meta { display: flex; align-items: center; gap: 16px; }
.report-period { font-size: 18px; color: var(--text-secondary); }
.report-time { font-size: 18px; color: var(--text-muted); margin-left: auto; }
.report-summary { font-size: 18px; color: var(--text); line-height: 1.7; padding: 12px; background: var(--glass); border-radius: 8px; border-left: 4px solid var(--glass-line); }
.key-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.metric-item { padding: 10px; background: var(--glass); border-radius: 8px; }
.metric-name { display: block; font-size: 18px; color: var(--text-muted); }
.metric-value { display: block; font-size: 18px; font-weight: 700; margin: 4px 0; }
.metric-comment { display: block; font-size: 18px; color: var(--text-muted); }
.report-recommendations h4 { margin: 0 0 8px; font-size: 18px; }
.rec-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 18px; color: var(--text); }
.rec-item + .rec-item { border-top: 1px dashed var(--glass-line); }

.dashboard-container { padding:0; container-type:inline-size; }
.stat-row { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:14px; margin:0 0 24px!important; }
.stat-row .el-col { width:auto; max-width:none; padding:0!important; }
.stat-card { height:100%; padding:22px 18px; }
.chart-row { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:20px; margin:0 0 24px!important; }
.chart-row .el-col { width:auto; max-width:none; padding:0!important; min-width:0; }
.chart-row .el-col:only-child { grid-column:1/-1; }
.chart-card { height:100%; }
.chart-card :deep(.el-card__header) { padding:20px 24px; }
.chart-card :deep(.el-card__body) { padding:20px 22px; }
.dashboard-chart { width:100%; height:400px; }
@container (max-width:1050px) {
  .chart-row { grid-template-columns:minmax(0,1fr); }
  .stat-row { grid-template-columns:repeat(3,minmax(0,1fr)); }
}
</style>
