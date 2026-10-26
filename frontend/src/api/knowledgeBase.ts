import { request_handler, type ResultPackage } from '@/api/base'
import { header_authorization } from '@/api/user'

// ---- 查询参数 ----

interface DocListParams {
  currentPage: number
  pageSize: number
  title?: string
}

// ---- 数据实体 ----

interface KnowledgeDocItem {
  doc_id: number
  title: string
  file_type: string
  file_path: string
  chunk_count: number
  upload_time: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'rejected'
  content_hash: string
}

interface KnowledgeDocListData {
  doc_list: KnowledgeDocItem[]
  currentPage: number
  pageSize: number
  totalSize: number
}

interface AccuracyTestResult {
  total: number
  correct: number
  accuracy: number
  passed: boolean
  metric_name: string
  pass_threshold: number
  evaluation_method: string
  model_name: string
  rag_enabled: boolean
  duration_ms: number
  executed_at: string
  details: AccuracyTestDetail[]
}

interface AccuracyTestDetail {
  question: string
  spot_name?: string
  source_doc?: string
  category?: string
  expected_keywords?: string
  expected_answer: string
  actual_answer: string
  matched_keywords: string[]
  matched_count: number
  required_count: number
  keyword_coverage: number
  reference_count: number
  duration_ms: number
  error?: string
  is_correct: boolean
}

// ---- 接口函数 ----

/** 上传知识库文档（FormData 方式） */
const uploadDoc = (formData: FormData) => {
  return request_handler<ResultPackage<{ doc_id: number }>>({
    method: 'POST',
    url: '/knowledge-base/upload',
    data: formData,
    headers: {
      Authorization: header_authorization.value,
      'Content-Type': 'multipart/form-data',
    },
  })
}

/** 分页查询知识库文档列表 */
const getDocList = (params: DocListParams) => {
  return request_handler<ResultPackage<KnowledgeDocListData>>({
    method: 'GET',
    url: '/knowledge-base/list',
    params,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 删除知识库文档 */
const deleteDoc = (docId: number) => {
  return request_handler<ResultPackage<string>>({
    method: 'DELETE',
    url: `/knowledge-base/delete/${docId}`,
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 全部重建索引 */
const rebuildIndex = () => {
  return request_handler<ResultPackage<string>>({
    method: 'POST',
    url: '/knowledge-base/reindex',
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

/** 执行真实的 RAG 知识问答评测 */
const testAccuracy = () => {
  return request_handler<ResultPackage<AccuracyTestResult>>({
    method: 'GET',
    url: '/knowledge-base/test-qa',
    headers: {
      Authorization: header_authorization.value,
    },
  })
}

export {
  type DocListParams,
  type KnowledgeDocItem,
  type KnowledgeDocListData,
  type AccuracyTestResult,
  type AccuracyTestDetail,
  uploadDoc,
  getDocList,
  deleteDoc,
  rebuildIndex,
  testAccuracy,
}
