import axios from 'axios'
import { getToken, removeToken } from './auth.js'
import { useRouter } from 'vue-router'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

request.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 401) {
      removeToken()
      window.location.href = '/#/login'
      return Promise.reject(new Error(res.msg || '未登录'))
    }
    return res
  },
  (error) => {
    if (error.response?.status === 401) {
      removeToken()
      window.location.href = '/#/login'
    }
    return Promise.reject(error)
  }
)

export default request
