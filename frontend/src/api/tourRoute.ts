import { request_handler, type ResultPackage } from '@/api/base'
import { header_authorization } from '@/api/user'
import type { ScenicSpotItem } from '@/api/scenicSpot'

// ---- 查询参数 ----

interface RouteListParams {
  currentPage: number
  pageSize: number
  theme?: string
}

// ---- 数据实体 ----

interface TourRouteItem {
  route_id: number
  name: string
  theme: string
  estimated_time_minutes: number
  description: string
  spot_ids?: number[]
  spot_count?: number
  spot_names?: string[]
  walking_distance_meters?: number
  spots?: ScenicSpotItem[]
  create_time: string
  update_time: string
}

interface TourRouteListData {
  route_list: TourRouteItem[]
  currentPage: number
  pageSize: number
  totalSize: number
}

/** 创建/编辑线路的请求体 */
interface RouteCreateData {
  name: string
  theme: string
  estimated_time_minutes: number
  description: string
  spot_ids: number[]
}

interface RecommendRequest {
  preferences: Record<string, unknown>
}

interface RecommendResult {
  route_list: TourRouteItem[]
  match_score: number
}

// ---- 接口函数 ----

/** 分页查询线路列表 */
const getRouteList = (
  currentPage: number,
  pageSize: number,
  theme?: string,
) => {
  return request_handler<ResultPackage<TourRouteListData>>({
    method: 'GET',
    url: '/tour-routes/list',
    params: { currentPage, pageSize, theme },
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 查询线路详情 */
const getRouteDetail = (routeId: number) => {
  return request_handler<ResultPackage<TourRouteItem>>({
    method: 'GET',
    url: `/tour-routes/info/${routeId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 新建线路 */
const createRoute = (data: RouteCreateData) => {
  return request_handler<ResultPackage<TourRouteItem>>({
    method: 'POST',
    url: '/tour-routes/create',
    data,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 编辑线路 */
const editRoute = (routeId: number, data: Partial<RouteCreateData>) => {
  return request_handler<ResultPackage<TourRouteItem>>({
    method: 'PUT',
    url: `/tour-routes/edit/${routeId}`,
    data,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 删除线路 */
const deleteRoute = (routeId: number) => {
  return request_handler<ResultPackage<string>>({
    method: 'DELETE',
    url: `/tour-routes/delete/${routeId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 智能推荐线路 */
const getRecommendation = (preferences: Record<string, unknown>) => {
  return request_handler<ResultPackage<RecommendResult>>({
    method: 'POST',
    url: '/tour-routes/recommend',
    data: { preferences },
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

export {
  type RouteListParams,
  type TourRouteItem,
  type TourRouteListData,
  type RouteCreateData,
  type RecommendRequest,
  type RecommendResult,
  getRouteList,
  getRouteDetail,
  createRoute,
  editRoute,
  deleteRoute,
  getRecommendation,
}
