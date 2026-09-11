import request from '@/utils/request.js'

export function getArticleList(params) {
  return request({ url: '/', method: 'get', params })
}

export function getArticleDetail(articleId) {
  return request({ url: '/article/detail', method: 'get', params: { article_id: articleId } })
}

export function getNewPageData() {
  return request({ url: '/article/new-page', method: 'get' })
}

export function getDraftedDetail(data) {
  return request({ url: '/article/drafted', method: 'post', data })
}

export function saveArticle(data) {
  return request({ url: '/article/save', method: 'post', data })
}

export function uploadHeaderImage(formData) {
  return request({ url: '/article/upload', method: 'post', headers: { 'Content-Type': 'multipart/form-data' }, data: formData })
}