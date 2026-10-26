import { request_handler, type ResultPackage } from '@/api/base'

interface DashboardItem {
  spotCount: number          // 景区景点数
  docCount: number           // 知识文档数
  guideCount: number         // 数字导游数
  routeCount: number         // 游览路线数
  todaySessions: number      // 今日导览次数
  weekSessions: number       // 本周导览次数
  todayQuestions: number     // 今日问答数
  avgSatisfaction: number    // 平均满意度(%)
  activeSessions: number     // 当前进行中会话数
  totalInteractions: number  // 总交互次数
  totalChunks: number        // 知识片段总数
  // 7日趋势折线图
  sessionTrend: number[]     // 每日服务人次
  satisfactionTrend: number[] // 每日满意度
  newSessionTrend: number[]  // 每日新开会话
  activeUserTrend: number[]  // 每日活跃用户
}

// 获取运营数据大屏信息
const getDashboardInfoRequest = () => {
  return request_handler<ResultPackage<DashboardItem>>({
    method: 'GET',
    url: '/dashboard'
  })
}

export { getDashboardInfoRequest, type DashboardItem }
