import request from '@/utils/request.js'

export function updateFavoriteStatus(data) {
  return request({ url: '/favorite/update_status', method: 'post', data })
}
