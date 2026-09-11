import request from '@/utils/request.js'

export function getPersonalCenter(typeName = 'article', drafted = 1) {
  return request({ url: '/personal/', method: 'get', params: { type_name: typeName, drafted } })
}
