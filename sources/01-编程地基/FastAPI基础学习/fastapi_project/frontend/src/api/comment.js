import request from '@/utils/request.js'

export function addComment(data) {
  return request({ url: '/comment/add', method: 'post', data })
}

export function replyComment(data) {
  return request({ url: '/comment/reply', method: 'post', data })
}
