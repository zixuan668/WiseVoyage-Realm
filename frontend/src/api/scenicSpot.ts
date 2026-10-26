import { request_handler, type ResultPackage } from '@/api/base'
import { header_authorization } from '@/api/user'

// ---- 查询参数 ----

interface SpotListParams {
  currentPage: number
  pageSize: number
  spotName?: string
  category?: string
}

// ---- 数据实体 ----

interface ScenicSpotItem {
  city?:string
  latitude?:number
  longitude?:number
  visit_duration?:number
  photo_tips?:string
  service_facilities?:string
  tour_tips?:string
  spot_id: number
  spot_number?: number | null
  spot_name: string
  category: string
  tags: string
  location: string
  best_season: string
  description: string
  history_detail: string
  image_path: string
  instruction: string
  upload_date: string
}

interface ScenicSpotListData {
  spot_list: ScenicSpotItem[]
  currentPage: number
  pageSize: number
  totalSize: number
}

// ---- 接口函数 ----

/** 分页查询景点列表 */
const getSpotList = (
  currentPage: number,
  pageSize: number,
  spotName?: string,
  category?: string,
) => {
  return request_handler<ResultPackage<ScenicSpotListData>>({
    method: 'GET',
    url: '/scenic-spots/list',
    params: { currentPage, pageSize, spotName, category },
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 查询景点详情 */
const getSpotDetail = (spotId: number) => {
  return request_handler<ResultPackage<ScenicSpotItem>>({
    method: 'GET',
    url: `/scenic-spots/info/${spotId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 获取当前管理员所属景点的游览说明 */
const getSpotInstruction = (spotId: number) => request_handler<ResultPackage<string>>({
  method: 'GET',
  url: `/scenic-spots/instruction/${spotId}`,
  headers: { Authorization: header_authorization.value },
})

/** 新增景点 */
const createSpot = (data: Partial<ScenicSpotItem>) => {
  return request_handler<ResultPackage<ScenicSpotItem>>({
    method: 'POST',
    url: '/scenic-spots/create',
    data,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 编辑景点 */
const editSpot = (spotId: number, data: Partial<ScenicSpotItem>) => {
  return request_handler<ResultPackage<ScenicSpotItem>>({
    method: 'PUT',
    url: `/scenic-spots/edit/${spotId}`,
    data,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 删除景点 */
const deleteSpot = (spotId: number) => {
  return request_handler<ResultPackage<string>>({
    method: 'DELETE',
    url: `/scenic-spots/delete/${spotId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** AI生成景点描述和历史详情 */
const aiGenerateSpotContent = (spotName: string) => {
  return request_handler<ResultPackage<{ description: string; history_detail: string }>>({
    method: 'POST',
    url: '/scenic-spots/ai-generate',
    params: { spot_name: spotName },
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

export {
  type SpotListParams,
  type ScenicSpotItem,
  type ScenicSpotListData,
  getSpotList,
  getSpotDetail,
  getSpotInstruction,
  createSpot,
  editSpot,
  deleteSpot,
  aiGenerateSpotContent,
}
