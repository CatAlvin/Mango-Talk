import axios from 'axios'

export const TOKEN_KEY = 'mango_talk_token'
export const USER_KEY = 'mango_talk_user'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/',
  timeout: 10000,
})

http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY)

    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => Promise.reject(error)
)

http.interceptors.response.use((response) => response, (error) => {
  if ((error?.response?.status === 401 && !['/auth/login', '/auth/logout'].includes(error.config?.url)) || (error?.response?.status === 403 && error.config?.url === '/users/me')) {
    window.dispatchEvent(new Event('mango:unauthorized'))
  }
  return Promise.reject(error)
})

export default http
