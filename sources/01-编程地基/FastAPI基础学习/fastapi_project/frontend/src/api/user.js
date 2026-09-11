import request from '@/utils/request.js'

export function getVcodeUrl() {
  return '/api/user/vcode?' + Date.now()
}

export function sendEmailCode(data) {
  return request({ url: '/user/ecode', method: 'post', data })
}

export function register(data) {
  return request({ url: '/user/reg', method: 'post', data })
}

export function login(data) {
  return request({ url: '/user/login', method: 'post', data })
}

export function logout() {
  return request({ url: '/user/logout', method: 'post' })
}

export function getMe() {
  return request({ url: '/user/me', method: 'get' })
}
