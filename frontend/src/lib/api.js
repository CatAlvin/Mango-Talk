import http from './http'
import { demoRequest, isDemoActive } from './demo'

export default {
  get(url, config) { return isDemoActive() ? demoRequest('get', url, null, config) : http.get(url, config) },
  post(url, body, config) { return isDemoActive() ? demoRequest('post', url, body, config) : http.post(url, body, config) },
}

export function errorText(error, fallback) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (error?.response?.status === 401) return '登录已过期，请重新登录'
  if (!error?.response && error?.message && isDemoActive()) return error.message
  return fallback
}
