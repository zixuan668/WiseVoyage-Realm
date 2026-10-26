<script setup lang="ts">import { t, formatTableCell } from '@/i18n'

import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus/es'
import { getSentimentReport, type SentimentReport } from '@/api/analytics'
import { AxiosError } from 'axios'

// ======================== 加载 ========================

const loading = ref(false)
const sentimentReport = ref<SentimentReport | null>(null)

const loadData = async () => {
  loading.value = true
  try {
    const { data } = await getSentimentReport()
    if (data.code === 0) {
      sentimentReport.value = data.data
    } else {
      ElMessage.error(t("获取数据失败：") + data.message)
    }
  } catch (error: unknown) {
    if (error instanceof AxiosError) {
      ElMessage.error(t("加载失败：") + error.message)
    } else {
      ElMessage.error(t("未知错误"))
    }
  } finally {
    loading.value = false
  }
}

// ======================== 统计卡片 ========================

const statCards = computed(() => {
  const r = sentimentReport.value
  return [
    {
      title: t("总互动次数"),
      value: r?.total_interactions ?? 0,
      unit: t("次"),
      color: '#818cf8',
      bgColor: 'rgba(99,102,241,0.08)',
      sub: t("游客提问总数"),
    },
    {
      title: t("好评率"),
      value: r ? (r.positive_ratio * 100).toFixed(1) : '0.0',
      unit: '%',
      color: '#059669',
      bgColor: 'rgba(99,102,241,0.08)',
      sub: t("{p0} 条正面", {p0: r?.positive_count ?? 0}),
    },
    {
      title: t("负面反馈"),
      value: r?.negative_count ?? 0,
      unit: t("条"),
      color: '#e11d48',
      bgColor: 'rgba(99,102,241,0.08)',
      sub: t("占比 {p0}%", {p0: r ? (r.negative_ratio * 100).toFixed(1) : '0'}),
    },
    {
      title: t("整体趋势"),
      value: sentimentTrendLabel.value,
      unit: '',
      color: '#4f46e5',
      bgColor: 'rgba(99,102,241,0.08)',
      sub: sentimentTrendSub.value,
      isText: true,
    },
  ]
})

const sentimentTrendLabel = computed(() => {
  const s = sentimentReport.value?.overall_sentiment
  if (s === 'positive') return t("上升向好")
  if (s === 'neutral') return t("整体平稳")
  if (s === 'negative') return t("需关注")
  return t("暂无数据")
})

const sentimentTrendSub = computed(() => {
  const s = sentimentReport.value?.overall_sentiment
  if (s === 'positive') return t("游客情绪以正面为主")
  if (s === 'neutral') return t("正负面基本持平")
  if (s === 'negative') return t("负面占比较高，需改进")
  return ''
})

// ======================== 情感分布柱状图 ========================

const sentimentBars = computed(() => {
  const r = sentimentReport.value
  if (!r) return []
  const positivePercent = Math.round(r.positive_ratio * 100)
  const neutralPercent = Math.round(r.neutral_ratio * 100)
  const negativePercent = Math.round(r.negative_ratio * 100)
  return [
    { label: t("正面评价"), percent: positivePercent, count: r.positive_count, color: '#059669' },
    { label: t("中性评价"), percent: neutralPercent, count: r.neutral_count, color: '#4f46e5' },
    { label: t("负面评价"), percent: negativePercent, count: r.negative_count, color: '#e11d48' },
  ]
})

// ======================== 热门话题（后端关键词匹配分类） ========================

const hotTopics = computed(() => {
  return sentimentReport.value?.hot_topics ?? []
})

// ======================== 热门提问（高频问题 TOP8） ========================

const hotQuestions = computed(() => {
  return sentimentReport.value?.hot_questions ?? []
})

// ======================== 评论高亮 ========================

const commentHighlights = computed(() => {
  return sentimentReport.value?.comment_highlights.slice(0, 10) ?? []
})

const sentimentColorMap: Record<string, string> = {
  positive: '#059669',
  neutral: '#64748b',
  negative: '#e11d48',
}

// ======================== 服务建议 ========================

const serviceSuggestions = computed(() => {
  return sentimentReport.value?.suggestions ?? []
})

