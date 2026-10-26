import { request_handler, type ResultPackage } from '@/api/base'
import { header_authorization } from '@/api/user'

// ---- 数字导游数据实体 ----

export interface DigitalGuide {
  is_enabled: boolean
  voice_label?: string
  render_mode?: string
  guide_id: number
  name: string
  character: string
  avatar: string
  voice_style: string
  voice_speed: number
  outfit_images: string
  poster_image: string
  base_mp4_path: string
  tts_reference_audio: string
  tts_reference_sentence: string
  created_at: string
  updated_at: string
}

export interface DigitalGuideListData {
  guide_list: DigitalGuide[]
  currentPage: number
  pageSize: number
  totalSize: number
}

// ---- 数字导游 CRUD 接口 ----

/** 分页查询数字导游列表 */
const getGuideList = (currentPage: number, pageSize: number, name?: string) => {
  return request_handler<ResultPackage<DigitalGuideListData>>({
    method: 'GET',
    url: '/digital-guide/list',
    params: { currentPage, pageSize, name },
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 查询数字导游详情 */
const getGuideDetail = (guideId: number) => {
  return request_handler<ResultPackage<DigitalGuide>>({
    method: 'GET',
    url: `/digital-guide/info/${guideId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 新增数字导游 */
const createGuide = (data: Partial<DigitalGuide>) => {
  return request_handler<ResultPackage<DigitalGuide>>({
    method: 'POST',
    url: '/digital-guide/create',
    data,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 编辑数字导游 */
const editGuide = (guideId: number, data: Partial<DigitalGuide>) => {
  return request_handler<ResultPackage<DigitalGuide>>({
    method: 'PUT',
    url: `/digital-guide/edit/${guideId}`,
    data,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 删除数字导游 */
const deleteGuide = (guideId: number) => {
  return request_handler<ResultPackage<string>>({
    method: 'DELETE',
    url: `/digital-guide/delete/${guideId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

export { getGuideList, getGuideDetail, createGuide, editGuide, deleteGuide }
