import axios from 'axios'

const request_handler = axios.create({
  timeout: 30000,
  timeoutErrorMessage: '请求超时，请检查网络或服务状态后重试',
})

interface ResultPackage<T> {
  success: boolean
  code: number
  message: string
  data: T
  timestamp: number
}

export { request_handler }
export { type ResultPackage }