// ======================== 生命周期 ========================

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="feedback-analytics-container" v-loading="loading">
    <!-- ========== 统计卡片 ========== -->
    <el-row :gutter="20" class="stat-row">
      <el-col v-for="(card, idx) in statCards" :key="idx" :span="6">
        <div class="stat-card" :style="{ backgroundColor: card.bgColor }">
          <div class="stat-card-header">
            <span class="stat-card-title">{{ $t(card.title) }}</span>
          </div>
          <div class="stat-card-body">
            <span v-if="!card.isText" class="stat-card-value" :style="{ color: card.color }">
              {{ $t(card.value) }}
            </span>
            <span v-else class="stat-card-value stat-card-text" :style="{ color: card.color }">
              {{ $t(card.value) }}
            </span>
            <span v-if="card.unit" class="stat-card-unit">{{ $t(card.unit) }}</span>
          </div>

        </div>
      </el-col>
    </el-row>

    <!-- ========== 图表区 ========== -->
    <el-row :gutter="20" class="charts-row">
      <!-- 情感分布 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span class="chart-title">{{ $t("游客情感分布") }}</span>
          </template>
          <div v-if="sentimentBars.length > 0" class="bar-chart">
            <div v-for="(bar, idx) in sentimentBars" :key="idx" class="bar-item">
              <span class="bar-label">{{ $t(bar.label) }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: bar.percent + '%', backgroundColor: bar.color }">
                  <span v-if="bar.percent > 10" class="bar-percent">{{ $t(bar.percent) }}%</span>
                </div>
                <span v-if="bar.percent <= 10" class="bar-percent outside" :style="{ left: bar.percent + '%' }">{{ $t(bar.percent) }}%</span>
              </div>
              <span class="bar-count">{{ $t(bar.count) }} {{ $t("条") }}</span>
            </div>
          </div>
          <el-empty v-else :description='$t("暂无情感数据")' :image-size="80" />
        </el-card>
      </el-col>

      <!-- 热门话题（关键词分类统计） -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span class="chart-title">{{ $t("热门话题分类") }}</span>
          </template>
          <el-table
            v-if="hotTopics.length > 0"
            :data="hotTopics"
            style="width: 100%"
            max-height="320"
            stripe
            size="small"
          >
            <el-table-column prop="topic" :label='$t("话题类别")' min-width="140">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" type="primary">{{ $t(row.topic) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :formatter="formatTableCell" prop="count" :label='$t("提及次数")' width="110" align="center" sortable />
          </el-table>
          <el-empty v-else :description='$t("暂无话题数据")' :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ========== 热门提问 + 服务建议 ========== -->
    <el-row :gutter="20" class="bottom-row">
      <!-- 热门提问 TOP8 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span class="chart-title">{{ $t("热门提问 TOP8") }}</span>
          </template>
          <div v-if="hotQuestions.length > 0" class="hot-questions-list">
            <div v-for="(q, idx) in hotQuestions" :key="idx" class="hot-q-item">
              <span class="hot-q-rank" :class="idx < 3 ? 'top3' : ''">{{ $t(idx + 1) }}</span>
              <span class="hot-q-text">{{ $t(q.question) }}</span>
              <span class="hot-q-count">{{ $t(q.count) }} {{ $t("次") }}</span>
            </div>
          </div>
          <el-empty v-else :description='$t("暂无提问数据")' :image-size="80" />
        </el-card>
      </el-col>

      <!-- 服务建议 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span class="chart-title">{{ $t("服务优化建议") }}</span>
          </template>
          <div v-if="serviceSuggestions.length > 0" class="suggestions-list">
            <el-alert
              v-for="(s, idx) in serviceSuggestions"
              :key="idx"
              :title="$t(s)"
              :type="idx === 0 ? 'warning' : 'info'"
              :closable="false"
              show-icon
              class="suggestion-item"
            />
          </div>
          <el-empty v-else :description='$t("暂无建议")' :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ========== 评论精选 ========== -->
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span class="chart-title">{{ $t("游客留言精选") }}</span>
          </template>
          <div v-if="commentHighlights.length > 0" class="comments-grid">
            <div v-for="(item, idx) in commentHighlights" :key="idx" class="comment-item">
              <div class="comment-header">
                <span class="sentiment-dot" :style="{ backgroundColor: sentimentColorMap[item.sentiment] || '#64748b' }" />
                <span class="comment-sentiment-label">
                  {{ $t(item.sentiment === 'positive' ? '正面' : item.sentiment === 'negative' ? '负面' : '中性') }}
                </span>
                <el-tag size="small" effect="plain" type="info">{{ $t(item.role === 'user' ? '游客' : '导游') }}</el-tag>
                <span class="comment-time">{{ $t(item.time?.slice(0, 16) || '') }}</span>
              </div>
              <p class="comment-text">&ldquo;{{ $t(item.comment) }}&rdquo;</p>
            </div>
          </div>
          <el-empty v-else :description='$t("暂无留言数据")' :image-size="80" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style lang="scss" scoped>
