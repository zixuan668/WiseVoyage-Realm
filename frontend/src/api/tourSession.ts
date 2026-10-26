import { request_handler, type ResultPackage } from '@/api/base'
import { header_authorization } from '@/api/user'

// ---- 数据实体 ----

interface TourSessionItem {
  session_id: number
  name: string
  live_status: number  // 0=未开始 1=进行中 2=已结束
  start_time: string
  visitor_preferences?: string
}

interface TourSessionListData {
  session_list: TourSessionItem[]
  currentPage: number
  pageSize: number
  totalSize: number
}

interface SessionLiveInfo {
  session: TourSessionItem
  current_viewer_count: number
  peak_viewer_count: number
  total_views: number
  comment_count: number
  like_count: number
  product_click_count: number
  order_count: number
  total_sales: number
}

// ---- 接口函数 ----

/** 分页查询直播场次列表 */
const getSessionList = (currentPage: number, pageSize: number) => {
  return request_handler<ResultPackage<TourSessionListData>>({
    method: 'GET',
    url: '/tour-session/list',
    params: { currentPage, pageSize, all_users: true },
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 获取场次实时直播信息 */
const getSessionLiveInfo = (sessionId: number) => {
  return request_handler<ResultPackage<SessionLiveInfo>>({
    method: 'GET',
    url: `/tour-session/live-info/${sessionId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 开始直播 */
const startSession = (sessionId: number) => {
  return request_handler<ResultPackage<TourSessionItem>>({
    method: 'PUT',
    url: `/tour-session/start/${sessionId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 结束直播 */
const endSession = (sessionId: number) => {
  return request_handler<ResultPackage<TourSessionItem>>({
    method: 'PUT',
    url: `/tour-session/end/${sessionId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 创建导览会话 */
const createSession = (name: string, routeId: number, guideId: number, preferences: string) => {
  return request_handler<ResultPackage<{ session_id: number }>>({
    method: 'POST',
    url: '/tour-session/create',
    params: { name, route_id: routeId, guide_id: guideId, visitor_preferences: preferences },
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

interface IssueAnalysisResult {
  knowledge_gaps: string[]
  common_confusions: string[]
  service_gaps: string[]
  satisfaction: '高' | '中' | '低'
  satisfaction_reason: string
  hot_topics: string[]
  improvement_actions: string[]
  summary: string
  analysis_source: string
  analyzed_question_count: number
}

/** AI分析导览会话 */
const analyzeSession = (sessionId: number) => {
  return request_handler<ResultPackage<IssueAnalysisResult>>({
    method: 'POST',
    url: `/tour-session/analyze/${sessionId}`,
    timeout: 180000,
    headers: { Authorization: header_authorization.value },
  })
}

export interface SessionDetail {
  session: {
    session_id: number; name: string; visitor_preferences: string
    live_status: number; start_time: string; end_time: string
    current_spot_index: number
  }
  conversation: Array<{ role: string; message: string; send_time: string }>
  stats: { total_messages: number; user_questions: number; guide_responses: number }
}

/** 获取会话详情（完整对话记录） */
const getSessionDetail = (sessionId: number) => {
  return request_handler<ResultPackage<SessionDetail>>({
    method: 'GET',
    url: `/tour-session/detail/${sessionId}`,
    headers: { Authorization: header_authorization.value },
  })
}

// ---- AI分析增强接口 ----

interface QuestionAnalysisItem {
  index: number
  question: string
  answer: string
  question_type: string
  question_quality: string
  answer_quality_score: number
  knowledge_covered: string
  improvement_note: string
  time: string
}

interface QuestionAnalysisResult {
  session_id: number
  total_questions: number
  per_question: QuestionAnalysisItem[]
  summary_stats: {
    avg_answer_score: number
    knowledge_gaps: string[]
    question_type_distribution: Record<string, number>
    overall_assessment: string
  }
}

/** 逐题深度分析 */
const analyzeQuestions = (sessionId: number) => {
  return request_handler<ResultPackage<QuestionAnalysisResult>>({
    method: 'POST',
    url: `/tour-session/analyze-questions/${sessionId}`,
    headers: { Authorization: header_authorization.value },
  })
}

interface SessionReportResult {
  session_id: number
  report: {
    title?: string
    session_quality_score: number
    quality_level: string
    visitor_profile: {
      interests: string[]
      engagement_level: string
      satisfaction_trend: string
    }
    qa_summary: {
      total_exchanges: number
      deep_questions_ratio: number
      avg_response_length: number
    }
    knowledge_gaps: string[]
    service_highlights: string[]
    improvement_suggestions: Array<{
      area: string
      suggestion: string
      priority: string
    }>
    executive_summary: string
  }
  generated_at: string
}

/** 生成会话综合报告 */
const generateSessionReport = (sessionId: number) => {
  return request_handler<ResultPackage<SessionReportResult>>({
    method: 'POST',
    url: `/tour-session/session-report/${sessionId}`,
    headers: { Authorization: header_authorization.value },
  })
}

interface SessionComparison {
  comparison: Array<{
    session_id: number
    total_messages: number
    user_questions: number
    guide_responses: number
    avg_user_msg_length: number
    avg_guide_msg_length: number
    time_span: string
  }>
}

/** 多会话对比分析 */
const compareSessions = (sessionIds: number[]) => {
  return request_handler<ResultPackage<SessionComparison>>({
    method: 'POST',
    url: '/tour-session/compare-sessions',
    data: sessionIds,
    headers: { Authorization: header_authorization.value },
  })
}

/** 删除导览会话（软删除） */
const deleteSession = (sessionId: number) => {
  return request_handler<ResultPackage<any>>({
    method: 'DELETE',
    url: `/tour-session/${sessionId}`,
    headers: { Authorization: header_authorization.value },
  })
}

export {
  type TourSessionItem, type TourSessionListData, type SessionLiveInfo,
  getSessionList, getSessionLiveInfo, startSession, endSession, createSession,
  analyzeSession, getSessionDetail, analyzeQuestions, generateSessionReport,
  compareSessions, deleteSession,
  type QuestionAnalysisItem, type QuestionAnalysisResult, type SessionReportResult,
  type IssueAnalysisResult,
}
