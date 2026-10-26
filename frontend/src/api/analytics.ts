import { request_handler, type ResultPackage } from '@/api/base'
import { header_authorization } from '@/api/user'

// ---- 数据实体 ----

interface SentimentReport {
  session_id?: number
  overall_sentiment: 'positive' | 'neutral' | 'negative'
  total_interactions: number
  positive_count: number
  neutral_count: number
  negative_count: number
  positive_ratio: number
  neutral_ratio: number
  negative_ratio: number
  top_positive_keywords: string[]
  top_negative_keywords: string[]
  hot_questions: Array<{ question: string; count: number }>
  hot_topics: Array<{ topic: string; count: number }>
  comment_highlights: Array<{
    comment: string
    sentiment: string
    confidence: number
    role: string
    time: string
  }>
  suggestions: string[]
  generated_time?: string
}

interface DashboardStats {
  // 核心指标
  total_sessions: number
  active_sessions: number
  total_visitors: number
  total_sales: number
  conversion_rate: number

  // 趋势数据（近30天）
  daily_sessions: number[]
  daily_visitors: number[]
  daily_sales: number[]

  // 品类分布
  category_distribution: Array<{
    category: string
    count: number
    ratio: number
  }>

  // Top 景点
  top_spots: Array<{
    spot_name: string
    visit_count: number
    conversion_rate: number
  }>

  // Top 线路
  top_routes: Array<{
    route_name: string
    session_count: number
    total_sales: number
  }>
}

interface FeedbackItem {
  feedback_id: number
  session_id: number
  user_name: string
  rating: number
  content: string
  tags: string[]
  is_resolved: boolean
  reply?: string
  create_time: string
}

interface FeedbackListData {
  feedback_list: FeedbackItem[]
  currentPage: number
  pageSize: number
  totalSize: number
  average_rating: number
}

// ---- 接口函数 ----

/** 获取情感分析报告（可按场次过滤） */
const getSentimentReport = (sessionId?: number) => {
  return request_handler<ResultPackage<SentimentReport>>({
    method: 'GET',
    url: '/analytics/sentiment-report',
    params: { sessionId },
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 获取 Dashboard 核心统计数据 */
const getDashboardStats = () => {
  return request_handler<ResultPackage<DashboardStats>>({
    method: 'GET',
    url: '/analytics/dashboard/stats',
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 分页查询用户反馈列表 */
const getFeedbackList = (currentPage: number, pageSize: number) => {
  return request_handler<ResultPackage<FeedbackListData>>({
    method: 'GET',
    url: '/analytics/feedback/list',
    params: { currentPage, pageSize },
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

// ---- 新增：综合看板 + 报告 API ----

interface SpotRankingItem {
  spot_id: number
  spot_name: string
  category: string
  session_count: number
}

interface DailyTrendItem {
  date: string
  sessions: number
  questions: number
  satisfaction: number
}

interface HourlyDistItem {
  day: string
  hour: string
  count: number
}

interface EmotionStats {
  total: number
  positive: number
  neutral: number
  negative: number
  positive_rate: number
  negative_rate: number
}

interface ComprehensiveData {
  spot_ranking: SpotRankingItem[]
  daily_trend: DailyTrendItem[]
  hourly_distribution: HourlyDistItem[]
  emotion_stats: EmotionStats
  sentiment: Record<string, any>
  service_stats: Record<string, any>
}

/** 获取综合分析看板数据 */
const getComprehensiveAnalytics = () => {
  return request_handler<ResultPackage<ComprehensiveData>>({
    method: 'GET',
    url: '/analytics/comprehensive',
    headers: { Authorization: header_authorization.value },
  })
}

interface KnowledgeGapData {
  uncertain_answers_count: number
  uncertain_samples: Array<{
    guide_response: string
    keyword_matched: string
    time: string
  }>
  top_entities: Array<{ entity: string; count: number }>
  total_interactions_analyzed: number
}

/** 获取知识盲区分析 */
const getKnowledgeGaps = () => {
  return request_handler<ResultPackage<KnowledgeGapData>>({
    method: 'GET',
    url: '/analytics/knowledge-gaps',
    headers: { Authorization: header_authorization.value },
  })
}

interface AnalyticsReport {
  report_id: number
  report_type: string
  report: {
    title: string
    period: string
    executive_summary: string
    key_metrics: Array<{ name: string; value: string; trend: string; comment: string }>
    sentiment_analysis: { overall: string; highlights: string[]; concerns: string[] }
    hot_topics: string[]
    service_insights: { strengths: string[]; weaknesses: string[] }
    recommendations: Array<{ priority: string; action: string; expected_impact: string }>
    next_steps: string
  }
  generated_at: string
}

/** 生成AI分析报告 */
const generateAnalyticsReport = (reportType: 'daily' | 'weekly' | 'session', sessionId?: number) => {
  return request_handler<ResultPackage<AnalyticsReport>>({
    method: 'POST',
    url: '/analytics/generate-report',
    params: { report_type: reportType, session_id: sessionId },
    headers: { Authorization: header_authorization.value },
  })
}

interface ReportListItem {
  report_id: number
  report_type: string
  content: string
  created_at: string
}

/** 获取历史报告列表 */
const getReportList = (reportType?: string) => {
  return request_handler<ResultPackage<{ reports: ReportListItem[] }>>({
    method: 'GET',
    url: '/analytics/reports',
    params: { report_type: reportType },
    headers: { Authorization: header_authorization.value },
  })
}

// ---- 游客画像 API ----

interface VisitorProfile {
  session_id: number
  interests: Array<{ category: string; score: number }>
  engagement: {
    total_messages: number
    questions_count: number
    avg_question_length: number
    engagement_level: string
  }
  emotion_trend: {
    trend: string
    overall_score: number
    overall_label: string
  }
  intent_distribution: Array<{ intent: string; count: number }>
  top_questions: string[]
}

/** 获取游客画像 */
const getVisitorProfile = (sessionId: number) => {
  return request_handler<ResultPackage<VisitorProfile>>({
    method: 'GET',
    url: `/analytics/visitor-profile/${sessionId}`,
    headers: { Authorization: header_authorization.value },
  })
}

interface VisitorSegments {
  segments: Array<{ segment: string; count: number; percentage: number }>
  total_sessions: number
}

/** 获取游客群体细分 */
const getVisitorSegments = () => {
  return request_handler<ResultPackage<VisitorSegments>>({
    method: 'GET',
    url: '/analytics/visitor-segments',
    headers: { Authorization: header_authorization.value },
  })
}

export {
  type SentimentReport,
  type DashboardStats,
  type FeedbackItem,
  type FeedbackListData,
  getSentimentReport,
  getDashboardStats,
  getFeedbackList,
  type ComprehensiveData, type SpotRankingItem, type DailyTrendItem,
  type HourlyDistItem, type EmotionStats, type KnowledgeGapData,
  type AnalyticsReport, type ReportListItem, type VisitorProfile, type VisitorSegments,
  getComprehensiveAnalytics, getKnowledgeGaps,
  generateAnalyticsReport, getReportList,
  getVisitorProfile, getVisitorSegments,
}