.feedback-analytics-container { padding: 16px; overflow-x: hidden; }

.stat-row { margin-bottom: 20px; }
.stat-card { border-radius: 12px; padding: 20px 24px; transition: transform .2s; &:hover { transform: translateY(-2px); } }
.stat-card-header { margin-bottom: 10px; }
.stat-card-title { font-size: 18px; color: var(--text-secondary); font-weight: 500; }
.stat-card-body { display: flex; align-items: baseline; gap: 4px; }
.stat-card-value { font-size: 32px; font-weight: 700; line-height: 1.2; }
.stat-card-text { font-size: 22px; }
.stat-card-unit { font-size: 18px; color: var(--text-muted); }
.stat-card-sub { margin-top: 4px; font-size: 18px; color: var(--text-muted); }

.charts-row { margin-bottom: 20px; }
.bottom-row { margin-bottom: 20px; }
.chart-card { border-radius: 12px; margin-bottom: 20px; .chart-title { font-size: 18px; font-weight: 600; } }

// 柱状图
.bar-chart { display: grid; grid-template-columns: max-content minmax(0, 1fr) max-content; align-items: center; gap: 18px 16px; }
.bar-item { display: contents; }
.bar-label { font-size: 18px; color: var(--text-secondary); white-space: nowrap; }
.bar-track { min-width: 0; height: 28px; background: var(--glass); border-radius: 6px; overflow: hidden; position: relative; }
.bar-fill { height: 100%; border-radius: 6px; display: flex; align-items: center; justify-content: flex-end; transition: width .6s ease; min-width: 0; }
.bar-percent { padding-right: 8px; color: var(--text); font-size: 18px; font-weight: 600; white-space: nowrap; font-variant-numeric: tabular-nums; &.outside { padding: 0; margin-left: 8px; color: var(--text); position: absolute; top: 50%; transform: translateY(-50%); } }
.bar-count { min-width: 3.5em; font-size: 18px; color: var(--text-muted); text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }

// 热门提问
.hot-questions-list { display: flex; flex-direction: column; gap: 8px; }
.hot-q-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: var(--glass); border-radius: 8px; }
.hot-q-rank { width: 22px; height: 22px; border-radius: 6px; background: var(--glass); color: var(--text-muted); font-size: 18px; font-weight: 600; display: flex; align-items: center; justify-content: center; flex-shrink: 0; &.top3 { background: var(--glass); color: var(--champagne); } }
.hot-q-text { flex: 1; font-size: 18px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hot-q-count { font-size: 18px; color: var(--text-muted); flex-shrink: 0; }

// 服务建议
.suggestions-list { display: flex; flex-direction: column; gap: 10px; }
.suggestion-item { border-radius: 8px; }

// 评论
.comments-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; max-height: 440px; overflow-y: auto; }
.comment-item { padding: 12px 14px; background: var(--glass); border-radius: 8px; border-left: 3px solid var(--glass-line); }
.comment-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.sentiment-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.comment-sentiment-label { font-size: 18px; color: var(--text-secondary); font-weight: 500; }
.comment-time { font-size: 18px; color: var(--text-muted); margin-left: auto; }
.comment-text { font-size: 18px; color: var(--text); line-height: 1.5; margin: 0; }
</style>
